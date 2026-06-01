"""
NEVEN SDK — Physical Intelligence as a Service
===============================================
The OS for Autonomous Agents in the Physical World.

Connect any AI agent to cameras, screens, sensors, locks, and speakers
through a single unified API. No proprietary hardware required.

"Stripe didn't build a bank. Twilio didn't build a tower.
 NEVEN doesn't build hardware — NEVEN makes any hardware think."

Quick Start:
    from neven import NevenClient

    client = NevenClient(api_key="nv_live_xxx")
    session = client.connect(agent_id="my-agent", nodes=["node_sp_01"])
    state = client.perceive(node_id="node_sp_01")
    client.act(node_id="node_sp_01", action_type="display_message",
               parameters={"text": "Hello, Physical World!"})

Docs:    https://docs.neventech.com
GitHub:  https://github.com/thiagofreitas299-stack/neven-sdk
Website: https://neventech.com
"""

__version__ = "1.0.0"
__author__ = "NEVEN Technologies"
__email__ = "sdk@neventech.com"
__license__ = "MIT"

# Core client — primary interface
from neven.core.client import NevenClient

# Identity (KAIS)
from neven.core.identity import KAISIdentity as NevenIdentity

# Exceptions
from neven.core.exceptions import (
    NevenError,
    NevenAuthError,
    NevenConnectionError,
    NevenSafetyError,
    NevenNodeNotFoundError,
)

# Config
from neven.core.config import NevenConfig

# Models
from neven.core.models import (
    PhysicalNode,
    Device,
    DetectedEntity,
    SpatialState,
    ConnectResponse,
    PerceiveResponse,
    ActResponse,
)

__all__ = [
    # Client
    "NevenClient",
    # Identity
    "NevenIdentity",  # alias for KAISIdentity
    # Config
    "NevenConfig",
    # Exceptions
    "NevenError",
    "NevenAuthError",
    "NevenConnectionError",
    "NevenSafetyError",
    "NevenNodeNotFoundError",
    # Models
    "PhysicalNode",
    "Device",
    "DetectedEntity",
    "SpatialState",
    "ConnectResponse",
    "PerceiveResponse",
    "ActResponse",
]

# MCP Server
from neven.mcp.server import NevenMCPServer, NEVEN_MCP_TOOLS

# Tiers
from neven.core.tiers import TierName, TierLimits
