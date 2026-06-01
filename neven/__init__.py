"""
NEVEN SDK — Physical Intelligence as a Service
===============================================
Connect any AI agent to the physical world.

"Stripe didn't build a bank. Twilio didn't build a tower.
 NEVEN doesn't build hardware — NEVEN makes any hardware think."

Quick Start:
    from neven import NevenClient

    client = NevenClient(api_key="nv_live_xxx")
    session = client.connect(agent_id="my-agent", requested_nodes=["node_sp_01"])
    state = client.perceive(node_id="node_sp_01")
    client.act(node_id="node_sp_01", action_type="display_message",
               parameters={"text": "Hello, Physical World!"})

Docs: https://docs.neventech.com
"""

__version__ = "1.0.0"
__author__ = "NEVEN Technologies"
__email__ = "sdk@neventech.com"
__license__ = "MIT"

from neven.client import NevenClient
from neven.identity import NevenIdentity
from neven.exceptions import (
    NevenError,
    NevenAuthError,
    NevenConnectionError,
    NevenSafetyError,
    NevenNodeNotFoundError,
)

__all__ = [
    "NevenClient",
    "NevenIdentity",
    "NevenError",
    "NevenAuthError",
    "NevenConnectionError",
    "NevenSafetyError",
    "NevenNodeNotFoundError",
]
