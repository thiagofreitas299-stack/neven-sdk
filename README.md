<div align="center">

# 🌌 NEVEN SDK

### Physical Intelligence as a Service

**Connect any AI agent to the physical world.**
Cameras, screens, sensors, locks, speakers — one unified API.

[![PyPI version](https://badge.fury.io/py/neven-sdk.svg)](https://pypi.org/project/neven-sdk/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Discord](https://img.shields.io/badge/Discord-Join%20Us-7289da)](https://discord.gg/neventech)

[Documentation](https://docs.neventech.com) · [Examples](examples/) · [Discord](https://discord.gg/neventech) · [neventech.com](https://neventech.com)

---

*"Stripe didn't build a bank. Twilio didn't build a tower.
NEVEN doesn't build hardware — NEVEN makes any hardware think."*

</div>

---

## What is NEVEN?

NEVEN is the **operating system for autonomous AI agents in the physical world**.

Most AI agents are intelligent but blind — they live in the cloud, disconnected from the real world. At the same time, cities are full of cameras, screens, sensors, and smart devices that are "dumb" — they record and report, but don't think.

NEVEN is the **missing layer** that connects them.

Install NEVEN on any physical hardware → connect any AI agent → your agent can now **see, understand, and act** in the real world.

```
Your AI Agent  ──→  NEVEN Runtime  ──→  Physical World
(GPT, Claude,       (perceive/act)       (cameras, screens,
 Gemini, custom)                          sensors, lockers)
```

## Installation

```bash
pip install neven-sdk
```

## Quickstart (5 minutes, no hardware required)

```bash
# Start the local development server
neven mock-server

# In another terminal, run the interactive demo
neven demo
```

Or in Python:

```python
from neven import NevenClient

# Development (mock server) — no hardware needed
client = NevenClient(api_key="nv_test_xxx", mock=True)

# Connect to physical nodes
session = client.connect(
    agent_id="my-agent-01",
    requested_nodes=["node_sp_iguatemi_01"],
    capabilities=["perception", "actuation"]
)

# See what's happening in the physical space
state = client.perceive(node_id="node_sp_iguatemi_01")
people = [e for e in state["spatial_state"]["detected_entities"]
          if e["class"] == "person"]
print(f"People in space: {len(people)}")

# Act on the physical world
client.display("node_sp_iguatemi_01", f"Welcome! {len(people)} people here.")
client.speak("node_sp_iguatemi_01", "Bem-vindo ao futuro.", lang="pt-BR")

# Unlock a smart locker (subject to safety validation)
from neven.exceptions import NevenSafetyError
try:
    client.unlock("node_rj_keepithub_01", compartment_id="C-4")
    print("Locker opened!")
except NevenSafetyError as e:
    print(f"Safety engine blocked: {e.message}")
    # This is correct! Physical safety is non-negotiable.
```

## Core API

NEVEN has **3 core methods**. That's it.

| Method | What it does |
|--------|-------------|
| `client.connect()` | Establish secure session with physical nodes |
| `client.perceive()` | Query real-time semantic state of physical space |
| `client.act()` | Execute safe physical actions (DSE-validated) |

Plus convenience shortcuts:

```python
client.display(node, text, duration)   # Show on screen
client.speak(node, text, lang)         # Text-to-speech
client.unlock(node, compartment_id)    # Open smart locker
client.get_people_count(node)          # Count people
client.detect_anomalies(node)          # Get anomaly list
```

## KAIS Identity

Every agent and node gets a cryptographic identity:

```python
from neven.identity import NevenIdentity

identity = NevenIdentity.create(
    agent_name="hub-sp-01",
    location="São Paulo, Brazil",
    capabilities=["camera", "screen", "payment"]
)
print(identity.did)  # did:neven:hub-sp-01-a3f9b2c1

# Save and load
identity.save("./hub-identity.json")
identity = NevenIdentity.load("./hub-identity.json")

# Sign requests
signed = identity.sign_request({"action": "unlock_door"})
```

## Deterministic Safety Engine (DSE)

The DSE is NEVEN's core safety layer. It runs **locally on edge hardware** and validates every actuation against hard-coded rules before any electrical signal reaches the actuator.

**Why it matters:**
- AI models hallucinate. A hallucinating agent could unlock a door with the wrong person
- The DSE is deterministic — not probabilistic
- Works offline (no internet required for safety)
- Every action is cryptographically signed and auditable

```python
# Safety violations surface as typed exceptions
try:
    client.unlock("node_hub", "C-4")
except NevenSafetyError as e:
    print(e.rule_id)   # rule_human_presence_required
    print(e.message)   # No verified human within 1.5 meters
```

## Use Cases

| Sector | With NEVEN |
|--------|------------|
| **Shopping Centers** | Intelligent guide agent on existing kiosks |
| **Airports** | Autonomous check-in via existing cameras |
| **Hospitals** | Smart triage on reception tablets |
| **Smart Cities** | Urban management on traffic cameras |
| **Logistics** | Autonomous delivery on standard lockers |
| **Retail** | Behavioral analytics + conversion agent |

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              NEVEN 4-Layer Architecture             │
├─────────────────────────────────────────────────────┤
│  L1: Agent-to-Reality Interface (REST/gRPC/MCP)    │
├─────────────────────────────────────────────────────┤
│  L2: Physical World State Graph (Spatial DB)        │
├─────────────────────────────────────────────────────┤
│  L3: Deterministic Safety Engine (Edge-local)       │
├─────────────────────────────────────────────────────┤
│  L4: Hardware Abstraction (RTSP/MQTT/Modbus)        │
└─────────────────────────────────────────────────────┘
              ↕ Any physical hardware
```

**Microservices (Go + Rust):**
- `neven-a2r-gateway` — API gateway for agent connections
- `neven-spatial-graph` — Physical World State Graph
- `neven-edge-runtime` — Edge processing + DSE
- `neven-hal-bridge` — Hardware protocol translation

**Databases:**
- PostgreSQL + PostGIS + pgvector (spatial state)
- Redis Cluster (real-time state cache, sub-ms)
- TimescaleDB (telemetry + audit logs)

## CLI

```bash
neven mock-server              # Start development server
neven demo                     # Interactive demonstration
neven status                   # Check connectivity

neven identity create \
  --name hub-sp-01 \
  --location "São Paulo" \
  --capabilities camera,screen,voice

neven identity show ./hub-sp-01-identity.json
```

## Examples

| File | Description |
|------|-------------|
| [quickstart.py](examples/quickstart.py) | Hello World in 10 lines |
| [shopping_guide.py](examples/shopping_guide.py) | Autonomous shopping guide |
| [delivery_coordinator.py](examples/delivery_coordinator.py) | Smart delivery coordination |
| [smart_city_monitor.py](examples/smart_city_monitor.py) | City-scale monitoring |

## Getting Started (Production)

1. **Get API key:** [neventech.com](https://neventech.com)
2. **Install:** `pip install neven-sdk`
3. **Register your first node:** `neven identity create --name my-node-01`
4. **Connect and build:** see [examples/](examples/)

## Contributing

NEVEN is open source (MIT). We welcome contributions!

```bash
git clone https://github.com/neventech/neven-sdk
cd neven-sdk
pip install -e ".[dev]"
pytest tests/
```

## Roadmap

- [x] Python SDK v1.0
- [x] Mock server for development
- [x] KAIS identity layer
- [x] DSE safety engine
- [ ] Node.js SDK
- [ ] Native MCP server (Claude/GPT tool integration)
- [ ] SenseTime camera SDK integration
- [ ] $KEEPIT token integration
- [ ] Kubernetes Helm chart
- [ ] Edge deployment for NVIDIA Jetson

## License

MIT — see [LICENSE](LICENSE)

---

<div align="center">

**NEVEN** · [neventech.com](https://neventech.com) · [Docs](https://docs.neventech.com) · [Discord](https://discord.gg/neventech) · [@neventech](https://x.com/neventech)

*Built for the age of autonomous agents.*

</div>
