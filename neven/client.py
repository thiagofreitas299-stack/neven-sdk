"""
NEVEN Client — Core SDK Interface
===================================
The main entry point for interacting with the NEVEN Physical World Runtime.

Architecture:
    NevenClient
    ├── connect()     → Establish session with physical nodes
    ├── perceive()    → Query semantic state of physical space
    ├── act()         → Execute safe physical actions (via DSE)
    ├── subscribe()   → Stream real-time spatial events
    └── disconnect()  → Close session

Usage:
    client = NevenClient(api_key="nv_live_xxx")
    session = client.connect(
        agent_id="my-agent-01",
        requested_nodes=["node_sp_iguatemi_01"],
        capabilities=["perception", "actuation"]
    )
    state = client.perceive("node_sp_iguatemi_01")
    result = client.act("node_sp_iguatemi_01", "display_message", {"text": "Hello!"})
"""

import json
import time
import hmac
import hashlib
from typing import Any, Callable, Generator, Optional
from dataclasses import dataclass, field

import requests

from neven.exceptions import (
    NevenAuthError,
    NevenConnectionError,
    NevenSafetyError,
    NevenNodeNotFoundError,
    NevenActuationError,
    NevenSessionError,
)

# Default API base — points to mock server in dev, real server in prod
DEFAULT_BASE_URL = "https://api.neventech.com"
MOCK_BASE_URL = "http://localhost:8420"


@dataclass
class NevenSession:
    """Active session between an agent and NEVEN physical nodes."""
    session_id: str
    agent_id: str
    authorized_nodes: dict[str, list[str]]
    rules_enforced: list[str]
    websocket_url: str
    created_at: float = field(default_factory=time.time)

    @property
    def is_valid(self) -> bool:
        return bool(self.session_id)

    def can_perceive(self, node_id: str) -> bool:
        caps = self.authorized_nodes.get(node_id, [])
        return "perception" in caps or "perceive" in caps

    def can_act(self, node_id: str) -> bool:
        caps = self.authorized_nodes.get(node_id, [])
        return "actuation" in caps or "act" in caps


class NevenClient:
    """
    NEVEN Physical World Runtime Client.

    Connect any AI agent to the physical world — cameras, screens,
    sensors, locks, payments — through a single unified API.

    Args:
        api_key: Your NEVEN API key (starts with nv_live_ or nv_test_)
        agent_private_key: Secret key for cryptographic signing (optional)
        base_url: API base URL (default: https://api.neventech.com)
        timeout: Request timeout in seconds (default: 30)
        mock: Use mock server for development (default: False)

    Example:
        # Real server
        client = NevenClient(api_key="nv_live_xxx")

        # Development (mock server)
        client = NevenClient(api_key="nv_test_xxx", mock=True)
        # Or: NEVEN_MOCK=1 in environment

    Raises:
        NevenAuthError: Invalid API key
        NevenConnectionError: Cannot reach NEVEN runtime
    """

    def __init__(
        self,
        api_key: str,
        agent_private_key: str = None,
        base_url: str = None,
        timeout: int = 30,
        mock: bool = False,
    ):
        import os

        self.api_key = api_key
        self.agent_private_key = (agent_private_key or os.urandom(32).hex()).encode("utf-8")
        self.timeout = timeout

        # Auto-detect mock mode
        if mock or os.environ.get("NEVEN_MOCK") == "1" or api_key.startswith("nv_test_"):
            self.base_url = MOCK_BASE_URL
            self._mock = True
        else:
            self.base_url = base_url or DEFAULT_BASE_URL
            self._mock = False

        self._session: Optional[NevenSession] = None
        self._event_handlers: dict[str, list[Callable]] = {}

    # -------------------------------------------------------------------------
    # Session Management
    # -------------------------------------------------------------------------

    def connect(
        self,
        agent_id: str,
        requested_nodes: list[str],
        capabilities: list[str] = None,
        session_timeout: int = 3600,
    ) -> NevenSession:
        """
        Establish a secure session with NEVEN physical nodes.

        Args:
            agent_id: Unique identifier for your agent
            requested_nodes: List of node IDs to connect to
            capabilities: Required capabilities: ["perception", "actuation"]
            session_timeout: Session TTL in seconds (default: 1h)

        Returns:
            NevenSession with authorized nodes and rules

        Raises:
            NevenAuthError: Invalid credentials
            NevenConnectionError: Cannot reach nodes

        Example:
            session = client.connect(
                agent_id="jarvis-guide-01",
                requested_nodes=["node_sp_iguatemi_01"],
                capabilities=["perception", "actuation"]
            )
            print(f"Connected! Session: {session.session_id}")
        """
        payload = {
            "agent_id": agent_id,
            "requested_nodes": requested_nodes,
            "capabilities_required": capabilities or ["perception", "actuation"],
            "session_timeout_seconds": session_timeout,
        }

        data = self._post("/v1/session/connect", payload)

        self._session = NevenSession(
            session_id=data["session_id"],
            agent_id=agent_id,
            authorized_nodes=data.get("authorized_nodes", {}),
            rules_enforced=data.get("deterministic_rules_enforced", []),
            websocket_url=data.get("websocket_stream_url", ""),
        )
        return self._session

    def disconnect(self) -> None:
        """Close the active session."""
        if self._session:
            try:
                self._post("/v1/session/disconnect", {"session_id": self._session.session_id})
            except Exception:
                pass
            self._session = None

    @property
    def session(self) -> NevenSession:
        if not self._session:
            raise NevenSessionError()
        return self._session

    # -------------------------------------------------------------------------
    # Core API: Perceive
    # -------------------------------------------------------------------------

    def perceive(
        self,
        node_id: str,
        query_type: str = "semantic_state",
        target_objects: list[str] = None,
        confidence_threshold: float = 0.75,
        include_telemetry: bool = True,
    ) -> dict:
        """
        Query the real-time semantic state of a physical space.

        The NEVEN runtime processes raw video/sensor feeds at the edge
        and returns structured semantic state — no raw video is sent.

        Args:
            node_id: Physical node to query
            query_type: Type of query ("semantic_state", "occupancy", "anomalies")
            target_objects: Filter by object class (e.g. ["person", "vehicle"])
            confidence_threshold: Minimum confidence for detections (0.0-1.0)
            include_telemetry: Include environmental data (temp, light, etc.)

        Returns:
            Dict with spatial_state, detected_entities, telemetry

        Example:
            state = client.perceive(
                node_id="node_sp_iguatemi_01",
                target_objects=["person"],
                confidence_threshold=0.85
            )
            for entity in state["spatial_state"]["detected_entities"]:
                print(f"Found {entity['class']} at {entity['spatial_position']}")
        """
        self._require_session()

        payload = {
            "session_id": self.session.session_id,
            "node_id": node_id,
            "query_type": query_type,
            "parameters": {
                "target_objects": target_objects or ["person", "vehicle", "package"],
                "return_spatial_coordinates": True,
                "confidence_threshold": confidence_threshold,
                "include_telemetry": include_telemetry,
            },
        }

        return self._post("/v1/perception/query", payload)

    # -------------------------------------------------------------------------
    # Core API: Act
    # -------------------------------------------------------------------------

    def act(
        self,
        node_id: str,
        action_type: str,
        parameters: dict,
        verify: bool = True,
    ) -> dict:
        """
        Execute a physical action on a node — safely, via the DSE.

        ALL actions pass through the Deterministic Safety Engine (DSE)
        before any electrical signal is sent to the actuator. This is
        non-negotiable — it's what makes NEVEN safe for the real world.

        Supported actions (varies by node type):
            - display_message: Show text/media on screen
            - unlock_compartment: Open smart locker compartment
            - speak: Text-to-speech output
            - set_led: Control LED indicators
            - read_sensor: Read specific sensor value
            - trigger_alarm: Activate/deactivate alarm
            - process_payment: Initiate payment flow

        Args:
            node_id: Target physical node
            action_type: Action to execute (see supported actions above)
            parameters: Action-specific parameters
            verify: Include cryptographic signature (required for actuation)

        Returns:
            Dict with transaction_id, status, safety_evaluation, execution_details

        Raises:
            NevenSafetyError: DSE blocked the action (safety rule violation)
            NevenActuationError: Hardware-level failure
            NevenAuthError: Agent not authorized for this action

        Example:
            # Display a message
            result = client.act(
                node_id="node_sp_iguatemi_01",
                action_type="display_message",
                parameters={"text": "Welcome! How can I help?", "duration_seconds": 10}
            )

            # Unlock compartment (will be blocked by DSE if no person present)
            result = client.act(
                node_id="node_rj_keepithub_01",
                action_type="unlock_compartment",
                parameters={"compartment_id": "C-4"}
            )
        """
        self._require_session()

        payload = {
            "session_id": self.session.session_id,
            "node_id": node_id,
            "action_type": action_type,
            "parameters": parameters,
        }

        if verify:
            payload["cryptographic_signature"] = self._sign_payload(payload)

        data = self._post("/v1/actuation/execute", payload)

        # Surface DSE safety violations as proper exceptions
        if data.get("status") == "blocked":
            safety = data.get("safety_evaluation", {})
            raise NevenSafetyError(
                message=data.get("reason", "Action blocked by Deterministic Safety Engine"),
                rule_id=safety.get("violated_rule_id"),
                details=safety,
            )

        return data

    # -------------------------------------------------------------------------
    # Convenience methods
    # -------------------------------------------------------------------------

    def display(self, node_id: str, text: str, duration: int = 10) -> dict:
        """Show a message on a node's screen. Shortcut for act(display_message)."""
        return self.act(node_id, "display_message", {"text": text, "duration_seconds": duration})

    def speak(self, node_id: str, text: str, lang: str = "pt-BR") -> dict:
        """Speak a message via node's speaker. Shortcut for act(speak)."""
        return self.act(node_id, "speak", {"text": text, "language": lang})

    def unlock(self, node_id: str, compartment_id: str, token: str = None) -> dict:
        """Unlock a compartment. DSE will verify safety before actuation."""
        params = {"compartment_id": compartment_id}
        if token:
            params["verification_token"] = token
        return self.act(node_id, "unlock_compartment", params)

    def get_occupancy(self, node_id: str) -> float:
        """Get current occupancy ratio (0.0-1.0) for a space."""
        state = self.perceive(node_id, query_type="occupancy")
        return state.get("spatial_state", {}).get("occupancy_ratio", 0.0)

    def get_people_count(self, node_id: str) -> int:
        """Count people currently detected in a space."""
        state = self.perceive(node_id, target_objects=["person"])
        entities = state.get("spatial_state", {}).get("detected_entities", [])
        return sum(1 for e in entities if e.get("class") == "person")

    def detect_anomalies(self, node_id: str) -> list[dict]:
        """Get list of detected anomalies in a space."""
        state = self.perceive(node_id, query_type="anomalies")
        return state.get("spatial_state", {}).get("anomalies", [])

    # -------------------------------------------------------------------------
    # Event Subscription
    # -------------------------------------------------------------------------

    def on(self, event_type: str) -> Callable:
        """
        Decorator to register an event handler for spatial events.

        Example:
            @client.on("person_detected")
            def handle_person(event):
                print(f"Person at {event['payload']['spatial_coordinates']}")
        """
        def decorator(func: Callable) -> Callable:
            if event_type not in self._event_handlers:
                self._event_handlers[event_type] = []
            self._event_handlers[event_type].append(func)
            return func
        return decorator

    def subscribe(
        self,
        node_id: str,
        event_types: list[str] = None,
        class_filters: list[str] = None,
    ) -> Generator[dict, None, None]:
        """
        Stream real-time spatial events from a physical node.

        Args:
            node_id: Node to subscribe to
            event_types: Filter event types (e.g. ["person_detected", "anomaly_detected"])
            class_filters: Filter by object class (e.g. ["person", "vehicle"])

        Yields:
            Event dicts as they arrive from the physical space

        Example:
            for event in client.subscribe("node_sp_01", event_types=["person_detected"]):
                print(f"Event: {event['event_type']} at {event['timestamp']}")
        """
        self._require_session()

        # In real implementation, this opens a WebSocket to self.session.websocket_url
        # For now, yields mock events (mock mode) or real events via WS
        if self._mock:
            yield from self._mock_event_stream(node_id, event_types, class_filters)
        else:
            yield from self._ws_event_stream(node_id, event_types, class_filters)

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _require_session(self):
        if not self._session:
            raise NevenSessionError()

    def _sign_payload(self, payload: dict) -> str:
        timestamp = int(time.time())
        payload_str = json.dumps(payload, sort_keys=True)
        message = f"{timestamp}:{payload_str}".encode("utf-8")
        return hmac.new(self.agent_private_key, message, hashlib.sha256).hexdigest()

    def _get_headers(self, payload_str: str) -> dict:
        timestamp = int(time.time())
        sig = hmac.new(
            self.agent_private_key,
            f"{timestamp}:{payload_str}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return {
            "Authorization": f"Bearer {self.api_key}",
            "X-Neven-Signature": sig,
            "X-Neven-Timestamp": str(timestamp),
            "Content-Type": "application/json",
            "User-Agent": "neven-sdk-python/1.0.0",
        }

    def _post(self, endpoint: str, payload: dict) -> dict:
        url = f"{self.base_url}{endpoint}"
        payload_str = json.dumps(payload)
        headers = self._get_headers(payload_str)

        try:
            resp = requests.post(url, data=payload_str, headers=headers, timeout=self.timeout)
        except requests.exceptions.ConnectionError as e:
            if self._mock:
                raise NevenConnectionError(
                    "Mock server not running. Start it with: neven mock-server\n"
                    "Or install with: pip install neven-sdk[dev]"
                ) from e
            raise NevenConnectionError(f"Cannot reach NEVEN runtime at {self.base_url}") from e
        except requests.exceptions.Timeout as e:
            raise NevenConnectionError(f"Request timed out after {self.timeout}s") from e

        if resp.status_code == 401:
            raise NevenAuthError()
        if resp.status_code == 404:
            raise NevenNodeNotFoundError(payload.get("node_id", "unknown"))
        if not resp.ok:
            try:
                err = resp.json()
                msg = err.get("message") or err.get("error") or resp.text
            except Exception:
                msg = resp.text
            raise NevenActuationError(f"API error {resp.status_code}: {msg}")

        return resp.json()

    def _mock_event_stream(self, node_id, event_types, class_filters):
        """Generate mock events for development (no hardware needed)."""
        import random
        event_catalog = [
            {
                "event_type": "person_detected",
                "payload": {
                    "entity_id": f"ent_{random.randint(1000,9999)}",
                    "class": "person",
                    "confidence": round(random.uniform(0.85, 0.99), 2),
                    "spatial_coordinates": {"latitude": -23.5505, "longitude": -46.6333},
                },
            },
            {
                "event_type": "anomaly_detected",
                "payload": {
                    "anomaly_class": "unattended_baggage",
                    "confidence": 0.87,
                    "duration_unattended_seconds": 300,
                },
            },
        ]
        count = 0
        while count < 5:  # Finite in mock mode
            import time as t
            t.sleep(2)
            event = random.choice(event_catalog)
            if event_types and event["event_type"] not in event_types:
                continue
            yield {
                "event_id": f"evt_{count:04d}",
                "event_type": event["event_type"],
                "node_id": node_id,
                "timestamp": t.strftime("%Y-%m-%dT%H:%M:%SZ", t.gmtime()),
                "payload": event["payload"],
                "_mock": True,
            }
            count += 1

    def _ws_event_stream(self, node_id, event_types, class_filters):
        """Real WebSocket stream (production)."""
        try:
            import websocket as ws_lib
        except ImportError:
            raise ImportError("websocket-client required: pip install websocket-client")

        sub_payload = {
            "session_id": self.session.session_id,
            "filters": [{
                "node_id": node_id,
                "event_types": event_types or ["entity_entered", "anomaly_detected"],
                "class_filters": class_filters or ["person", "vehicle"],
            }],
        }

        ws = ws_lib.create_connection(
            self.session.websocket_url,
            header=[f"Authorization: Bearer {self.api_key}"],
        )
        ws.send(json.dumps(sub_payload))

        try:
            while True:
                raw = ws.recv()
                if raw:
                    yield json.loads(raw)
        finally:
            ws.close()

    # -------------------------------------------------------------------------
    # Context manager
    # -------------------------------------------------------------------------

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.disconnect()

    def __repr__(self):
        status = f"session={self._session.session_id[:8]}..." if self._session else "disconnected"
        mode = "mock" if self._mock else "live"
        return f"NevenClient(mode={mode!r}, {status})"
