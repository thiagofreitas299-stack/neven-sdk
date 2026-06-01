"""
NEVEN SDK — Quickstart (5 minutes, no hardware needed)
=======================================================
Run this demo locally with the mock server:

    # Terminal 1:
    neven mock-server

    # Terminal 2:
    python examples/quickstart.py
"""

from neven import NevenClient
from neven.mock_server import MockServer

# ─── Start mock server in background ────────────────────────────────────────
print("Starting NEVEN mock server...")
server = MockServer(port=8422).start_background()
print("✅ Mock server running\n")

# ─── Create client ───────────────────────────────────────────────────────────
# For production: NevenClient(api_key="nv_live_xxx")
# For dev:        NevenClient(api_key="nv_test_xxx", mock=True)
client = NevenClient(api_key="nv_test_quickstart", mock=True)
client.base_url = "http://localhost:8422"

# ─── Step 1: Connect ─────────────────────────────────────────────────────────
print("1️⃣  Connecting to physical nodes...")
session = client.connect(
    agent_id="my-first-agent",
    requested_nodes=["node_rj_keepithub_01"],
    capabilities=["perception", "actuation"],
)
print(f"   Connected! Session: {session.session_id}\n")

# ─── Step 2: Perceive the physical world ────────────────────────────────────
print("2️⃣  Perceiving physical space...")
state = client.perceive(node_id="node_rj_keepithub_01")
entities = state["spatial_state"]["detected_entities"]
print(f"   Detected {len(entities)} entities:")
for e in entities:
    print(f"   → {e['class']} (confidence: {e['confidence']:.0%})")
print()

# ─── Step 3: Act on the physical world ──────────────────────────────────────
print("3️⃣  Displaying message on screen...")
result = client.display(
    node_id="node_rj_keepithub_01",
    text="Hello from NEVEN! 🌌",
    duration=5,
)
print(f"   ✅ Message displayed! TX: {result['transaction_id']}")
print(f"   🛡  DSE: {result['safety_evaluation']['dse_status']}\n")

# ─── Step 4: Count people ────────────────────────────────────────────────────
print("4️⃣  Counting people in space...")
people = client.get_people_count("node_rj_keepithub_01")
print(f"   👥 {people} people currently detected\n")

# ─── Done ────────────────────────────────────────────────────────────────────
print("✅ Quickstart complete! NEVEN is working.")
print("\nNext steps:")
print("  • Try: examples/shopping_guide.py")
print("  • Try: examples/delivery_coordinator.py")
print("  • Docs: https://docs.neventech.com")

client.disconnect()
server.stop()
