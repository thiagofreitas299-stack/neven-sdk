"""
NEVEN SDK — Autonomous Delivery Coordinator
============================================
Demonstrates the complete NEVEN workflow from the Blueprint:
An autonomous agent that monitors for delivery vehicles and
coordinates locker access with DSE safety validation.

Based on Blueprint Section 7.2 — adapted and extended.

Run:
    neven mock-server &
    python examples/delivery_coordinator.py
"""

import time
from neven import NevenClient
from neven.exceptions import NevenSafetyError
from neven.mock_server import MockServer


def main():
    server = MockServer(port=8424).start_background()

    client = NevenClient(api_key="nv_test_delivery", mock=True)
    client.base_url = "http://localhost:8424"
    HUB_NODE = "node_rj_keepithub_01"

    print("📦 NEVEN Autonomous Delivery Coordinator")
    print(f"   Monitoring: KEEPITHUB Hub #1 — Rio de Janeiro")
    print(f"   Waiting for delivery vehicle...\n")

    session = client.connect(
        agent_id="agent_delivery_bot_01",
        requested_nodes=[HUB_NODE],
        capabilities=["perception", "actuation"],
    )
    print(f"✅ Connected | Session: {session.session_id[:16]}...\n")

    # ─── Phase 1: Monitor for delivery vehicle ────────────────────────────
    print("[Phase 1] Monitoring physical space for delivery vehicle...")
    truck_detected = False
    for attempt in range(1, 6):
        state = client.perceive(
            node_id=HUB_NODE,
            target_objects=["vehicle", "person"],
            confidence_threshold=0.85,
        )
        entities = state["spatial_state"]["detected_entities"]
        vehicles = [e for e in entities if e["class"] == "vehicle"]
        people = [e for e in entities if e["class"] == "person"]

        print(f"  Scan {attempt}/5: {len(vehicles)} vehicles, {len(people)} people")

        if vehicles:
            v = vehicles[0]
            print(f"  🚛 VEHICLE DETECTED: {v['entity_id']} "
                  f"(confidence: {v['confidence']:.0%})")
            truck_detected = True
            break

        time.sleep(1.5)

    if not truck_detected:
        print("\n  ⏰ Vehicle not detected in monitoring window. Mission aborted.")
        client.disconnect()
        server.stop()
        return

    # ─── Phase 2: Prepare the hub ────────────────────────────────────────
    print("\n[Phase 2] Preparing hub for delivery...")
    client.display(
        HUB_NODE,
        "📦 DELIVERY IN PROGRESS — Please wait",
        duration=60,
    )
    print("  ✅ Status display updated")

    # ─── Phase 3: Unlock compartment (via DSE) ───────────────────────────
    print("\n[Phase 3] Unlocking compartment C-4 (subject to DSE validation)...")
    try:
        result = client.unlock(
            node_id=HUB_NODE,
            compartment_id="C-4",
            token="tok_delivery_truck_verified",
        )

        print(f"  🔓 Compartment C-4 UNLOCKED!")
        print(f"  TX: {result['transaction_id']}")
        print(f"  DSE Status: {result['safety_evaluation']['dse_status']}")

        for rule in result["safety_evaluation"].get("rules_evaluated", []):
            icon = "✅" if rule["result"] == "passed" else "❌"
            print(f"    {icon} {rule['rule_id']}: {rule['result']}")

        # ─── Phase 4: Confirm delivery ────────────────────────────────
        print("\n[Phase 4] Confirming delivery...")
        time.sleep(2)

        # Speak confirmation
        client.speak(
            HUB_NODE,
            "Entrega recebida com sucesso. Obrigado!",
            lang="pt-BR",
        )

        # Update display
        client.display(
            HUB_NODE,
            "✅ DELIVERY RECEIVED — Thank you!",
            duration=30,
        )
        print("  ✅ Delivery confirmed and logged")

    except NevenSafetyError as e:
        print(f"\n  🛡  DSE BLOCKED UNLOCK: {e.message}")
        print(f"  Rule violated: {e.rule_id}")
        print(f"  (This is correct behavior — physical safety is non-negotiable)")

        # Inform the delivery person
        client.display(
            HUB_NODE,
            "⚠️ Access denied. Please contact support: +55 21 9999-9999",
            duration=60,
        )

    # ─── Summary ─────────────────────────────────────────────────────────
    print("\n" + "="*50)
    print("DELIVERY COORDINATION COMPLETE")
    print("="*50)
    print(f"Hub: KEEPITHUB Hub #1, Rio de Janeiro")
    print(f"Session: {session.session_id[:16]}...")
    print(f"Scans performed: 5")
    print(f"Vehicle detected: {'Yes' if truck_detected else 'No'}")

    client.disconnect()
    server.stop()


if __name__ == "__main__":
    main()
