"""
NEVEN Data Models
Pydantic schemas for all API requests, responses, and internal data structures.
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field
import uuid


# ─── Enums ───────────────────────────────────────────────────────────────────

class NodeType(str, Enum):
    CITY = "city"
    DISTRICT = "district"
    HUB = "hub"
    CAMERA = "camera"
    LOCKER = "locker"
    SCREEN = "screen"
    SENSOR = "sensor"


class DeviceProtocol(str, Enum):
    RTSP = "RTSP"
    MQTT = "MQTT"
    MODBUS = "MODBUS"
    HTTP = "HTTP"
    ONVIF = "ONVIF"
    WEBCAM = "WEBCAM"


class DeviceStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    CONNECTING = "connecting"


class EntityClass(str, Enum):
    PERSON = "person"
    VEHICLE = "vehicle"
    PACKAGE = "package"
    OBSTACLE = "obstacle"
    UNKNOWN = "unknown"


class EventType(str, Enum):
    ENTITY_ENTERED = "entity_entered"
    ENTITY_EXITED = "entity_exited"
    ANOMALY_DETECTED = "anomaly_detected"
    STATE_CHANGED = "state_changed"
    ACTUATION_COMPLETED = "actuation_completed"
    SAFETY_VIOLATION = "safety_violation"


class DSEStatus(str, Enum):
    CLEARED = "cleared"
    BLOCKED = "blocked"
    REJECTED = "rejected"


class AnomalySeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ─── Core Entity Models ──────────────────────────────────────────────────────

class SpatialPosition(BaseModel):
    """Spatial coordinates for an entity."""
    x: float = 0.0
    y: float = 0.0
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    h3_index: Optional[str] = None


class BoundingBox(BaseModel):
    """Bounding box coordinates."""
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def centroid(self) -> tuple:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    @property
    def area(self) -> float:
        return (self.x2 - self.x1) * (self.y2 - self.y1)


class DetectedEntity(BaseModel):
    """A detected entity in the physical world."""
    entity_id: str = Field(default_factory=lambda: f"ent_{uuid.uuid4().hex[:8]}")
    class_label: EntityClass = EntityClass.UNKNOWN
    confidence: float = 0.0
    bbox: Optional[BoundingBox] = None
    spatial_position: Optional[SpatialPosition] = None
    velocity: Optional[Dict[str, float]] = None
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    track_id: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Anomaly(BaseModel):
    """A detected anomaly in the physical space."""
    anomaly_id: str = Field(default_factory=lambda: f"anom_{uuid.uuid4().hex[:8]}")
    anomaly_class: str
    description: str
    severity: AnomalySeverity = AnomalySeverity.LOW
    confidence: float = 0.0
    spatial_position: Optional[SpatialPosition] = None
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    duration_seconds: Optional[float] = None


# ─── Node & Device Models ────────────────────────────────────────────────────

class PhysicalNode(BaseModel):
    """A node in the Physical World State Graph."""
    node_id: str = Field(default_factory=lambda: f"node_{uuid.uuid4().hex[:12]}")
    parent_node_id: Optional[str] = None
    name: str
    type: NodeType
    h3_index: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Device(BaseModel):
    """A physical device connected to the NEVEN network."""
    device_id: str = Field(default_factory=lambda: f"dev_{uuid.uuid4().hex[:12]}")
    node_id: str
    name: str = ""
    protocol: DeviceProtocol
    connection_uri: str
    status: DeviceStatus = DeviceStatus.OFFLINE
    config: Dict[str, Any] = Field(default_factory=dict)
    last_heartbeat: Optional[datetime] = None


# ─── API Request/Response Models ─────────────────────────────────────────────

class ConnectRequest(BaseModel):
    """Request to establish a session with NEVEN."""
    agent_id: str
    requested_nodes: List[str] = Field(default_factory=list)
    capabilities_required: List[str] = Field(default_factory=lambda: ["perception"])
    session_timeout_seconds: int = 3600


class ConnectResponse(BaseModel):
    """Response after establishing a session."""
    session_id: str = Field(default_factory=lambda: f"sess_{uuid.uuid4().hex[:12]}")
    status: str = "connected"
    authorized_nodes: Dict[str, List[str]] = Field(default_factory=dict)
    deterministic_rules_enforced: List[str] = Field(default_factory=list)
    websocket_stream_url: Optional[str] = None


class PerceiveRequest(BaseModel):
    """Request to query spatial state."""
    session_id: str
    node_id: str
    query_type: str = "semantic_state"
    parameters: Dict[str, Any] = Field(default_factory=dict)


class SpatialState(BaseModel):
    """The spatial state of a physical node."""
    occupancy_status: str = "empty"
    detected_entities: List[DetectedEntity] = Field(default_factory=list)
    anomalies: List[Anomaly] = Field(default_factory=list)
    environmental_telemetry: Dict[str, Any] = Field(default_factory=dict)


class PerceiveResponse(BaseModel):
    """Response with spatial perception data."""
    node_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    spatial_state: SpatialState = Field(default_factory=SpatialState)


class ActRequest(BaseModel):
    """Request to execute a physical action."""
    session_id: str
    node_id: str
    action_type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    cryptographic_signature: Optional[str] = None


class SafetyEvaluation(BaseModel):
    """Result of the DSE safety evaluation."""
    dse_status: DSEStatus = DSEStatus.CLEARED
    rules_evaluated: List[Dict[str, str]] = Field(default_factory=list)
    reason: Optional[str] = None


class ActResponse(BaseModel):
    """Response after an actuation request."""
    transaction_id: str = Field(default_factory=lambda: f"tx_{uuid.uuid4().hex[:12]}")
    node_id: str
    status: str = "executed"
    safety_evaluation: SafetyEvaluation = Field(default_factory=SafetyEvaluation)
    execution_details: Dict[str, Any] = Field(default_factory=dict)


class SubscribeRequest(BaseModel):
    """Request to subscribe to spatial events."""
    session_id: str
    filters: List[Dict[str, Any]] = Field(default_factory=list)


class SpatialEvent(BaseModel):
    """A real-time spatial event."""
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    event_type: EventType
    node_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: Dict[str, Any] = Field(default_factory=dict)


# ─── Analytics Models ────────────────────────────────────────────────────────

class FootTrafficData(BaseModel):
    """Foot traffic analytics for a node."""
    node_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    total_count: int = 0
    entries: int = 0
    exits: int = 0
    current_occupancy: int = 0
    peak_occupancy: int = 0
    average_dwell_time_seconds: float = 0.0


class HeatmapCell(BaseModel):
    """A single cell in a spatial heatmap."""
    x: int
    y: int
    intensity: float = 0.0


class HeatmapData(BaseModel):
    """Heatmap analytics data."""
    node_id: str
    resolution: int = 50
    width: int = 0
    height: int = 0
    cells: List[HeatmapCell] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class AnalyticsSummary(BaseModel):
    """Summary analytics for a node."""
    node_id: str
    period_start: datetime
    period_end: datetime
    total_detections: int = 0
    unique_tracks: int = 0
    foot_traffic: Optional[FootTrafficData] = None
    anomalies_detected: int = 0
    average_confidence: float = 0.0
