"""
NEVEN Physical World State Graph (PWSG)

The PWSG represents the physical world as a Directed Acyclic Graph (DAG) of
spatial entities, containment relationships, and semantic attributes.

Structure:
    City -> District -> Facility -> Device (Camera, Sensor, Locker)

Each node has a state vector containing properties and semantic embeddings.
State changes propagate upward through the containment hierarchy.
"""

import time
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict

from neven.core.models import (
    PhysicalNode,
    Device,
    DetectedEntity,
    NodeType,
    DeviceStatus,
)

logger = logging.getLogger("neven.graph")


class GraphNode:
    """Internal representation of a node in the PWSG."""

    def __init__(self, node: PhysicalNode):
        self.node = node
        self.state: Dict[str, Any] = {
            "status": "active",
            "last_updated": datetime.utcnow().isoformat(),
            "entities": [],
            "occupancy": 0,
            "entity_count": 0,
        }
        self.children: Set[str] = set()
        self.devices: Dict[str, Device] = {}
        self.entities: List[DetectedEntity] = []

    @property
    def node_id(self) -> str:
        return self.node.node_id

    def update_state(self, key: str, value: Any) -> None:
        """Update a state attribute."""
        self.state[key] = value
        self.state["last_updated"] = datetime.utcnow().isoformat()


class PhysicalWorldStateGraph:
    """
    The Physical World State Graph (PWSG).

    Manages spatial entities as a hierarchical graph with:
    - Containment relationships (city -> district -> hub -> device)
    - Real-time state tracking per node
    - Entity detection and tracking
    - State propagation up the hierarchy
    """

    def __init__(self):
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: Dict[str, Set[str]] = defaultdict(set)  # parent -> children
        self._reverse_edges: Dict[str, str] = {}  # child -> parent
        self._devices: Dict[str, Device] = {}
        self._entity_index: Dict[str, str] = {}  # entity_id -> node_id

    def add_node(self, node: PhysicalNode) -> str:
        """Add a physical node to the graph."""
        graph_node = GraphNode(node)
        self._nodes[node.node_id] = graph_node

        # Establish parent-child relationship
        if node.parent_node_id and node.parent_node_id in self._nodes:
            self._edges[node.parent_node_id].add(node.node_id)
            self._reverse_edges[node.node_id] = node.parent_node_id
            self._nodes[node.parent_node_id].children.add(node.node_id)

        logger.info(f"Node added to PWSG: {node.node_id} ({node.name}, type={node.type})")
        return node.node_id

    def remove_node(self, node_id: str) -> bool:
        """Remove a node and its relationships from the graph."""
        if node_id not in self._nodes:
            return False

        # Remove from parent
        parent_id = self._reverse_edges.pop(node_id, None)
        if parent_id and parent_id in self._nodes:
            self._edges[parent_id].discard(node_id)
            self._nodes[parent_id].children.discard(node_id)

        # Remove children edges
        for child_id in list(self._edges.get(node_id, set())):
            self._reverse_edges.pop(child_id, None)
        self._edges.pop(node_id, None)

        del self._nodes[node_id]
        logger.info(f"Node removed from PWSG: {node_id}")
        return True

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get a graph node by ID."""
        return self._nodes.get(node_id)

    def get_node_state(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get the current state of a node."""
        node = self._nodes.get(node_id)
        if node:
            return node.state.copy()
        return None

    def get_children(self, node_id: str) -> List[str]:
        """Get all child node IDs."""
        return list(self._edges.get(node_id, set()))

    def get_parent(self, node_id: str) -> Optional[str]:
        """Get the parent node ID."""
        return self._reverse_edges.get(node_id)

    def register_device(self, device: Device) -> str:
        """Register a physical device under a node."""
        self._devices[device.device_id] = device

        if device.node_id in self._nodes:
            self._nodes[device.node_id].devices[device.device_id] = device
            logger.info(
                f"Device registered: {device.device_id} ({device.protocol}) -> {device.node_id}"
            )
        return device.device_id

    def update_device_status(self, device_id: str, status: DeviceStatus) -> None:
        """Update device connection status."""
        if device_id in self._devices:
            self._devices[device_id].status = status
            self._devices[device_id].last_heartbeat = datetime.utcnow()

    def update_entities(self, node_id: str, entities: List[DetectedEntity]) -> None:
        """
        Update detected entities for a node and propagate state changes.

        This is the core state update function called by the perception pipeline.
        """
        node = self._nodes.get(node_id)
        if not node:
            logger.warning(f"Cannot update entities: node {node_id} not found")
            return

        # Update node entities
        node.entities = entities
        node.state["entities"] = [e.model_dump() for e in entities]
        node.state["entity_count"] = len(entities)
        node.state["last_updated"] = datetime.utcnow().isoformat()

        # Calculate occupancy
        person_count = sum(1 for e in entities if e.class_label.value == "person")
        node.state["occupancy"] = person_count
        node.state["occupancy_status"] = "occupied" if person_count > 0 else "empty"

        # Update entity index
        for entity in entities:
            self._entity_index[entity.entity_id] = node_id

        # Propagate state upward
        self._propagate_state_upward(node_id)

    def _propagate_state_upward(self, node_id: str) -> None:
        """Propagate state changes up the containment hierarchy."""
        parent_id = self._reverse_edges.get(node_id)
        if not parent_id or parent_id not in self._nodes:
            return

        parent = self._nodes[parent_id]

        # Aggregate child states
        total_entities = 0
        total_occupancy = 0
        for child_id in self._edges.get(parent_id, set()):
            child = self._nodes.get(child_id)
            if child:
                total_entities += child.state.get("entity_count", 0)
                total_occupancy += child.state.get("occupancy", 0)

        parent.state["total_entities_in_subtree"] = total_entities
        parent.state["total_occupancy_in_subtree"] = total_occupancy
        parent.state["last_updated"] = datetime.utcnow().isoformat()

        # Continue propagation
        self._propagate_state_upward(parent_id)

    def query_spatial_state(self, node_id: str) -> Dict[str, Any]:
        """Query the full spatial state of a node including entities."""
        node = self._nodes.get(node_id)
        if not node:
            return {"error": f"Node {node_id} not found"}

        return {
            "node_id": node_id,
            "name": node.node.name,
            "type": node.node.type.value,
            "state": node.state,
            "devices": {
                did: {"status": d.status.value, "protocol": d.protocol.value}
                for did, d in node.devices.items()
            },
            "children": list(node.children),
            "entity_count": len(node.entities),
        }

    def get_all_nodes(self) -> List[Dict[str, Any]]:
        """Get summary of all nodes in the graph."""
        return [
            {
                "node_id": n.node_id,
                "name": n.node.name,
                "type": n.node.type.value,
                "status": n.state.get("status", "unknown"),
                "entity_count": n.state.get("entity_count", 0),
                "children_count": len(n.children),
            }
            for n in self._nodes.values()
        ]

    def get_topology(self) -> Dict[str, Any]:
        """Get the full graph topology."""
        roots = [
            nid for nid in self._nodes if nid not in self._reverse_edges
        ]
        return {
            "total_nodes": len(self._nodes),
            "total_devices": len(self._devices),
            "root_nodes": roots,
            "edges": {k: list(v) for k, v in self._edges.items()},
        }

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def device_count(self) -> int:
        return len(self._devices)
