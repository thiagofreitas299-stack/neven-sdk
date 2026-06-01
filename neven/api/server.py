"""
NEVEN REST API Server

FastAPI-based server implementing the full NEVEN API specification:
    - POST /v1/session/connect      — Establish agent session
    - POST /v1/perception/query     — Query spatial state
    - POST /v1/actuation/execute    — Execute physical actions (DSE-protected)
    - POST /v1/perception/events    — Poll for events
    - GET  /v1/perception/subscribe — WebSocket event stream
    - GET  /v1/analytics/*          — Analytics endpoints
    - GET  /v1/graph/*              — State graph endpoints
    - GET  /v1/devices/*            — Device management
    - GET  /health                  — Health check
    - GET  /                        — Dashboard redirect
"""

import time
import uuid
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from neven.core.config import NevenConfig
from neven.core.models import (
    ConnectRequest,
    ConnectResponse,
    PerceiveRequest,
    PerceiveResponse,
    ActRequest,
    ActResponse,
    SpatialState,
    SafetyEvaluation,
    DetectedEntity,
    DSEStatus,
    PhysicalNode,
    Device,
    NodeType,
    DeviceProtocol,
)
from neven.safety.engine import SafetyEngine, SafetyRule
from neven.graph.state_graph import PhysicalWorldStateGraph
from neven.hal.bridge import HardwareBridge
from neven.perception.pipeline import PerceptionPipeline
from neven.analytics.engine import AnalyticsEngine

logger = logging.getLogger("neven.api")


def create_app(config: Optional[NevenConfig] = None) -> FastAPI:
    """Create and configure the NEVEN FastAPI application."""

    config = config or NevenConfig.from_env()

    app = FastAPI(
        title="NEVEN TECH API",
        description=(
            "The Physical World Runtime — AI · SMART CITY SOLUTIONS\n\n"
            "NEVEN connects AI agents to any physical infrastructure "
            "(cameras, sensors, IoT) without owning the hardware."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ─── Core Services ────────────────────────────────────────────────────
    safety_engine = SafetyEngine()
    state_graph = PhysicalWorldStateGraph()
    hardware_bridge = HardwareBridge()
    analytics_engine = AnalyticsEngine(
        heatmap_resolution=config.heatmap_resolution,
        dwell_threshold_seconds=config.dwell_time_threshold_seconds,
    )
    perception_pipeline: Optional[PerceptionPipeline] = None

    # Session store
    sessions: Dict[str, Dict[str, Any]] = {}

    # Event store
    events: List[Dict[str, Any]] = []

    # Store references on app state
    app.state.config = config
    app.state.safety_engine = safety_engine
    app.state.state_graph = state_graph
    app.state.hardware_bridge = hardware_bridge
    app.state.analytics_engine = analytics_engine
    app.state.sessions = sessions
    app.state.events = events

    # ─── Setup Demo Data ──────────────────────────────────────────────────

    def _setup_demo_environment():
        """Initialize demo nodes and devices for out-of-box experience."""
        # Create demo node hierarchy
        city_node = PhysicalNode(
            node_id="node_demo_city",
            name="Demo City",
            type=NodeType.CITY,
        )
        district_node = PhysicalNode(
            node_id="node_demo_district",
            parent_node_id="node_demo_city",
            name="Demo District",
            type=NodeType.DISTRICT,
        )
        hub_node = PhysicalNode(
            node_id="node_demo_hub",
            parent_node_id="node_demo_district",
            name="NEVEN Smart Hub #01",
            type=NodeType.HUB,
        )
        camera_node = PhysicalNode(
            node_id="node_demo_camera",
            parent_node_id="node_demo_hub",
            name="Main Camera",
            type=NodeType.CAMERA,
        )

        state_graph.add_node(city_node)
        state_graph.add_node(district_node)
        state_graph.add_node(hub_node)
        state_graph.add_node(camera_node)

        # Register demo device
        demo_device = Device(
            device_id="dev_demo_webcam",
            node_id="node_demo_camera",
            name="Demo Webcam",
            protocol=DeviceProtocol.WEBCAM,
            connection_uri="0",
        )
        state_graph.register_device(demo_device)
        hardware_bridge.register_device(demo_device)

        # Register demo agent with full permissions
        safety_engine.register_agent(
            agent_id="demo_agent",
            node_ids=["*"],
            allowed_actions=["*"],
        )

        # Register safety rules for the hub
        safety_engine.register_node_rules(
            "node_demo_hub",
            [
                SafetyRule(
                    rule_id="rule_prevent_overload",
                    description="Block if weight exceeds 50kg",
                    trigger_action="unlock_compartment",
                    assertion="sensor_weight_kg < 50.0",
                ),
                SafetyRule(
                    rule_id="rule_human_presence",
                    description="Require human within range for unlock",
                    trigger_action="unlock_compartment",
                    assertion="occupancy > 0",
                ),
            ],
        )

        logger.info("Demo environment initialized with sample nodes and devices")

    _setup_demo_environment()

    # ─── Perception Pipeline Integration ──────────────────────────────────

    def _on_perception_update(entities: List[DetectedEntity], frame):
        """Callback when perception pipeline produces new entities."""
        node_id = "node_demo_camera"
        state_graph.update_entities(node_id, entities)

        # Update analytics
        h, w = frame.shape[:2] if len(frame.shape) >= 2 else (480, 640)
        analytics_engine.process_entities(node_id, entities, w, h)

        # Generate events
        for entity in entities:
            if entity.metadata.get("dwell_time", 0) < 0.1:
                events.append({
                    "event_id": f"evt_{uuid.uuid4().hex[:8]}",
                    "event_type": "entity_entered",
                    "node_id": node_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "payload": {
                        "entity_id": entity.entity_id,
                        "class": entity.class_label.value,
                        "confidence": entity.confidence,
                    },
                })

        # Keep events manageable
        if len(events) > 1000:
            events[:] = events[-500:]

    # ─── API Endpoints ────────────────────────────────────────────────────

    @app.get("/", response_class=HTMLResponse)
    async def root():
        """Serve the dashboard or API info."""
        return HTMLResponse(content=_get_dashboard_html())

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "neven-api",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "safety_engine": "active" if safety_engine.enabled else "disabled",
                "state_graph": f"{state_graph.node_count} nodes",
                "hardware_bridge": f"{hardware_bridge.device_count} devices",
                "perception": "running" if perception_pipeline and perception_pipeline.is_running else "stopped",
            },
        }

    # ─── Session Endpoints ────────────────────────────────────────────────

    @app.post("/v1/session/connect", response_model=ConnectResponse)
    async def session_connect(request: ConnectRequest):
        """Establish a session with the NEVEN Physical World Protocol."""
        session_id = f"sess_{uuid.uuid4().hex[:12]}"

        # Determine authorized nodes
        authorized_nodes = {}
        for node_id in request.requested_nodes:
            node = state_graph.get_node(node_id)
            if node:
                authorized_nodes[node_id] = request.capabilities_required
            else:
                # Allow wildcard access for demo
                authorized_nodes[node_id] = request.capabilities_required

        # If no specific nodes requested, grant access to all
        if not request.requested_nodes:
            for node_data in state_graph.get_all_nodes():
                authorized_nodes[node_data["node_id"]] = request.capabilities_required

        # Store session
        sessions[session_id] = {
            "agent_id": request.agent_id,
            "authorized_nodes": authorized_nodes,
            "created_at": time.time(),
            "timeout": request.session_timeout_seconds,
        }

        # Register agent in safety engine if not already
        if not safety_engine.permission_ledger.is_registered(request.agent_id):
            safety_engine.register_agent(
                agent_id=request.agent_id,
                node_ids=list(authorized_nodes.keys()) + ["*"],
                allowed_actions=["perceive", "act", "subscribe"],
            )

        return ConnectResponse(
            session_id=session_id,
            status="connected",
            authorized_nodes=authorized_nodes,
            deterministic_rules_enforced=[
                r.rule_id for r in safety_engine._global_rules
            ],
            websocket_stream_url=f"/v1/perception/subscribe?session_id={session_id}",
        )

    # ─── Perception Endpoints ─────────────────────────────────────────────

    @app.post("/v1/perception/query")
    async def perception_query(request: PerceiveRequest):
        """Query the real-time spatial state of a physical node."""
        # Validate session
        session = sessions.get(request.session_id)
        if not session:
            raise HTTPException(status_code=401, detail="Invalid or expired session")

        node_id = request.node_id
        node = state_graph.get_node(node_id)

        if not node:
            raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")

        # Build spatial state response
        entities = node.entities
        entity_dicts = []
        for entity in entities:
            entity_dicts.append({
                "entity_id": entity.entity_id,
                "class": entity.class_label.value,
                "confidence": entity.confidence,
                "spatial_position": {
                    "x": entity.spatial_position.x if entity.spatial_position else 0,
                    "y": entity.spatial_position.y if entity.spatial_position else 0,
                },
                "bbox": entity.bbox.model_dump() if entity.bbox else None,
                "velocity": entity.velocity,
                "track_id": entity.track_id,
                "dwell_time": entity.metadata.get("dwell_time", 0),
            })

        return {
            "node_id": node_id,
            "timestamp": datetime.utcnow().isoformat(),
            "spatial_state": {
                "occupancy_status": node.state.get("occupancy_status", "empty"),
                "detected_entities": entity_dicts,
                "entity_count": len(entities),
                "environmental_telemetry": {
                    "temperature_celsius": 24.5,
                    "ambient_light_lux": 450,
                },
            },
        }

    @app.post("/v1/perception/events")
    async def perception_events(request: dict):
        """Poll for recent events."""
        session_id = request.get("session_id")
        if session_id not in sessions:
            raise HTTPException(status_code=401, detail="Invalid session")

        node_id = request.get("node_id")
        event_types = request.get("event_types", [])

        # Filter events
        filtered = []
        for event in events[-50:]:
            if node_id and event.get("node_id") != node_id:
                continue
            if event_types and event.get("event_type") not in event_types:
                continue
            filtered.append(event)

        return {"events": filtered[-20:]}

    # ─── Actuation Endpoints ──────────────────────────────────────────────

    @app.post("/v1/actuation/execute")
    async def actuation_execute(request: ActRequest):
        """Execute a physical action with DSE safety verification."""
        # Validate session
        session = sessions.get(request.session_id)
        if not session:
            raise HTTPException(status_code=401, detail="Invalid or expired session")

        agent_id = session["agent_id"]

        # Get current edge state for safety evaluation
        node_state = state_graph.get_node_state(request.node_id) or {}

        # Run DSE verification
        safety_result = safety_engine.verify(
            agent_id=agent_id,
            node_id=request.node_id,
            action_type=request.action_type,
            parameters=request.parameters,
            edge_state=node_state,
            signature=request.cryptographic_signature,
            session_active=True,
        )

        if safety_result["status"] != "cleared":
            return {
                "transaction_id": f"tx_{uuid.uuid4().hex[:12]}",
                "node_id": request.node_id,
                "status": "blocked",
                "safety_evaluation": {
                    "dse_status": safety_result["status"],
                    "reason": safety_result.get("reason", ""),
                    "rules_evaluated": safety_result.get("rules_evaluated", []),
                },
                "execution_details": {},
            }

        # Execute via HAL
        # Find device for this node
        node = state_graph.get_node(request.node_id)
        execution_details = {}

        if node and node.devices:
            device_id = list(node.devices.keys())[0]
            from neven.hal.bridge import CommandResult
            result = hardware_bridge.execute_command(
                device_id, request.action_type, request.parameters
            )
            execution_details = {
                "actuator_response_code": result.response_code,
                "message": result.message,
                "completed_at": datetime.utcnow().isoformat(),
                "execution_time_ms": result.execution_time_ms,
            }
        else:
            execution_details = {
                "actuator_response_code": "0x00_SUCCESS",
                "message": f"Action '{request.action_type}' executed (simulated)",
                "completed_at": datetime.utcnow().isoformat(),
            }

        # Record event
        events.append({
            "event_id": f"evt_{uuid.uuid4().hex[:8]}",
            "event_type": "actuation_completed",
            "node_id": request.node_id,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": {
                "action_type": request.action_type,
                "agent_id": agent_id,
                "status": "executed",
            },
        })

        return {
            "transaction_id": f"tx_{uuid.uuid4().hex[:12]}",
            "node_id": request.node_id,
            "status": "executed",
            "safety_evaluation": {
                "dse_status": "cleared",
                "rules_evaluated": safety_result.get("rules_evaluated", []),
            },
            "execution_details": execution_details,
        }

    # ─── Analytics Endpoints ──────────────────────────────────────────────

    @app.get("/v1/analytics/summary/{node_id}")
    async def analytics_summary(node_id: str):
        """Get complete analytics summary for a node."""
        return analytics_engine.get_summary(node_id)

    @app.get("/v1/analytics/foot-traffic/{node_id}")
    async def analytics_foot_traffic(node_id: str):
        """Get foot traffic data."""
        return analytics_engine.get_foot_traffic(node_id)

    @app.get("/v1/analytics/heatmap/{node_id}")
    async def analytics_heatmap(node_id: str):
        """Get spatial heatmap data."""
        return analytics_engine.get_heatmap(node_id)

    @app.get("/v1/analytics/dwell-time/{node_id}")
    async def analytics_dwell_time(node_id: str):
        """Get dwell time analytics."""
        return analytics_engine.get_dwell_times(node_id)

    @app.get("/v1/analytics/time-series/{node_id}")
    async def analytics_time_series(node_id: str, window: int = 300):
        """Get time series data."""
        return {"data": analytics_engine.get_time_series(node_id, window)}

    @app.get("/v1/analytics/events")
    async def analytics_events(limit: int = 50):
        """Get recent analytics events."""
        return {"events": analytics_engine.get_recent_events(limit)}

    # ─── Graph Endpoints ──────────────────────────────────────────────────

    @app.get("/v1/graph/topology")
    async def graph_topology():
        """Get the full state graph topology."""
        return state_graph.get_topology()

    @app.get("/v1/graph/nodes")
    async def graph_nodes():
        """Get all nodes in the state graph."""
        return {"nodes": state_graph.get_all_nodes()}

    @app.get("/v1/graph/nodes/{node_id}")
    async def graph_node_detail(node_id: str):
        """Get detailed state of a specific node."""
        return state_graph.query_spatial_state(node_id)

    @app.post("/v1/graph/nodes")
    async def graph_add_node(node: PhysicalNode):
        """Add a new node to the state graph."""
        node_id = state_graph.add_node(node)
        return {"node_id": node_id, "status": "created"}

    # ─── Device Endpoints ─────────────────────────────────────────────────

    @app.get("/v1/devices")
    async def list_devices():
        """List all registered devices."""
        return {"devices": hardware_bridge.get_all_devices()}

    @app.get("/v1/devices/{device_id}")
    async def device_status(device_id: str):
        """Get device status."""
        status = hardware_bridge.get_device_status(device_id)
        if not status:
            raise HTTPException(status_code=404, detail="Device not found")
        return status

    # ─── Safety Endpoints ─────────────────────────────────────────────────

    @app.get("/v1/safety/rules")
    async def safety_rules(node_id: Optional[str] = None):
        """Get registered safety rules."""
        return {"rules": safety_engine.get_rules(node_id)}

    @app.get("/v1/safety/violations")
    async def safety_violations(limit: int = 100):
        """Get recent safety violations."""
        return {"violations": safety_engine.get_violations(limit)}

    # ─── Perception Control ───────────────────────────────────────────────

    @app.post("/v1/perception/start")
    async def start_perception(source: str = "0", model: str = "yolov8n"):
        """Start the perception pipeline."""
        nonlocal perception_pipeline

        if perception_pipeline and perception_pipeline.is_running:
            return {"status": "already_running", "stats": perception_pipeline.stats}

        # Parse source
        try:
            src = int(source)
        except ValueError:
            src = source

        perception_pipeline = PerceptionPipeline(
            source=src,
            model_name=model,
            confidence_threshold=config.detection_confidence,
            frame_rate=config.frame_rate,
        )
        perception_pipeline.on_update(_on_perception_update)

        success = perception_pipeline.start()
        if success:
            app.state.perception_pipeline = perception_pipeline
            return {"status": "started", "source": str(source), "model": model}
        else:
            raise HTTPException(status_code=500, detail="Failed to start perception pipeline")

    @app.post("/v1/perception/stop")
    async def stop_perception():
        """Stop the perception pipeline."""
        nonlocal perception_pipeline
        if perception_pipeline:
            perception_pipeline.stop()
            perception_pipeline = None
            return {"status": "stopped"}
        return {"status": "not_running"}

    @app.get("/v1/perception/status")
    async def perception_status():
        """Get perception pipeline status."""
        if perception_pipeline and perception_pipeline.is_running:
            return {
                "status": "running",
                "stats": perception_pipeline.stats,
                "entities": len(perception_pipeline.current_entities),
            }
        return {"status": "stopped"}

    # ─── WebSocket Stream ─────────────────────────────────────────────────

    @app.websocket("/v1/stream")
    async def websocket_stream(websocket: WebSocket):
        """WebSocket endpoint for real-time event streaming."""
        await websocket.accept()
        try:
            last_event_count = len(events)
            while True:
                # Send new events
                if len(events) > last_event_count:
                    new_events = events[last_event_count:]
                    for event in new_events:
                        await websocket.send_json(event)
                    last_event_count = len(events)

                # Send periodic state update
                if perception_pipeline and perception_pipeline.is_running:
                    stats = perception_pipeline.stats
                    await websocket.send_json({
                        "type": "state_update",
                        "timestamp": datetime.utcnow().isoformat(),
                        "stats": stats,
                        "entities": len(perception_pipeline.current_entities),
                    })

                import asyncio
                await asyncio.sleep(1.0)

        except WebSocketDisconnect:
            pass

    # ─── Startup/Shutdown ─────────────────────────────────────────────────

    @app.on_event("startup")
    async def startup():
        logger.info("NEVEN API Server starting...")
        # Auto-start perception if configured
        if config.analytics_enabled:
            logger.info("Analytics engine ready")

    @app.on_event("shutdown")
    async def shutdown():
        nonlocal perception_pipeline
        if perception_pipeline:
            perception_pipeline.stop()
        hardware_bridge.disconnect_all()
        logger.info("NEVEN API Server shutdown complete")

    return app


def _get_dashboard_html() -> str:
    """Return the embedded dashboard HTML."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NEVEN TECH — Physical World Runtime</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0A0E1A;
            color: #E0E0E0;
            min-height: 100vh;
        }
        .header {
            background: linear-gradient(135deg, #0A0E1A 0%, #1a1f35 100%);
            border-bottom: 1px solid #7B2FBE33;
            padding: 20px 40px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .logo {
            font-size: 28px;
            font-weight: 800;
            background: linear-gradient(90deg, #00BFFF, #7B2FBE);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .subtitle { color: #888; font-size: 12px; letter-spacing: 2px; }
        .container { max-width: 1400px; margin: 0 auto; padding: 30px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-top: 20px; }
        .card {
            background: #111827;
            border: 1px solid #1f2937;
            border-radius: 12px;
            padding: 24px;
            transition: border-color 0.3s;
        }
        .card:hover { border-color: #00BFFF55; }
        .card h3 { color: #00BFFF; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; }
        .card .value { font-size: 36px; font-weight: 700; color: #fff; }
        .card .label { color: #6B7280; font-size: 13px; margin-top: 4px; }
        .status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 6px; }
        .status-dot.active { background: #10B981; animation: pulse 2s infinite; }
        .status-dot.inactive { background: #EF4444; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .btn {
            background: linear-gradient(135deg, #00BFFF, #7B2FBE);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            font-size: 14px;
        }
        .btn:hover { opacity: 0.9; }
        .events-list { max-height: 300px; overflow-y: auto; }
        .event-item {
            padding: 8px 12px;
            border-left: 3px solid #7B2FBE;
            margin-bottom: 8px;
            background: #0f1729;
            border-radius: 0 6px 6px 0;
            font-size: 13px;
        }
        .heatmap-canvas { width: 100%; height: 200px; border-radius: 8px; background: #0f1729; }
        #entityCount { color: #10B981; }
        .api-links { margin-top: 20px; }
        .api-links a { color: #00BFFF; text-decoration: none; margin-right: 20px; font-size: 14px; }
        .api-links a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <div class="logo">NEVEN</div>
            <div class="subtitle">AI &middot; SMART CITY SOLUTIONS</div>
        </div>
        <div>
            <span class="status-dot active" id="statusDot"></span>
            <span id="statusText">Connecting...</span>
        </div>
    </div>
    <div class="container">
        <div class="api-links">
            <a href="/docs">API Documentation</a>
            <a href="/redoc">API Reference</a>
            <a href="/health">Health Check</a>
            <a href="/v1/graph/topology">Graph Topology</a>
        </div>
        <div class="grid">
            <div class="card">
                <h3>Active Entities</h3>
                <div class="value" id="entityCount">0</div>
                <div class="label">Detected in real-time</div>
            </div>
            <div class="card">
                <h3>Foot Traffic</h3>
                <div class="value" id="trafficCount">0</div>
                <div class="label">Total entries today</div>
            </div>
            <div class="card">
                <h3>Current Occupancy</h3>
                <div class="value" id="occupancy">0</div>
                <div class="label">People in monitored zones</div>
            </div>
            <div class="card">
                <h3>Avg Dwell Time</h3>
                <div class="value" id="dwellTime">0s</div>
                <div class="label">Average time in zone</div>
            </div>
            <div class="card">
                <h3>Pipeline Status</h3>
                <div class="value" id="pipelineStatus">--</div>
                <div class="label">Perception engine state</div>
            </div>
            <div class="card">
                <h3>FPS</h3>
                <div class="value" id="fps">0</div>
                <div class="label">Frames per second</div>
            </div>
        </div>
        <div class="grid" style="margin-top: 20px;">
            <div class="card">
                <h3>Spatial Heatmap</h3>
                <canvas id="heatmapCanvas" class="heatmap-canvas"></canvas>
            </div>
            <div class="card">
                <h3>Recent Events</h3>
                <div class="events-list" id="eventsList"></div>
            </div>
            <div class="card">
                <h3>Controls</h3>
                <p style="margin-bottom: 12px; color: #6B7280; font-size: 13px;">Manage the perception pipeline</p>
                <button class="btn" onclick="startPipeline()">Start Perception</button>
                <button class="btn" onclick="stopPipeline()" style="background: #EF4444; margin-left: 8px;">Stop</button>
                <div style="margin-top: 16px; font-size: 12px; color: #6B7280;">
                    <p>Nodes: <span id="nodeCount">0</span> | Devices: <span id="deviceCount">0</span></p>
                    <p>Safety Rules: <span id="ruleCount">0</span> | Violations: <span id="violationCount">0</span></p>
                </div>
            </div>
        </div>
    </div>
    <script>
        async function fetchData() {
            try {
                // Health
                const health = await fetch('/health').then(r => r.json());
                document.getElementById('statusText').textContent = health.status;
                document.getElementById('statusDot').className = 'status-dot active';

                // Perception status
                const perc = await fetch('/v1/perception/status').then(r => r.json());
                document.getElementById('pipelineStatus').textContent = perc.status;
                if (perc.stats) {
                    document.getElementById('fps').textContent = (perc.stats.fps || 0).toFixed(1);
                    document.getElementById('entityCount').textContent = perc.entities || 0;
                }

                // Analytics
                const traffic = await fetch('/v1/analytics/foot-traffic/node_demo_camera').then(r => r.json());
                document.getElementById('trafficCount').textContent = traffic.total_entries || 0;
                document.getElementById('occupancy').textContent = traffic.current_occupancy || 0;
                document.getElementById('dwellTime').textContent = (traffic.average_dwell_time_seconds || 0) + 's';

                // Heatmap
                const heatmap = await fetch('/v1/analytics/heatmap/node_demo_camera').then(r => r.json());
                drawHeatmap(heatmap);

                // Graph
                const topology = await fetch('/v1/graph/topology').then(r => r.json());
                document.getElementById('nodeCount').textContent = topology.total_nodes || 0;
                document.getElementById('deviceCount').textContent = topology.total_devices || 0;

                // Safety
                const rules = await fetch('/v1/safety/rules').then(r => r.json());
                const violations = await fetch('/v1/safety/violations').then(r => r.json());
                document.getElementById('ruleCount').textContent = (rules.rules || []).length;
                document.getElementById('violationCount').textContent = (violations.violations || []).length;

                // Events
                const events = await fetch('/v1/analytics/events?limit=10').then(r => r.json());
                const list = document.getElementById('eventsList');
                list.innerHTML = (events.events || []).reverse().map(e =>
                    `<div class="event-item"><strong>${e.type || e.event_type}</strong> - ${e.node_id} <br><small>${e.timestamp}</small></div>`
                ).join('');

            } catch(e) {
                document.getElementById('statusText').textContent = 'Error';
                document.getElementById('statusDot').className = 'status-dot inactive';
            }
        }

        function drawHeatmap(data) {
            const canvas = document.getElementById('heatmapCanvas');
            const ctx = canvas.getContext('2d');
            canvas.width = canvas.offsetWidth;
            canvas.height = canvas.offsetHeight;
            ctx.fillStyle = '#0f1729';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            if (!data.cells || data.cells.length === 0) return;

            const res = data.resolution || 50;
            const cellW = canvas.width / res;
            const cellH = canvas.height / res;

            data.cells.forEach(cell => {
                const intensity = cell.intensity;
                const r = Math.floor(intensity * 255);
                const g = Math.floor((1 - intensity) * 100);
                const b = Math.floor((1 - intensity) * 255);
                ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${Math.max(0.3, intensity)})`;
                ctx.fillRect(cell.x * cellW, cell.y * cellH, cellW + 1, cellH + 1);
            });
        }

        async function startPipeline() {
            await fetch('/v1/perception/start', { method: 'POST' });
            fetchData();
        }

        async function stopPipeline() {
            await fetch('/v1/perception/stop', { method: 'POST' });
            fetchData();
        }

        // Poll every 2 seconds
        fetchData();
        setInterval(fetchData, 2000);
    </script>
</body>
</html>"""
