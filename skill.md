---
name: neven
version: 1.0.0
description: Physical Intelligence as a Service — Connect any AI agent to the physical world. Perceive real spaces, act on physical hardware, orchestrate multi-agent workflows.
homepage: https://neventech.com
metadata:
  neven:
    emoji: "🌌"
    category: physical-ai
    api_base: https://api.neventech.com/v1
    sdk_install: pip install neven-sdk
    mock_mode: NEVEN_MOCK=1
---

# NEVEN SDK

**The Physical World Runtime for AI Agents.**

Connect any AI agent to cameras, screens, sensors, locks, and speakers in the real world — through a single unified API. No proprietary hardware required.

> "Stripe didn't build a bank. Twilio didn't build a tower.
> NEVEN doesn't build hardware — NEVEN makes any hardware think."

---

## Install

```bash
pip install neven-sdk
```

## Quick Start (no hardware needed)

```bash
# Terminal 1: Start mock server
neven mock-server

# Terminal 2: Run demo
neven demo
```

## Core API (3 methods)

### 1. Connect to physical nodes

```python
from neven import NevenClient

client = NevenClient(api_key="nv_live_YOUR_KEY")
# For development: NevenClient(api_key="nv_test_xxx", mock=True)

session = client.connect(
    agent_id="my-agent-01",
    requested_nodes=["node_sp_iguatemi_01"],
    capabilities=["perception", "actuation"]
)
```

### 2. Perceive the physical world

```python
state = client.perceive(node_id="node_sp_iguatemi_01")

# What's in the space?
entities = state["spatial_state"]["detected_entities"]
for entity in entities:
    print(f"{entity['class']} at {entity['spatial_position']['h3_index']}")

# Environmental data
temp = state["spatial_state"]["environmental_telemetry"]["temperature_celsius"]
```

### 3. Act on the physical world (DSE-protected)

```python
# Display a message on screen
client.display("node_sp_iguatemi_01", "Hello! How can I help?", duration=10)

# Speak via speaker
client.speak("node_sp_iguatemi_01", "Bem-vindo!", lang="pt-BR")

# Unlock smart locker (subject to DSE safety validation)
try:
    client.unlock("node_rj_keepithub_01", compartment_id="C-4")
except NevenSafetyError as e:
    print(f"DSE blocked: {e.message}")  # Physical safety is non-negotiable
```

---

## Supported Actions

| Action | Description |
|--------|-------------|
| `display_message` | Show text/media on screen |
| `speak` | Text-to-speech via node speaker |
| `unlock_compartment` | Open smart locker compartment |
| `set_led` | Control LED indicators |
| `read_sensor` | Read sensor value |
| `trigger_alarm` | Activate/deactivate alarm |
| `process_payment` | Initiate payment flow |

---

## KAIS Identity

Every agent and physical node in NEVEN has a cryptographic identity:

```python
from neven.identity import NevenIdentity

# Create identity
identity = NevenIdentity.create(
    agent_name="hub-sp-iguatemi-01",
    location="Shopping Iguatemi, São Paulo",
    capabilities=["camera", "screen", "voice"]
)
print(identity.did)  # did:neven:hub-sp-iguatemi-01-a3f9b2c1

# Sign a request
signed = identity.sign_request({"action": "unlock_door"})

# Save/load
identity.save("./my-identity.json")
loaded = NevenIdentity.load("./my-identity.json")
```

---

## CLI

```bash
neven mock-server           # Start local development server
neven demo                  # Run interactive demonstration
neven status               # Check connectivity
neven identity create --name hub-sp-01 --location "São Paulo"
neven identity show ./hub-sp-01-identity.json
```

---

## Deterministic Safety Engine (DSE)

**NEVEN is safe by design.** The DSE runs locally on edge hardware and validates every actuation request against hard-coded safety rules BEFORE any electrical signal reaches the actuator.

This means:
- An AI hallucination cannot unlock a door with a person standing in front of it
- Safety rules are deterministic — not probabilistic
- If the internet is cut, the DSE continues enforcing rules locally
- Every physical action is cryptographically signed and auditable

```python
# If DSE blocks, you get a typed exception — not a crash
try:
    client.unlock("node_hub", compartment_id="C-4")
except NevenSafetyError as e:
    print(f"Rule: {e.rule_id}")  # rule_human_presence_required
    print(f"Why: {e.message}")   # SAFETY_RULE_VIOLATION: No person within 1.5m
```

---

## Architecture

```
Your AI Agent
     ↓  neven.connect()
NEVEN Runtime
     ↓  neven.perceive()
Physical World State Graph (PWSG)
     ↓  neven.act() → DSE validation
Physical Hardware (cameras, screens, sensors, actuators)
```

**4 Layers:**
- **L1 Agent-to-Reality Interface** — REST/gRPC/MCP
- **L2 Physical World State Graph** — Semantic spatial database
- **L3 Deterministic Safety Engine** — Zero-trust hardware gatekeeper
- **L4 Hardware Abstraction** — RTSP/ONVIF/MQTT/Modbus

---

## Use Cases

| Sector | Infrastructure | With NEVEN |
|--------|---------------|------------|
| Shopping | Dumb information kiosk | Intelligent guide agent |
| Airport | Security cameras | Autonomous check-in agent |
| Hospital | Reception tablet | Triage agent that learns |
| City | Traffic cameras | Real-time urban management |
| Retail | Traditional POS | Behavioral analytics agent |
| Logistics | Standard lockers | Autonomous delivery agent |

---

## Get API Key

1. Visit [neventech.com](https://neventech.com)
2. Create your account
3. Generate API key (starts with `nv_live_`)

For development: use `nv_test_xxx` with `mock=True` (no key needed)

---

## Resources

- **Docs:** https://docs.neventech.com
- **GitHub:** https://github.com/neventech/neven-sdk
- **Discord:** https://discord.gg/neventech
- **X/Twitter:** @neventech

---

*NEVEN — Physical Intelligence as a Service*
*Built for the age of autonomous agents.*
