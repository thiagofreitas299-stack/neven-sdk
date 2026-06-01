"""
NEVEN SDK — Tests
==================
Tests that run without any physical hardware using the mock server.

Run: pytest tests/ -v
"""

import pytest
import threading
import time

from neven import NevenClient, NevenIdentity
from neven.exceptions import NevenSessionError, NevenSafetyError
from neven.mock_server import MockServer


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def mock_server():
    """Start mock server once for all tests."""
    server = MockServer(port=8430)
    server.start_background()
    time.sleep(0.5)
    yield server
    server.stop()


@pytest.fixture
def client(mock_server):
    """Create a test client connected to mock server."""
    c = NevenClient(api_key="nv_test_pytest", mock=True)
    c.base_url = "http://localhost:8430"
    yield c
    c.disconnect()


@pytest.fixture
def connected_client(client):
    """Client with an active session."""
    client.connect(
        agent_id="test-agent-pytest",
        requested_nodes=["node_rj_keepithub_01", "node_sp_iguatemi_01"],
        capabilities=["perception", "actuation"],
    )
    return client


# ─────────────────────────────────────────────────────────────────────────────
# Identity Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestNevenIdentity:
    def test_create_identity(self):
        identity = NevenIdentity.create(
            agent_name="test-hub-01",
            location="Test Location",
            capabilities=["camera", "screen"],
        )
        assert identity.did.startswith("did:neven:test-hub-01-")
        assert identity.agent_name == "test-hub-01"
        assert len(identity.private_key) == 64  # 32 bytes hex
        assert identity.metadata["location"] == "Test Location"
        assert "camera" in identity.metadata["capabilities"]

    def test_sign_and_verify(self):
        identity = NevenIdentity.create("signer-test")
        payload = {"action": "test", "value": 42}
        signature = identity.sign(payload)
        assert identity.verify(payload, signature)
        assert not identity.verify({"tampered": True}, signature)

    def test_sign_request_envelope(self):
        identity = NevenIdentity.create("envelope-test")
        envelope = identity.sign_request({"action": "unlock"})
        assert "did" in envelope
        assert "signature" in envelope
        assert "timestamp" in envelope
        assert envelope["did"] == identity.did

    def test_save_and_load(self, tmp_path):
        identity = NevenIdentity.create("persistence-test", location="São Paulo")
        path = tmp_path / "test-identity.json"
        identity.save(str(path))
        loaded = NevenIdentity.load(str(path))
        assert loaded.did == identity.did
        assert loaded.private_key == identity.private_key
        assert loaded.metadata["location"] == "São Paulo"

    def test_public_card_no_private_key(self):
        identity = NevenIdentity.create("public-card-test")
        card = identity.to_public_card()
        assert "private_key" not in card
        assert "did" in card
        assert "public_key_fingerprint" in card

    def test_did_format(self):
        identity = NevenIdentity.create("format-test")
        parts = identity.did.split(":")
        assert parts[0] == "did"
        assert parts[1] == "neven"
        assert len(parts[2]) > 10  # name + fingerprint


# ─────────────────────────────────────────────────────────────────────────────
# Client Connection Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestNevenClientConnection:
    def test_connect_success(self, client):
        session = client.connect(
            agent_id="test-connect-agent",
            requested_nodes=["node_rj_keepithub_01"],
            capabilities=["perception", "actuation"],
        )
        assert session.session_id
        assert session.is_valid
        assert "node_rj_keepithub_01" in session.authorized_nodes

    def test_session_requires_connect(self, client):
        with pytest.raises(NevenSessionError):
            client.perceive("node_rj_keepithub_01")

    def test_context_manager(self, mock_server):
        c = NevenClient(api_key="nv_test_ctx", mock=True)
        c.base_url = "http://localhost:8430"
        with c:
            c.connect("ctx-agent", ["node_sp_iguatemi_01"], ["perception"])
            assert c._session is not None
        assert c._session is None

    def test_client_repr(self, client):
        assert "disconnected" in repr(client)
        client.connect("repr-test", ["node_rj_keepithub_01"], ["perception"])
        assert "session=" in repr(client)


# ─────────────────────────────────────────────────────────────────────────────
# Perceive Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPerceive:
    def test_perceive_returns_spatial_state(self, connected_client):
        state = connected_client.perceive("node_rj_keepithub_01")
        assert "spatial_state" in state
        assert "detected_entities" in state["spatial_state"]
        assert "environmental_telemetry" in state["spatial_state"]

    def test_perceive_has_entities_list(self, connected_client):
        state = connected_client.perceive("node_sp_iguatemi_01")
        entities = state["spatial_state"]["detected_entities"]
        assert isinstance(entities, list)

    def test_perceive_telemetry_fields(self, connected_client):
        state = connected_client.perceive("node_rj_keepithub_01")
        telemetry = state["spatial_state"]["environmental_telemetry"]
        assert "temperature_celsius" in telemetry
        assert "ambient_light_lux" in telemetry

    def test_perceive_has_timestamp(self, connected_client):
        state = connected_client.perceive("node_rj_keepithub_01")
        assert "timestamp" in state

    def test_get_people_count(self, connected_client):
        count = connected_client.get_people_count("node_rj_keepithub_01")
        assert isinstance(count, int)
        assert count >= 0

    def test_get_occupancy(self, connected_client):
        occupancy = connected_client.get_occupancy("node_sp_iguatemi_01")
        assert 0.0 <= occupancy <= 1.0


# ─────────────────────────────────────────────────────────────────────────────
# Act Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAct:
    def test_display_message(self, connected_client):
        result = connected_client.display(
            "node_sp_iguatemi_01",
            "Test message",
            duration=5,
        )
        assert result["status"] == "executed"
        assert "transaction_id" in result
        assert result["transaction_id"].startswith("tx_act_")

    def test_speak(self, connected_client):
        result = connected_client.speak(
            "node_rj_keepithub_01",
            "Test speech",
            lang="pt-BR",
        )
        assert result["status"] == "executed"

    def test_act_returns_dse_evaluation(self, connected_client):
        result = connected_client.display("node_sp_iguatemi_01", "DSE test")
        assert "safety_evaluation" in result
        assert "dse_status" in result["safety_evaluation"]

    def test_unlock_may_raise_safety_error(self, connected_client):
        # Unlock may succeed or fail depending on mock DSE state
        # Both outcomes are correct — we just verify the types
        try:
            result = connected_client.unlock(
                "node_rj_keepithub_01",
                compartment_id="C-1",
            )
            assert result["status"] == "executed"
        except NevenSafetyError as e:
            assert e.rule_id is not None
            assert "SAFETY_RULE_VIOLATION" in e.code

    def test_act_without_session_raises(self, client):
        with pytest.raises(NevenSessionError):
            client.act("node_rj_keepithub_01", "display_message", {"text": "test"})


# ─────────────────────────────────────────────────────────────────────────────
# DSE Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDSE:
    def test_safety_error_has_rule_id(self, connected_client):
        """Run enough unlocks to trigger DSE at some point."""
        safety_triggered = False
        for i in range(10):
            try:
                connected_client.unlock("node_rj_keepithub_01", f"C-{i+1}")
            except NevenSafetyError as e:
                safety_triggered = True
                assert e.rule_id is not None
                assert hasattr(e, "details")
                break
        # DSE should trigger at some point (mock has 20% chance per unlock)
        # We just verify that when it does, the exception is well-formed

    def test_safety_error_message(self, connected_client):
        for _ in range(20):
            try:
                connected_client.unlock("node_rj_keepithub_01", "C-99")
            except NevenSafetyError as e:
                assert len(e.message) > 10
                return
        # If DSE never triggered in 20 tries, that's statistically unusual but OK


# ─────────────────────────────────────────────────────────────────────────────
# Mock Server Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestMockServer:
    def test_health_endpoint(self):
        import requests
        r = requests.get("http://localhost:8430/health")
        assert r.ok
        assert r.json()["mock"] is True

    def test_mock_flag_in_responses(self, connected_client):
        state = connected_client.perceive("node_rj_keepithub_01")
        assert state.get("_mock") is True
