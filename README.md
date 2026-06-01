# NEVEN TECH

[![Version](https://img.shields.io/badge/version-2.1.0-blue.svg)](https://neventech.com)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org)
[![Docker](https://img.shields.io/badge/docker-supported-blue.svg)](https://www.docker.com)
[![MCP](https://img.shields.io/badge/MCP-compatible-purple.svg)](https://modelcontextprotocol.io)

**NEVEN TECH** is "the Stripe of the Physical World." It is a functional, highly-extensible AI platform designed to connect AI agents to any physical infrastructure—cameras, sensors, and IoT actuators—without owning or managing the underlying hardware.

---

## Webcam to Claude — 3 Lines

```python
from neven import NevenClient
client = NevenClient(api_key="nv_live_dev")
state = client.perceive("local_webcam")
print(f"Claude sees: {state.semantic_description}")
```

That's it. Your AI agent can now see and understand the physical world.

---

## Key Features

- **Standardized Core SDK**: Simple Python interface (`connect()`, `perceive()`, `act()`, `subscribe()`) to interact with any physical space.
- **Physical World State Graph**: Real-time hierarchical representation of physical spaces (Cities → Districts → Hubs → Cameras) with automatic state propagation.
- **Deterministic Safety Engine (DSE)**: Dual-pass verification system with circuit breaker that evaluates safety assertions before executing any physical action.
- **KAIS Identity System** (v2.1): Cryptographic Agent Identity with DID generation, HMAC-SHA256 signing, and immutable audit trails.
- **MCP Server** (v2.1): Native Model Context Protocol integration for Claude Desktop and MCP-compatible AI agents.
- **Pricing Tiers** (v2.1): Built-in rate limiting with Starter, Business, and Enterprise tiers.
- **Real-Time Spatial Analytics**: Built-in algorithms for foot traffic counting, spatial heatmaps, and dwell-time tracking.
- **Hardware Abstraction Layer (HAL)**: Protocol bridges for RTSP/ONVIF, MQTT, HTTP, and local Webcams.
- **FastAPI REST Server & Web Dashboard**: Fully featured REST API with a built-in real-time analytics dashboard.
- **LGPD/GDPR Compliance**: Built-in data anonymization helpers for privacy-sensitive deployments.

---

## System Architecture

```mermaid
graph TD
    subgraph AI Agents & Clients
        Agent[AI Agent / SDK]
        Claude[Claude Desktop via MCP]
        CLI[NEVEN CLI]
        Dash[Web Dashboard]
    end

    subgraph NEVEN Core Runtime (FastAPI Server)
        API[REST API & WebSockets]
        MCP[MCP Server - stdio]
        DSE[Dual-Pass Safety Engine]
        KAIS[KAIS Identity System]
        Graph[Physical World State Graph]
        Analytics[Spatial Analytics Engine]
        HAL[Hardware Abstraction Layer]
    end

    subgraph Physical Infrastructure
        Webcam[Local Webcam]
        RTSP[RTSP / ONVIF Cameras]
        MQTT[MQTT IoT Sensors]
        Modbus[Modbus Actuators]
    end

    %% Client Interactions
    Agent -->|gRPC / REST| API
    Claude -->|MCP stdio| MCP
    CLI -->|REST| API
    Dash -->|WebSockets / REST| API

    %% Core Flow
    API --> DSE
    API --> KAIS
    API --> Graph
    API --> Analytics
    API --> HAL
    MCP --> API

    %% Safety & Graph
    DSE -->|Verify Permissions & Rules| Graph
    Analytics -->|Update Spatial State| Graph
    KAIS -->|Sign & Audit| DSE

    %% HAL to Devices
    HAL --> Webcam
    HAL --> RTSP
    HAL --> MQTT
    HAL --> Modbus
```

---

## Directory Structure

```text
neven-tech/
├── Dockerfile                  # Multi-stage production Docker image
├── docker-compose.yml          # One-command multi-service deployment
├── pyproject.toml              # Modern PEP 517 package configuration
├── setup.py                    # Legacy installation support
├── requirements.txt            # Package dependencies
├── README.md                   # Quickstart and documentation
├── .env.example                # Template environment variables
│
├── neven/                      # Main package directory
│   ├── __init__.py             # Top-level SDK client export (v2.1.0)
│   ├── core/                   # Core modules
│   │   ├── client.py           # Python SDK Client (KAIS-integrated)
│   │   ├── config.py           # Configuration management
│   │   ├── identity.py         # KAIS Identity System (v2.1)
│   │   ├── models.py           # Pydantic schemas and types
│   │   └── tiers.py            # Pricing tiers & rate limiting (v2.1)
│   ├── safety/                 # Safety & permission engines
│   │   └── engine.py           # DSE Dual-Pass Safety Engine (v2.1)
│   ├── mcp/                    # Model Context Protocol (v2.1)
│   │   └── server.py           # MCP Server for Claude Desktop
│   ├── graph/                  # Spatial state graph
│   │   └── state_graph.py      # Physical World State Graph
│   ├── perception/             # Computer vision & tracking
│   │   ├── detector.py         # Built-in and YOLO detectors
│   │   ├── tracker.py          # Multi-object tracking (SORT-based)
│   │   └── pipeline.py         # Real-time frame processing pipeline
│   ├── hal/                    # Hardware Abstraction Layer
│   │   └── bridge.py           # Protocol drivers (RTSP, MQTT, etc.)
│   ├── analytics/              # Spatial analytics algorithms
│   │   └── engine.py           # Foot traffic, heatmaps, dwell times
│   ├── api/                    # REST API Server
│   │   └── server.py           # FastAPI application & dashboard
│   ├── cli/                    # Command-line interface
│   │   └── main.py             # CLI command parser (v2.1 commands)
│   └── utils/                  # Shared utilities
│       └── logging.py          # Custom colored logging and banners
│
├── examples/                   # Example scripts (v2.1)
│   └── webcam_to_claude.py     # The famous 3-line example
│
├── demo/                       # Demo and example scripts
│   ├── run_demo.py             # Executable demo script
│   └── sdk_example.py          # Complete Python SDK usage example
│
├── config/                     # Configuration files
│   ├── default.json            # Default system parameters
│   └── safety_rules.json       # Pre-configured safety rules
│
├── scripts/                    # Automation scripts
│   └── start.sh                # Executable entrypoint script
│
└── tests/                      # Full test suite
    ├── test_core.py            # Unit tests for core engines
    ├── test_api.py             # Integration tests for API endpoints
    ├── test_identity.py        # KAIS identity tests (v2.1)
    └── test_mcp.py             # MCP server tests (v2.1)
```

---

## Installation

### Method 1: Local Development Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/neventech/neven.git
   cd neven
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install the package in editable mode**:
   ```bash
   pip install -e .
   ```

   *To install optional vision dependencies (OpenCV & YOLOv8)*:
   ```bash
   pip install -e ".[vision]"
   ```

### Method 2: Production Deployment with Docker

Start the entire stack (API server, Redis cache, and persistent storage) with a single command:

```bash
docker-compose up --build -d
```

To include the MCP server:
```bash
docker-compose --profile mcp up --build -d
```

---

## Quickstart Guide

### 1. Webcam to Claude (3 Lines)

```python
from neven import NevenClient
client = NevenClient(api_key="nv_live_dev")
state = client.perceive("local_webcam")
print(f"Claude sees: {state.semantic_description}")
```

### 2. Run the Demo out of the box

NEVEN includes an interactive demo mode that starts the API server and simulates real-time perception analytics using a synthetic video source (no camera required).

```bash
./scripts/start.sh demo
```

Or run the demo script directly:
```bash
python demo/run_demo.py
```

Open your browser and navigate to **[http://localhost:8420](http://localhost:8420)** to view the live analytics dashboard.

### 3. Run the API Server

Start the production-ready FastAPI server:
```bash
neven serve
```

Access the interactive API documentation at **[http://localhost:8420/docs](http://localhost:8420/docs)**.

### 4. Initialize a New Project

Create a pre-configured NEVEN project structure:
```bash
neven init my_smart_city
cd my_smart_city
neven serve
```

---

## MCP Server (Claude Desktop Integration)

NEVEN v2.1 includes a native **Model Context Protocol (MCP)** server that exposes NEVEN as a tool for Claude Desktop and other MCP-compatible AI agents.

### Setup for Claude Desktop

1. Start the NEVEN server:
   ```bash
   neven serve
   ```

2. Get the Claude Desktop configuration:
   ```bash
   neven mcp-server --config
   ```

3. Add the output to your `claude_desktop_config.json`:
   ```json
   {
     "mcpServers": {
       "neven": {
         "command": "neven",
         "args": ["mcp-server"],
         "env": {
           "NEVEN_API_KEY": "nv_live_dev",
           "NEVEN_BASE_URL": "http://localhost:8420"
         }
       }
     }
   }
   ```

4. Restart Claude Desktop. You can now ask Claude to perceive physical spaces, execute actions, and subscribe to events.

### MCP Tools Exposed

| Tool | Description |
| :--- | :--- |
| `neven_connect` | Establish a session with physical infrastructure |
| `neven_perceive` | Query real-time spatial state of a node |
| `neven_act` | Execute a safe physical action (DSE-verified) |
| `neven_subscribe` | Subscribe to real-time spatial events |

---

## KAIS Identity System

NEVEN v2.1 introduces the **Cryptographic Agent Identity System (KAIS)** for secure, auditable interactions with physical infrastructure.

### Features

- **DID Generation**: Every agent gets a unique Decentralized Identifier: `did:neven:{node_type}-{location}-{unique_id}`
- **HMAC-SHA256 Signing**: Every action is cryptographically signed for non-repudiation
- **Immutable Audit Trail**: All actions are logged in a tamper-evident local JSON log
- **LGPD/GDPR Compliance**: Built-in data anonymization helpers

### Usage

```python
from neven import NevenClient

client = NevenClient(api_key="nv_live_dev")
print(f"Agent DID: {client.identity.did}")
# did:neven:agent-default-a1b2c3d4

# Sign an action
signature = client.identity.sign_action("unlock", "node_01", {"door": "main"})

# Verify a signature
is_valid = client.identity.verify_signature(signature, "unlock", "node_01", {"door": "main"})

# Get audit trail
trail = client.identity.get_audit_trail()

# Anonymize state for LGPD/GDPR
anonymized = client.identity.anonymize_state(state_dict)
```

### CLI Commands

```bash
neven identity                    # Show current DID
neven identity --generate         # Generate a new identity
neven identity --audit            # View audit trail
```

---

## Pricing Tiers

NEVEN v2.1 includes built-in rate limiting and pricing tiers:

| Tier | Price | Requests/Month | Nodes | Support |
| :--- | :--- | :--- | :--- | :--- |
| **Starter** | Free | 1,000 | 5 | Community |
| **Business** | $99/mo | 50,000 | 100 | Priority |
| **Enterprise** | Custom | Unlimited | Unlimited | Dedicated |

### Check Your Tier

```bash
neven tier
```

### API Usage Endpoint

```
GET /api/v1/usage
GET /api/v1/tiers
```

---

## Python SDK Reference

The SDK enables AI agents to interact with physical environments securely.

```python
import neven

# 1. Initialize the client
client = neven.Client(
    api_key="nv_dev_demo_key",
    agent_private_key="demo_agent_secret_key",
    base_url="http://localhost:8420"
)

# 2. Connect and establish a session
session = client.connect(
    agent_id="demo_agent",
    nodes=["node_demo_camera", "node_demo_hub"],
    capabilities=["perception", "actuation"]
)
print(f"Connected! Session: {session.session_id}")
print(f"Agent DID: {client.identity.did}")

# 3. Perceive the spatial state in real-time
state = client.perceive(node_id="node_demo_camera")
print(f"Semantic: {state.semantic_description}")
print(f"Current occupancy: {state.spatial_state.occupancy_status}")
for entity in state.spatial_state.detected_entities:
    print(f"Detected {entity.class_label.value} with confidence {entity.confidence:.2f}")

# 4. Execute a safe physical action (DSE-verified, KAIS-signed)
result = client.act(
    node_id="node_demo_hub",
    action_type="unlock_compartment",
    parameters={"compartment_id": "C-4"}
)
print(f"Action Status: {result.status} | DSE Status: {result.safety_evaluation.dse_status.value}")

# 5. Subscribe to real-time events via WebSockets
def handle_event(event):
    print(f"Event: {event.event_type.value} on node {event.node_id}")

client.subscribe(
    node_id="node_demo_camera",
    events=["entity_entered"],
    callback=handle_event
)
```

---

## API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/health` | `GET` | System health check and component status |
| `/metrics` | `GET` | System metrics including DSE and usage stats |
| `/v1/session/connect` | `POST` | Establish a physical session for an AI agent |
| `/v1/perception/query` | `POST` | Query real-time spatial state of a node |
| `/v1/actuation/execute` | `POST` | Execute a physical action (DSE-verified) |
| `/v1/perception/events` | `POST` | Poll for recent spatial events |
| `/v1/stream` | `WS` | WebSocket stream for real-time state updates |
| `/v1/analytics/summary/{node_id}` | `GET` | Get complete spatial analytics summary |
| `/v1/analytics/heatmap/{node_id}` | `GET` | Get current normalized heatmap cells |
| `/v1/graph/topology` | `GET` | Get the full state graph topology |
| `/api/v1/identity` | `GET` | Get KAIS identity information |
| `/api/v1/identity/verify` | `POST` | Verify an agent's identity |
| `/api/v1/identity/audit` | `GET` | Get KAIS audit trail |
| `/api/v1/mcp` | `GET` | MCP server configuration info |
| `/api/v1/tiers` | `GET` | Available pricing tiers |
| `/api/v1/usage` | `GET` | Current API key usage statistics |

---

## Deterministic Safety Engine (DSE)

NEVEN implements a **dual-pass verification engine** with circuit breaker to prevent unauthorized or unsafe physical actions:

1. **Pass 1: Cryptographic Authorization**: Verifies the agent's signature against the permission ledger to ensure it has explicit access to the target node and action.
2. **Pass 2: State Assertion Verification**: Evaluates logical assertions against the real-time edge state. If any assertion fails, the action is immediately blocked.

**Circuit Breaker** (v2.1): If a node experiences repeated safety violations, the circuit breaker trips and blocks all actions to that node until manually reset.

Example safety rule defined in `config/safety_rules.json`:
```json
{
  "rule_id": "rule_human_presence_required",
  "description": "Do not open any locker compartment unless a person is detected nearby",
  "trigger_action": "unlock_compartment",
  "assertion": "occupancy > 0",
  "fail_action": "BLOCK_AND_LOG"
}
```

---

## Running Tests

Execute the full test suite to verify the SDK, safety engine, state graph, identity system, MCP server, and REST API:

```bash
pytest
```

For verbose output:
```bash
pytest -v
```

---

## Contributing

We welcome contributions to the NEVEN TECH platform! Please see our [Contributing Guide](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Contact

- **Brand**: NEVEN TECH
- **Website**: [neventech.com](https://neventech.com)
- **Tagline**: *AI · SMART CITY SOLUTIONS*
- **Inquiries**: [engineering@neventech.com](mailto:engineering@neventech.com)
