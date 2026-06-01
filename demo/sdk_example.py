#!/usr/bin/env python3
"""
NEVEN SDK Usage Example
========================

Demonstrates how an AI agent uses the NEVEN SDK to:
1. Connect to the Physical World Protocol
2. Perceive spatial state (detect people, objects)
3. Execute safe physical actions (unlock locker)
4. Subscribe to real-time events

Prerequisites:
    - NEVEN server running: neven serve (or python demo/run_demo.py)
    - Server at http://localhost:8420
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import neven


def main():
    print("=" * 60)
    print("  NEVEN SDK Example — AI Agent Integration")
    print("=" * 60)
    print()

    # ─── Step 1: Initialize Client ───────────────────────────────────────
    print("[1] Initializing NEVEN Client...")
    client = neven.Client(
        api_key="nv_dev_demo_key",
        agent_private_key="demo_agent_secret_key",
        base_url="http://localhost:8420",
    )
    print("    Client initialized.")
    print()

    # ─── Step 2: Connect to Physical World ───────────────────────────────
    print("[2] Connecting to NEVEN Physical World Protocol...")
    try:
        session = client.connect(
            agent_id="demo_agent",
            nodes=["node_demo_camera", "node_demo_hub"],
            capabilities=["perception", "actuation"],
        )
        print(f"    Connected! Session ID: {session.session_id}")
        print(f"    Authorized nodes: {list(session.authorized_nodes.keys())}")
        print(f"    Safety rules enforced: {session.deterministic_rules_enforced}")
    except ConnectionError as e:
        print(f"    [ERROR] {e}")
        print("    Make sure the server is running: neven serve")
        sys.exit(1)
    print()

    # ─── Step 3: Perceive Spatial State ──────────────────────────────────
    print("[3] Querying spatial state of node_demo_camera...")
    for attempt in range(3):
        state = client.perceive(
            node_id="node_demo_camera",
            query_type="semantic_state",
            parameters={"target_objects": ["person", "vehicle"]},
        )
        entities = state.spatial_state.detected_entities
        print(f"    Attempt {attempt + 1}: Detected {len(entities)} entities")

        for entity in entities[:5]:
            print(f"      - {entity.class_label.value} (confidence: {entity.confidence:.2f})")

        if entities:
            break
        time.sleep(2)
    print()

    # ─── Step 4: Execute Physical Action ─────────────────────────────────
    print("[4] Executing physical action (unlock compartment)...")
    result = client.act(
        node_id="node_demo_hub",
        action_type="unlock_compartment",
        parameters={
            "compartment_id": "C-4",
            "verification_token": "tok_demo_verified",
        },
    )
    print(f"    Transaction ID: {result.transaction_id}")
    print(f"    Status: {result.status}")
    print(f"    DSE Status: {result.safety_evaluation.dse_status.value}")
    if result.safety_evaluation.rules_evaluated:
        print(f"    Rules evaluated:")
        for rule in result.safety_evaluation.rules_evaluated:
            print(f"      - {rule['rule_id']}: {rule['result']}")
    print()

    # ─── Step 5: Subscribe to Events ─────────────────────────────────────
    print("[5] Subscribing to real-time events...")

    event_count = [0]

    def on_event(event):
        event_count[0] += 1
        print(f"    Event #{event_count[0]}: {event.event_type.value} on {event.node_id}")

    sub_id = client.subscribe(
        node_id="node_demo_camera",
        events=["entity_entered", "anomaly_detected"],
        callback=on_event,
    )
    print(f"    Subscription active: {sub_id}")
    print("    Listening for 10 seconds...")

    time.sleep(10)

    # ─── Cleanup ─────────────────────────────────────────────────────────
    print()
    print("[6] Disconnecting...")
    client.disconnect()
    print("    Done!")
    print()
    print(f"    Total events received: {event_count[0]}")
    print()
    print("=" * 60)
    print("  Demo complete! Visit http://localhost:8420 for the dashboard.")
    print("=" * 60)


if __name__ == "__main__":
    main()
