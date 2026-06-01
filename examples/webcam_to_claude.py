#!/usr/bin/env python3
"""
NEVEN TECH — Webcam to Claude in 3 Lines

This is the simplest possible integration: connect a local webcam to an AI agent
and get a semantic understanding of the physical world in real-time.

Prerequisites:
    pip install neven-tech
    neven serve  # Start the NEVEN server (in another terminal)

The 3-line magic:
    1. Create a client with your API key
    2. Perceive the physical world through a camera node
    3. Get a human-readable semantic description

That's it. Claude (or any AI agent) can now "see" and understand physical spaces.
"""

from neven import NevenClient

# ─── The Famous 3-Line Example ────────────────────────────────────────────────

client = NevenClient(api_key="nv_live_dev")                    # 1. Connect
state = client.perceive("local_webcam")                        # 2. Perceive
print(f"Claude sees: {state.semantic_description}")            # 3. Understand

# ─── That's it! Here's what happens under the hood: ───────────────────────────
#
# Line 1: Creates a NEVEN client with KAIS identity (auto-generated DID)
#          and establishes a secure session with the local server.
#
# Line 2: Queries the "local_webcam" node, which runs the perception pipeline
#          (YOLOv8 detection + DeepSORT tracking) and returns a SpatialState
#          with detected entities, occupancy, and semantic description.
#
# Line 3: Accesses the AI-generated semantic description of the physical space.
#          Example output: "A well-lit office with 3 people at workstations,
#          1 person walking toward the exit. Occupancy: moderate."
#
# Security: Every action is signed with HMAC-SHA256 via the KAIS identity system.
# Safety: All actuation commands pass through the DSE (Dual-pass Safety Engine).
# Privacy: LGPD/GDPR compliance via built-in anonymization helpers.

# ─── Extended Example (with full session lifecycle) ───────────────────────────

if __name__ == "__main__":
    import time

    # Full lifecycle demonstration
    with NevenClient(api_key="nv_live_dev") as client:
        # Connect with explicit session
        session = client.connect(
            agent_id="webcam_demo_agent",
            nodes=["node_demo_camera"],
            capabilities=["perception"],
        )
        print(f"Session: {session.session_id}")
        print(f"Agent DID: {client.identity.did}")

        # Continuous perception loop
        print("\nStarting perception loop (Ctrl+C to stop)...")
        try:
            for i in range(5):
                state = client.perceive("node_demo_camera")
                print(f"\n[{i+1}] {state.semantic_description}")
                print(f"    Entities: {len(state.spatial_state.detected_entities)}")
                print(f"    Occupancy: {state.spatial_state.occupancy_status}")
                time.sleep(2)
        except KeyboardInterrupt:
            pass

        print("\nDone! Check the audit trail:")
        for entry in client.identity.get_audit_trail()[-3:]:
            print(f"  [{entry['timestamp']}] {entry['action']} -> {entry['target_node']}")
