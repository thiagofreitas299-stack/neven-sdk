"""
Tests for KAIS (Cryptographic Agent Identity System) — neven/core/identity.py

Tests cover:
    - DID generation format
    - Action signing and verification
    - Audit trail recording
    - State anonymization (LGPD/GDPR)
    - DID resolution and lookup
    - Identity verification
"""

import json
import os
import tempfile
import pytest

from neven.core.identity import KAISIdentity


class TestKAISIdentityGeneration:
    """Test DID generation and format."""

    def test_did_format(self):
        """DID should follow format: did:neven:{node_type}-{location}-{unique_id}"""
        identity = KAISIdentity(
            node_type="agent",
            location="saopaulo",
            secret_key="test_key_123",
        )
        assert identity.did.startswith("did:neven:agent-saopaulo-")
        parts = identity.did.split(":")
        assert parts[0] == "did"
        assert parts[1] == "neven"
        assert parts[2].startswith("agent-saopaulo-")

    def test_did_uniqueness(self):
        """Each identity should generate a unique DID."""
        id1 = KAISIdentity(node_type="agent", location="sp", secret_key="key1")
        id2 = KAISIdentity(node_type="agent", location="sp", secret_key="key2")
        assert id1.did != id2.did

    def test_did_components(self):
        """DID should contain correct node_type and location."""
        identity = KAISIdentity(
            node_type="camera",
            location="rio",
            secret_key="cam_key",
        )
        assert "camera" in identity.did
        assert "rio" in identity.did

    def test_identity_properties(self):
        """Identity should expose node_type, location, and created timestamp."""
        identity = KAISIdentity(
            node_type="hub",
            location="brasilia",
            secret_key="hub_key",
        )
        assert identity.node_type == "hub"
        assert identity.location == "brasilia"
        assert identity.created is not None


class TestKAISSigningVerification:
    """Test HMAC-SHA256 signing and verification."""

    def test_sign_action_returns_signature(self):
        """sign_action should return a hex signature string."""
        identity = KAISIdentity(
            node_type="agent",
            location="local",
            secret_key="signing_key",
        )
        signature = identity.sign_action(
            action="unlock_compartment",
            target_node="node_01",
            parameters={"compartment_id": "A1"},
        )
        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA-256 hex digest

    def test_verify_valid_signature(self):
        """verify_signature should return True for valid signatures."""
        identity = KAISIdentity(
            node_type="agent",
            location="local",
            secret_key="verify_key",
        )
        signature = identity.sign_action(
            action="lock_door",
            target_node="node_02",
            parameters={"door_id": "main"},
        )
        is_valid = identity.verify_signature(
            signature=signature,
            action="lock_door",
            target_node="node_02",
            parameters={"door_id": "main"},
        )
        assert is_valid is True

    def test_verify_invalid_signature(self):
        """verify_signature should return False for tampered signatures."""
        identity = KAISIdentity(
            node_type="agent",
            location="local",
            secret_key="verify_key",
        )
        is_valid = identity.verify_signature(
            signature="0000000000000000000000000000000000000000000000000000000000000000",
            action="lock_door",
            target_node="node_02",
            parameters={"door_id": "main"},
        )
        assert is_valid is False

    def test_different_keys_produce_different_signatures(self):
        """Different secret keys should produce different signatures."""
        id1 = KAISIdentity(node_type="agent", location="local", secret_key="key_a")
        id2 = KAISIdentity(node_type="agent", location="local", secret_key="key_b")

        sig1 = id1.sign_action("test", "node", {})
        sig2 = id2.sign_action("test", "node", {})
        assert sig1 != sig2


class TestKAISAuditTrail:
    """Test immutable audit trail."""

    def test_audit_trail_records_actions(self):
        """Each signed action should be recorded in the audit trail."""
        identity = KAISIdentity(
            node_type="agent",
            location="local",
            secret_key="audit_key",
        )
        identity.sign_action("action_1", "node_a", {"param": "value1"})
        identity.sign_action("action_2", "node_b", {"param": "value2"})

        trail = identity.get_audit_trail()
        assert len(trail) >= 2

    def test_audit_trail_contains_required_fields(self):
        """Audit entries should contain timestamp, action, target_node, signature."""
        identity = KAISIdentity(
            node_type="agent",
            location="local",
            secret_key="audit_key",
        )
        identity.sign_action("unlock", "node_01", {"key": "val"})

        trail = identity.get_audit_trail()
        entry = trail[-1]
        assert "timestamp" in entry
        assert "action" in entry
        assert "target_node" in entry
        assert "signature" in entry
        assert entry["action"] == "unlock"
        assert entry["target_node"] == "node_01"

    def test_audit_trail_immutability(self):
        """Audit trail entries should not be modifiable after creation."""
        identity = KAISIdentity(
            node_type="agent",
            location="local",
            secret_key="immutable_key",
        )
        identity.sign_action("test", "node", {})
        trail = identity.get_audit_trail()
        original_len = len(trail)

        # Modifying the returned list should not affect internal state
        trail.clear()
        assert len(identity.get_audit_trail()) == original_len


class TestKAISAnonymization:
    """Test LGPD/GDPR compliance helpers."""

    def test_anonymize_state_removes_pii(self):
        """anonymize_state should remove or mask personal identifiable information."""
        identity = KAISIdentity(
            node_type="camera",
            location="mall",
            secret_key="anon_key",
        )
        state = {
            "entities": [
                {"class": "person", "face_encoding": [0.1, 0.2, 0.3], "track_id": "t1"},
                {"class": "vehicle", "plate": "ABC-1234", "track_id": "t2"},
            ],
            "node_id": "cam_01",
            "occupancy": 5,
        }
        anonymized = identity.anonymize_state(state)

        # PII fields should be masked or removed
        for entity in anonymized.get("entities", []):
            assert "face_encoding" not in entity or entity["face_encoding"] is None
            assert "plate" not in entity or entity["plate"] == "[REDACTED]"

    def test_anonymize_preserves_non_pii(self):
        """anonymize_state should preserve non-PII data."""
        identity = KAISIdentity(
            node_type="camera",
            location="mall",
            secret_key="anon_key",
        )
        state = {
            "occupancy": 3,
            "node_id": "cam_01",
            "temperature": 24.5,
        }
        anonymized = identity.anonymize_state(state)
        assert anonymized["occupancy"] == 3
        assert anonymized["temperature"] == 24.5


class TestKAISDIDResolution:
    """Test DID resolution and lookup."""

    def test_did_document_structure(self):
        """DID document should have standard W3C-compatible structure."""
        identity = KAISIdentity(
            node_type="agent",
            location="cloud",
            secret_key="doc_key",
        )
        doc = identity.did_document.to_dict()
        assert "@context" in doc or "id" in doc
        assert doc["id"] == identity.did

    def test_verify_identity_self(self):
        """Identity should be able to verify itself."""
        identity = KAISIdentity(
            node_type="agent",
            location="local",
            secret_key="self_key",
        )
        result = identity.verify_identity(identity.did)
        assert result["verified"] is True

    def test_verify_identity_unknown(self):
        """Unknown DIDs should fail verification."""
        identity = KAISIdentity(
            node_type="agent",
            location="local",
            secret_key="self_key",
        )
        result = identity.verify_identity("did:neven:unknown-nowhere-000000")
        assert result["verified"] is False
