"""
NEVEN Client — The primary interface for AI agents to interact with the physical world.

Provides the four core operations:
    - neven.connect()   — Establish a session with physical infrastructure
    - neven.perceive()  — Query real-time spatial state
    - neven.act()       — Execute safe physical actions
    - neven.subscribe() — Stream real-time events
"""

import hmac
import hashlib
import time
import json
import uuid
import threading
import logging
from typing import Any, Callable, Dict, List, Optional

import requests

from neven.core.config import NevenConfig
from neven.core.models import (
    ConnectRequest,
    ConnectResponse,
    PerceiveRequest,
    PerceiveResponse,
    ActRequest,
    ActResponse,
    SubscribeRequest,
    SpatialEvent,
)

logger = logging.getLogger("neven.client")


class NevenClient:
    """
    NEVEN Client — Connect AI agents to the physical world.

    Example:
        client = NevenClient(api_key="nv_live_...", agent_private_key="secret")
        session = client.connect(agent_id="my_agent", nodes=["node_01"])
        state = client.perceive(node_id="node_01")
        result = client.act(node_id="node_01", action_type="unlock", parameters={...})
    """

    def __init__(
        self,
        api_key: str = "",
        agent_private_key: str = "",
        base_url: str = "http://localhost:8420",
        config: Optional[NevenConfig] = None,
    ):
        self.config = config or NevenConfig.from_env()
        self.api_key = api_key or self.config.api_key
        self.agent_private_key = (agent_private_key or self.config.agent_private_key).encode("utf-8")
        self.base_url = base_url or self.config.base_url
        self.session_id: Optional[str] = None
        self._subscriptions: Dict[str, threading.Thread] = {}
        self._running = True

    def _generate_signature(self, timestamp: int, payload: str) -> str:
        """Generate HMAC-SHA256 cryptographic signature for non-repudiation."""
        message = f"{timestamp}:{payload}".encode("utf-8")
        signature = hmac.new(self.agent_private_key, message, hashlib.sha256).hexdigest()
        return signature

    def _get_headers(self, payload_str: str = "") -> Dict[str, str]:
        """Build authenticated request headers."""
        timestamp = int(time.time())
        signature = self._generate_signature(timestamp, payload_str)
        return {
            "Authorization": f"Bearer {self.api_key}",
            "X-Neven-Signature": signature,
            "X-Neven-Timestamp": str(timestamp),
            "Content-Type": "application/json",
        }

    def _request(self, method: str, endpoint: str, payload: Optional[Dict] = None) -> Dict:
        """Make an authenticated request to the NEVEN API."""
        url = f"{self.base_url}{endpoint}"
        payload_str = json.dumps(payload) if payload else ""
        headers = self._get_headers(payload_str)

        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method == "POST":
                response = requests.post(url, data=payload_str, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            if response.status_code >= 400:
                raise Exception(
                    f"NEVEN API error ({response.status_code}): {response.text}"
                )
            return response.json()
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Cannot connect to NEVEN server at {self.base_url}. "
                "Is the server running? Start with: neven serve"
            )

    def connect(
        self,
        agent_id: str,
        nodes: Optional[List[str]] = None,
        capabilities: Optional[List[str]] = None,
        timeout_seconds: int = 3600,
    ) -> ConnectResponse:
        """
        Establish a session with the NEVEN Physical World Protocol.

        Args:
            agent_id: Unique identifier for the AI agent
            nodes: List of node IDs to request access to
            capabilities: Required capabilities (perception, actuation)
            timeout_seconds: Session timeout in seconds

        Returns:
            ConnectResponse with session_id and authorized nodes
        """
        request = ConnectRequest(
            agent_id=agent_id,
            requested_nodes=nodes or [],
            capabilities_required=capabilities or ["perception"],
            session_timeout_seconds=timeout_seconds,
        )

        data = self._request("POST", "/v1/session/connect", request.model_dump())
        response = ConnectResponse(**data)
        self.session_id = response.session_id
        logger.info(f"Connected to NEVEN. Session: {self.session_id}")
        return response

    def perceive(
        self,
        node_id: str,
        query_type: str = "semantic_state",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> PerceiveResponse:
        """
        Query the real-time spatial state of a physical node.

        Args:
            node_id: The physical node to query
            query_type: Type of query (semantic_state, heatmap, analytics)
            parameters: Additional query parameters

        Returns:
            PerceiveResponse with spatial state data
        """
        if not self.session_id:
            raise RuntimeError("No active session. Call connect() first.")

        request = PerceiveRequest(
            session_id=self.session_id,
            node_id=node_id,
            query_type=query_type,
            parameters=parameters or {},
        )

        data = self._request("POST", "/v1/perception/query", request.model_dump())
        return PerceiveResponse(**data)

    def act(
        self,
        node_id: str,
        action_type: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> ActResponse:
        """
        Execute a physical action, subject to DSE safety clearance.

        Args:
            node_id: Target physical node
            action_type: Type of action to execute
            parameters: Action parameters

        Returns:
            ActResponse with safety evaluation and execution details
        """
        if not self.session_id:
            raise RuntimeError("No active session. Call connect() first.")

        request = ActRequest(
            session_id=self.session_id,
            node_id=node_id,
            action_type=action_type,
            parameters=parameters or {},
        )

        data = self._request("POST", "/v1/actuation/execute", request.model_dump())
        return ActResponse(**data)

    def subscribe(
        self,
        node_id: str,
        events: Optional[List[str]] = None,
        callback: Optional[Callable[[SpatialEvent], None]] = None,
    ) -> str:
        """
        Subscribe to real-time spatial events from a node.

        Args:
            node_id: The node to subscribe to
            events: List of event types to filter
            callback: Function to call when events are received

        Returns:
            Subscription ID
        """
        if not self.session_id:
            raise RuntimeError("No active session. Call connect() first.")

        sub_id = f"sub_{uuid.uuid4().hex[:8]}"
        logger.info(f"Subscribed to events on {node_id}: {events}")

        # For local mode, we poll the events endpoint
        if callback:
            def _poll_events():
                while self._running:
                    try:
                        data = self._request(
                            "POST",
                            "/v1/perception/events",
                            {
                                "session_id": self.session_id,
                                "node_id": node_id,
                                "event_types": events or [],
                            },
                        )
                        for event_data in data.get("events", []):
                            event = SpatialEvent(**event_data)
                            callback(event)
                    except Exception as e:
                        logger.debug(f"Event poll error: {e}")
                    time.sleep(1.0)

            thread = threading.Thread(target=_poll_events, daemon=True)
            thread.start()
            self._subscriptions[sub_id] = thread

        return sub_id

    def unsubscribe(self, subscription_id: str) -> None:
        """Cancel an event subscription."""
        if subscription_id in self._subscriptions:
            del self._subscriptions[subscription_id]
            logger.info(f"Unsubscribed: {subscription_id}")

    def disconnect(self) -> None:
        """Close the session and clean up resources."""
        self._running = False
        self.session_id = None
        self._subscriptions.clear()
        logger.info("Disconnected from NEVEN.")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.disconnect()


# ─── Module-level convenience functions ──────────────────────────────────────

_default_client: Optional[NevenClient] = None


def _get_client() -> NevenClient:
    global _default_client
    if _default_client is None:
        _default_client = NevenClient()
    return _default_client


def connect(agent_id: str, nodes: Optional[List[str]] = None, **kwargs) -> ConnectResponse:
    """Module-level connect function."""
    return _get_client().connect(agent_id=agent_id, nodes=nodes, **kwargs)


def perceive(node_id: str, **kwargs) -> PerceiveResponse:
    """Module-level perceive function."""
    return _get_client().perceive(node_id=node_id, **kwargs)


def act(node_id: str, action_type: str, parameters: Optional[Dict] = None, **kwargs) -> ActResponse:
    """Module-level act function."""
    return _get_client().act(node_id=node_id, action_type=action_type, parameters=parameters, **kwargs)


def subscribe(node_id: str, events: Optional[List[str]] = None, callback=None, **kwargs) -> str:
    """Module-level subscribe function."""
    return _get_client().subscribe(node_id=node_id, events=events, callback=callback, **kwargs)
