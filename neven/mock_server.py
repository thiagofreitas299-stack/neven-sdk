"""
NEVEN Mock Server
==================
A lightweight HTTP mock server that simulates the NEVEN physical runtime.
Enables full SDK development and testing WITHOUT any physical hardware.

Usage:
    # Start from CLI
    neven mock-server

    # Or from Python
    from neven.mock_server import MockServer
    server = MockServer(port=8420)
    server.start()  # blocking
    # Or: server.start_background()

    # Then use SDK with mock=True
    client = NevenClient(api_key="nv_test_xxx", mock=True)

The mock server simulates:
    - Camera feeds (returns synthetic detections)
    - Sensor readings (temperature, occupancy, motion)
    - Actuator responses (screen, speaker, locker, LED)
    - DSE safety validation (enforces sample rules)
    - WebSocket event streaming
"""

import json
import random
import time
import uuid
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional


# ---------------------------------------------------------------------------
# Mock data generators
# ---------------------------------------------------------------------------

def _mock_entities(count: int = None) -> list[dict]:
    """Generate realistic mock entity detections."""
    count = count or random.randint(0, 5)
    classes = ["person", "vehicle", "package"]
    entities = []
    for i in range(count):
        cls = random.choice(classes)
        entities.append({
            "entity_id": f"ent_{cls[:3]}_{uuid.uuid4().hex[:6]}",
            "class": cls,
            "confidence": round(random.uniform(0.80, 0.99), 2),
            "spatial_position": {
                "latitude": round(-23.0 + random.uniform(-0.1, 0.1), 6),
                "longitude": round(-43.0 + random.uniform(-0.1, 0.1), 6),
                "h3_index": "8b80145a5a08fff",
            },
            "velocity": {"x": round(random.uniform(-1, 1), 2), "y": round(random.uniform(-1, 1), 2)},
        })
    return entities


def _mock_telemetry() -> dict:
    return {
        "temperature_celsius": round(20 + random.uniform(0, 10), 1),
        "ambient_light_lux": random.randint(200, 800),
        "humidity_percent": round(40 + random.uniform(0, 40), 1),
        "noise_db": round(40 + random.uniform(0, 30), 1),
    }


# ---------------------------------------------------------------------------
# In-memory state store
# ---------------------------------------------------------------------------

class MockStateStore:
    """Simulates the Physical World State Graph in memory."""

    def __init__(self):
        self.sessions: dict[str, dict] = {}
        self.nodes: dict[str, dict] = {
            # Pre-populated sample nodes
            "node_rj_keepithub_01": {
                "name": "KEEPITHUB Hub #1 — Rio de Janeiro",
                "type": "hub",
                "location": "Rio de Janeiro, Brazil",
                "capabilities": ["camera", "screen", "voice", "locker", "payment"],
                "status": "active",
            },
            "node_sp_iguatemi_01": {
                "name": "Iguatemi São Paulo — Main Entrance",
                "type": "kiosk",
                "location": "São Paulo, Brazil",
                "capabilities": ["camera", "screen", "voice"],
                "status": "active",
            },
            "node_sh_bund_01": {
                "name": "Shanghai Bund Hub",
                "type": "hub",
                "location": "Shanghai, China",
                "capabilities": ["camera", "screen", "voice", "payment"],
                "status": "active",
            },
        }
        self.locker_states: dict[str, str] = {f"C-{i}": "locked" for i in range(1, 11)}
        self.action_log: list[dict] = []

    def create_session(self, agent_id: str, requested_nodes: list, capabilities: list) -> dict:
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        authorized = {}
        for node_id in requested_nodes:
            if node_id in self.nodes:
                authorized[node_id] = capabilities
        self.sessions[session_id] = {
            "agent_id": agent_id,
            "authorized_nodes": authorized,
            "created_at": time.time(),
        }
        return {
            "session_id": session_id,
            "status": "connected",
            "authorized_nodes": authorized,
            "deterministic_rules_enforced": [
                "rule_prevent_overload",
                "rule_human_presence_required",
                "rule_max_actuation_frequency",
            ],
            "websocket_stream_url": f"ws://localhost:8420/v1/stream?session_id={session_id}",
        }

    def get_node_state(self, node_id: str) -> Optional[dict]:
        return self.nodes.get(node_id)


_store = MockStateStore()


# ---------------------------------------------------------------------------
# DSE (Deterministic Safety Engine) — mock rules
# ---------------------------------------------------------------------------

def _dse_validate(node_id: str, action_type: str, parameters: dict) -> dict:
    """Simulate DSE safety validation."""
    rules_evaluated = []

    if action_type == "unlock_compartment":
        compartment_id = parameters.get("compartment_id", "")

        # Rule: max frequency (mocked as always passing here)
        rules_evaluated.append({"rule_id": "rule_max_actuation_frequency", "result": "passed"})

        # Rule: human presence required (mock: 80% chance person is present)
        person_present = random.random() > 0.2
        rules_evaluated.append({
            "rule_id": "rule_human_presence_required",
            "result": "passed" if person_present else "FAILED",
        })

        if not person_present:
            return {
                "dse_status": "blocked",
                "violated_rule_id": "rule_human_presence_required",
                "rules_evaluated": rules_evaluated,
                "message": "SAFETY_RULE_VIOLATION: No verified human detected within 1.5 meters",
            }

        # Rule: compartment not already open
        current_state = _store.locker_states.get(compartment_id, "unknown")
        already_open = current_state == "unlocked"
        rules_evaluated.append({
            "rule_id": "rule_no_double_unlock",
            "result": "FAILED" if already_open else "passed",
        })

        if already_open:
            return {
                "dse_status": "blocked",
                "violated_rule_id": "rule_no_double_unlock",
                "rules_evaluated": rules_evaluated,
                "message": f"SAFETY_RULE_VIOLATION: Compartment {compartment_id} already open",
            }

    # All other actions: cleared by default in mock
    rules_evaluated.append({"rule_id": "rule_default_allow", "result": "passed"})
    return {"dse_status": "cleared", "rules_evaluated": rules_evaluated}


# ---------------------------------------------------------------------------
# HTTP Request Handler
# ---------------------------------------------------------------------------

class NevenMockHandler(BaseHTTPRequestHandler):
    """Handles all NEVEN API mock requests."""

    def log_message(self, fmt, *args):
        # Suppress default noisy logging; use our own
        pass

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Neven-Mock", "true")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length:
            return json.loads(self.rfile.read(length))
        return {}

    def do_GET(self):
        if self.path == "/health":
            self._send_json({"status": "ok", "mock": True, "version": "1.0.0"})
        elif self.path == "/v1/nodes":
            self._send_json({"nodes": list(_store.nodes.values())})
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        body = self._read_body()

        # ── Session Connect ──────────────────────────────────────────────────
        if self.path == "/v1/session/connect":
            result = _store.create_session(
                agent_id=body.get("agent_id", "unknown"),
                requested_nodes=body.get("requested_nodes", []),
                capabilities=body.get("capabilities_required", ["perception", "actuation"]),
            )
            print(f"  [NEVEN MOCK] ✅ Session {result['session_id'][:12]}... "
                  f"agent={body.get('agent_id')} nodes={body.get('requested_nodes')}")
            self._send_json(result)

        # ── Session Disconnect ───────────────────────────────────────────────
        elif self.path == "/v1/session/disconnect":
            session_id = body.get("session_id", "")
            _store.sessions.pop(session_id, None)
            self._send_json({"status": "disconnected"})

        # ── Perception Query ─────────────────────────────────────────────────
        elif self.path == "/v1/perception/query":
            node_id = body.get("node_id", "unknown")
            params = body.get("parameters", {})
            target_objects = params.get("target_objects", ["person", "vehicle", "package"])
            threshold = params.get("confidence_threshold", 0.75)

            entities = [e for e in _mock_entities() if e["class"] in target_objects
                        and e["confidence"] >= threshold]
            occupancy = round(len(entities) / 10, 2)

            result = {
                "node_id": node_id,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "spatial_state": {
                    "occupancy_status": "occupied" if entities else "empty",
                    "occupancy_ratio": occupancy,
                    "detected_entities": entities,
                    "environmental_telemetry": _mock_telemetry(),
                    "anomalies": [],
                },
                "_mock": True,
            }
            print(f"  [NEVEN MOCK] 👁  perceive {node_id} → {len(entities)} entities")
            self._send_json(result)

        # ── Actuation Execute ────────────────────────────────────────────────
        elif self.path == "/v1/actuation/execute":
            node_id = body.get("node_id", "unknown")
            action_type = body.get("action_type", "unknown")
            parameters = body.get("parameters", {})

            # DSE validation
            dse = _dse_validate(node_id, action_type, parameters)

            if dse["dse_status"] == "blocked":
                result = {
                    "status": "blocked",
                    "reason": dse.get("message", "DSE blocked action"),
                    "safety_evaluation": dse,
                    "_mock": True,
                }
                print(f"  [NEVEN MOCK] 🛡  DSE BLOCKED {action_type} on {node_id}: {dse['message']}")
                self._send_json(result, 200)  # 200 but status=blocked
                return

            # Execute mock action
            tx_id = f"tx_act_{uuid.uuid4().hex[:8]}"
            _store.action_log.append({
                "tx_id": tx_id,
                "node_id": node_id,
                "action_type": action_type,
                "parameters": parameters,
                "timestamp": time.time(),
            })

            # Update locker state if unlocking
            if action_type == "unlock_compartment":
                comp_id = parameters.get("compartment_id")
                if comp_id:
                    _store.locker_states[comp_id] = "unlocked"

            result = {
                "transaction_id": tx_id,
                "node_id": node_id,
                "status": "executed",
                "safety_evaluation": dse,
                "execution_details": {
                    "actuator_response_code": "0x00_SUCCESS",
                    "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "action_type": action_type,
                    "parameters": parameters,
                },
                "_mock": True,
            }
            print(f"  [NEVEN MOCK] ⚡ {action_type} → {node_id} ✅ tx={tx_id[:12]}")
            self._send_json(result)

        else:
            self._send_json({"error": "Endpoint not found", "path": self.path}, 404)


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

class MockServer:
    """NEVEN Mock Server for development and testing."""

    def __init__(self, host: str = "localhost", port: int = 8420):
        self.host = host
        self.port = port
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Start server (blocking)."""
        self._server = HTTPServer((self.host, self.port), NevenMockHandler)
        print(f"\n{'='*55}")
        print(f"  🌌 NEVEN Mock Server running on http://{self.host}:{self.port}")
        print(f"  Use: NevenClient(api_key='nv_test_xxx', mock=True)")
        print(f"  Or:  NEVEN_MOCK=1 python your_script.py")
        print(f"  Health: GET http://{self.host}:{self.port}/health")
        print(f"{'='*55}\n")
        self._server.serve_forever()

    def start_background(self) -> "MockServer":
        """Start server in background thread. Returns self for chaining."""
        self._thread = threading.Thread(target=self.start, daemon=True)
        self._thread.start()
        time.sleep(0.3)  # Brief wait for server to bind
        return self

    def stop(self):
        """Stop the server."""
        if self._server:
            self._server.shutdown()
            self._server = None


def run_mock_server(port: int = 8420):
    """Entry point for `neven mock-server` CLI command."""
    server = MockServer(port=port)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n  Mock server stopped.")
