"""
NEVEN SDK — Shopping Guide Agent
==================================
An autonomous AI agent that detects when people look lost in a shopping
center and proactively offers help via the NEVEN physical runtime.

This example shows:
    - Real-time perception loop
    - Contextual actuation (speak + display)
    - Event-driven architecture with @client.on()

Run:
    neven mock-server &
    python examples/shopping_guide.py
"""

import time
from neven import NevenClient
from neven.api.mock_server import MockServer

# In production, this would call your LLM to generate a response
def generate_greeting(entity_count: int, temperature: float) -> str:
    if entity_count == 0:
        return "Bem-vindo ao shopping! Em que posso ajudar?"
    elif entity_count < 3:
        return f"Olá! Posso te ajudar a encontrar algo hoje?"
    else:
        return f"Atenção: área movimentada. Informações no painel central."


def main():
    # Start mock server
    server = MockServer(port=8423).start_background()

    client = NevenClient(api_key="nv_test_shopping", mock=True)
    client.base_url = "http://localhost:8423"
    NODE = "node_sp_iguatemi_01"

    print("🛍  NEVEN Shopping Guide Agent started")
    print(f"   Monitoring: {NODE}")
    print("   Press Ctrl+C to stop\n")

    session = client.connect(
        agent_id="shopping-guide-v1",
        requested_nodes=[NODE],
        capabilities=["perception", "actuation"],
    )
    print(f"✅ Connected | Session: {session.session_id[:16]}...\n")

    # ─── Main perception loop ──────────────────────────────────────────────
    iteration = 0
    try:
        while iteration < 5:  # In production: while True
            iteration += 1
            print(f"[Scan {iteration}] Perceiving space...")

            state = client.perceive(
                node_id=NODE,
                target_objects=["person"],
                confidence_threshold=0.80,
            )

            entities = state["spatial_state"]["detected_entities"]
            telemetry = state["spatial_state"]["environmental_telemetry"]
            people = [e for e in entities if e["class"] == "person"]

            print(f"   👥 {len(people)} people | 🌡 {telemetry['temperature_celsius']}°C")

            if people:
                # Generate contextual response
                message = generate_greeting(len(people), telemetry["temperature_celsius"])

                # Display + speak simultaneously
                display_result = client.display(NODE, message, duration=8)
                speak_result = client.speak(NODE, message, lang="pt-BR")

                print(f"   📺 Displayed: '{message}'")
                print(f"   🔊 Spoken: TX={speak_result['transaction_id'][:12]}")

                # Check for anomalies
                anomalies = client.detect_anomalies(NODE)
                if anomalies:
                    print(f"   ⚠️  Anomaly detected: {anomalies[0]['class']}")
                    alert = f"ALERTA: {anomalies[0].get('description', 'Situação incomum detectada')}"
                    client.display(NODE, alert, duration=30)

            time.sleep(3)

    except KeyboardInterrupt:
        print("\n\nStopping agent...")

    finally:
        client.disconnect()
        server.stop()
        print("✅ Agent stopped cleanly.")


if __name__ == "__main__":
    main()
