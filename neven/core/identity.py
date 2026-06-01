"""
KAIS — Cryptographic Agent Identity System

Provides decentralized identity (DID) generation, HMAC-SHA256 action signing,
immutable audit trails, and LGPD/GDPR compliance helpers for the NEVEN platform.

DID Format: did:neven:{node_type}-{location}-{unique_id}

Every action executed through NEVEN is cryptographically signed and logged,
ensuring non-repudiation and full traceability across distributed physical nodes.
"""

import hashlib
import hmac
import json
import os
import time
import uuid
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("neven.identity")


# ─── Constants ────────────────────────────────────────────────────────────────

DID_METHOD = "neven"
DID_PREFIX = f"did:{DID_METHOD}:"
AUDIT_LOG_DIR = os.environ.get("NEVEN_AUDIT_LOG_DIR", ".neven/audit")
SIGNATURE_ALGORITHM = "HMAC-SHA256"


# ─── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class AuditEntry:
    """An immutable audit trail entry."""
    entry_id: str
    did: str
    action: str
    target_node: str
    timestamp: str
    signature: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: str = "pending"
    anonymized: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DIDDocument:
    """W3C-inspired DID Document for NEVEN agents."""
    id: str  # The DID itself
    node_type: str
    location: str
    created: str
    authentication: List[str] = field(default_factory=list)
    service: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─── KAIS Identity Class ─────────────────────────────────────────────────────

class KAISIdentity:
    """
    Cryptographic Agent Identity System (KAIS).

    Manages decentralized identity for NEVEN agents, providing:
    - DID generation following did:neven:{node_type}-{location}-{unique_id}
    - HMAC-SHA256 signing for every action
    - Immutable local JSON audit trail
    - Agent identity verification
    - DID resolution and lookup
    - LGPD/GDPR compliance helpers

    Example:
        identity = KAISIdentity(
            node_type="camera",
            location="sp-paulista",
            secret_key="my_agent_secret"
        )
        print(identity.did)  # did:neven:camera-sp-paulista-a1b2c3d4

        signature = identity.sign_action("unlock_door", "node_hub_01", {"door": "A"})
        assert identity.verify_signature(signature, "unlock_door", "node_hub_01", {"door": "A"})
    """

    def __init__(
        self,
        node_type: str = "agent",
        location: str = "default",
        secret_key: str = "",
        unique_id: Optional[str] = None,
        audit_log_dir: Optional[str] = None,
    ):
        self._node_type = node_type.lower().replace(" ", "-")
        self._location = location.lower().replace(" ", "-")
        self._unique_id = unique_id or uuid.uuid4().hex[:8]
        self._secret_key = (secret_key or os.environ.get("NEVEN_AGENT_SECRET", "default_secret")).encode("utf-8")
        self._created = datetime.now(timezone.utc).isoformat()
        self._audit_log_dir = Path(audit_log_dir or AUDIT_LOG_DIR)
        self._audit_trail: List[AuditEntry] = []
        self._did_registry: Dict[str, DIDDocument] = {}

        # Generate DID
        self._did = self.generate_did(self._node_type, self._location, self._unique_id)

        # Create DID Document
        self._did_document = DIDDocument(
            id=self._did,
            node_type=self._node_type,
            location=self._location,
            created=self._created,
            authentication=[SIGNATURE_ALGORITHM],
            service=[
                {"type": "NevenEndpoint", "serviceEndpoint": "http://localhost:8420"}
            ],
        )

        # Register self
        self._did_registry[self._did] = self._did_document

        # Ensure audit log directory exists
        self._audit_log_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"KAIS Identity initialized: {self._did}")

    # ─── Properties ───────────────────────────────────────────────────────

    @property
    def did(self) -> str:
        """Return the Decentralized Identifier."""
        return self._did

    @property
    def node_type(self) -> str:
        return self._node_type

    @property
    def location(self) -> str:
        return self._location

    @property
    def did_document(self) -> DIDDocument:
        return self._did_document

    @property
    def created(self) -> str:
        return self._created

    # ─── DID Generation ───────────────────────────────────────────────────

    @staticmethod
    def generate_did(node_type: str, location: str, unique_id: Optional[str] = None) -> str:
        """
        Generate a Decentralized Identifier (DID) for a NEVEN agent.

        Format: did:neven:{node_type}-{location}-{unique_id}

        Args:
            node_type: Type of node (agent, camera, hub, sensor)
            location: Physical location identifier
            unique_id: Optional unique suffix (auto-generated if not provided)

        Returns:
            A fully-qualified DID string
        """
        uid = unique_id or uuid.uuid4().hex[:8]
        node_type_clean = node_type.lower().replace(" ", "-")
        location_clean = location.lower().replace(" ", "-")
        return f"{DID_PREFIX}{node_type_clean}-{location_clean}-{uid}"

    # ─── Action Signing ───────────────────────────────────────────────────

    def sign_action(
        self,
        action: str,
        target_node: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Sign an action with HMAC-SHA256 for non-repudiation.

        Creates a cryptographic signature over the action payload and records
        the action in the immutable audit trail.

        Args:
            action: The action type (e.g., "unlock_compartment")
            target_node: The target node ID
            parameters: Action parameters

        Returns:
            Hex-encoded HMAC-SHA256 signature
        """
        parameters = parameters or {}
        timestamp = datetime.now(timezone.utc).isoformat()

        # Build canonical payload for signing
        payload = self._build_canonical_payload(action, target_node, parameters, timestamp)

        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self._secret_key,
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        # Record in audit trail
        entry = AuditEntry(
            entry_id=f"audit_{uuid.uuid4().hex[:12]}",
            did=self._did,
            action=action,
            target_node=target_node,
            timestamp=timestamp,
            signature=signature,
            parameters=parameters,
            result="signed",
        )
        self._audit_trail.append(entry)
        self._persist_audit_entry(entry)

        logger.debug(f"Action signed: {action} -> {target_node} [{signature[:16]}...]")
        return signature

    def verify_signature(
        self,
        signature: str,
        action: str,
        target_node: str,
        parameters: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None,
    ) -> bool:
        """
        Verify an HMAC-SHA256 signature for a given action.

        Args:
            signature: The signature to verify
            action: The action type
            target_node: The target node ID
            parameters: Action parameters
            timestamp: The timestamp used during signing (if None, checks recent entries)

        Returns:
            True if signature is valid, False otherwise
        """
        parameters = parameters or {}

        # If timestamp provided, verify directly
        if timestamp:
            payload = self._build_canonical_payload(action, target_node, parameters, timestamp)
            expected = hmac.new(
                self._secret_key,
                payload.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            return hmac.compare_digest(signature, expected)

        # Otherwise, check against recent audit entries
        for entry in reversed(self._audit_trail[-100:]):
            if entry.action == action and entry.target_node == target_node:
                payload = self._build_canonical_payload(
                    action, target_node, parameters, entry.timestamp
                )
                expected = hmac.new(
                    self._secret_key,
                    payload.encode("utf-8"),
                    hashlib.sha256,
                ).hexdigest()
                if hmac.compare_digest(signature, expected):
                    return True

        return False

    # ─── Audit Trail ──────────────────────────────────────────────────────

    def get_audit_trail(
        self,
        limit: int = 100,
        action_filter: Optional[str] = None,
        node_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the immutable audit trail.

        Args:
            limit: Maximum number of entries to return
            action_filter: Filter by action type
            node_filter: Filter by target node

        Returns:
            List of audit trail entries as dictionaries
        """
        entries = self._audit_trail

        if action_filter:
            entries = [e for e in entries if e.action == action_filter]
        if node_filter:
            entries = [e for e in entries if e.target_node == node_filter]

        return [e.to_dict() for e in entries[-limit:]]

    # ─── DID Resolution ───────────────────────────────────────────────────

    def resolve_did(self, did: str) -> Optional[Dict[str, Any]]:
        """
        Resolve a DID to its DID Document.

        Args:
            did: The DID to resolve

        Returns:
            DID Document as dictionary, or None if not found
        """
        doc = self._did_registry.get(did)
        if doc:
            return doc.to_dict()
        return None

    def register_did(self, did_document: DIDDocument) -> None:
        """
        Register a DID Document in the local registry.

        Args:
            did_document: The DID Document to register
        """
        self._did_registry[did_document.id] = did_document
        logger.info(f"DID registered: {did_document.id}")

    def list_registered_dids(self) -> List[str]:
        """List all registered DIDs."""
        return list(self._did_registry.keys())

    # ─── LGPD/GDPR Compliance ─────────────────────────────────────────────

    def anonymize_state(self, state: Dict[str, Any], fields_to_anonymize: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Anonymize sensitive fields in a state dictionary for LGPD/GDPR compliance.

        Replaces personally identifiable information with anonymized hashes,
        preserving data structure while removing traceability to individuals.

        Args:
            state: The state dictionary to anonymize
            fields_to_anonymize: Specific fields to anonymize (defaults to common PII fields)

        Returns:
            Anonymized copy of the state dictionary
        """
        default_pii_fields = [
            "face_id", "person_id", "track_id", "name", "email",
            "phone", "address", "license_plate", "mac_address",
            "ip_address", "device_id", "biometric_data", "face_encoding", "plate",
        ]
        fields = fields_to_anonymize or default_pii_fields
        anonymized = self._deep_anonymize(state, fields)

        # Log anonymization event
        entry = AuditEntry(
            entry_id=f"audit_{uuid.uuid4().hex[:12]}",
            did=self._did,
            action="anonymize_state",
            target_node="system",
            timestamp=datetime.now(timezone.utc).isoformat(),
            signature="N/A",
            parameters={"fields_anonymized": fields},
            result="anonymized",
            anonymized=True,
        )
        self._audit_trail.append(entry)

        return anonymized

    def get_data_retention_policy(self) -> Dict[str, Any]:
        """
        Get the current data retention policy for LGPD/GDPR compliance.

        Returns:
            Dictionary describing retention periods and policies
        """
        return {
            "audit_trail_retention_days": 90,
            "pii_retention_days": 30,
            "anonymization_method": "SHA256-hash",
            "data_subject_rights": [
                "right_to_access",
                "right_to_rectification",
                "right_to_erasure",
                "right_to_portability",
                "right_to_restrict_processing",
            ],
            "legal_basis": "legitimate_interest",
            "dpo_contact": "dpo@neventech.com",
        }

    def export_subject_data(self, subject_id: str) -> Dict[str, Any]:
        """
        Export all data related to a data subject (LGPD Art. 18 / GDPR Art. 15).

        Args:
            subject_id: The identifier of the data subject

        Returns:
            All stored data related to the subject
        """
        related_entries = [
            e.to_dict() for e in self._audit_trail
            if subject_id in str(e.parameters) or subject_id in e.target_node
        ]
        return {
            "subject_id": subject_id,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "entries": related_entries,
            "total_records": len(related_entries),
        }

    def erase_subject_data(self, subject_id: str) -> Dict[str, Any]:
        """
        Erase data related to a data subject (LGPD Art. 18 / GDPR Art. 17).

        Note: Audit entries are anonymized rather than deleted to maintain
        system integrity while respecting erasure rights.

        Args:
            subject_id: The identifier of the data subject

        Returns:
            Summary of erasure operation
        """
        erased_count = 0
        for entry in self._audit_trail:
            if subject_id in str(entry.parameters) or subject_id in entry.target_node:
                entry.anonymized = True
                entry.parameters = {"redacted": True}
                erased_count += 1

        return {
            "subject_id": subject_id,
            "erased_at": datetime.now(timezone.utc).isoformat(),
            "records_anonymized": erased_count,
            "status": "completed",
        }

    # ─── Identity Verification ────────────────────────────────────────────

    def verify_identity(self, did: str, challenge: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify an agent's identity by DID.

        Args:
            did: The DID to verify
            challenge: Optional challenge string for proof-of-possession

        Returns:
            Verification result dictionary
        """
        doc = self._did_registry.get(did)
        if not doc:
            return {
                "verified": False,
                "reason": "DID not found in registry",
                "did": did,
            }

        result = {
            "verified": True,
            "did": did,
            "node_type": doc.node_type,
            "location": doc.location,
            "created": doc.created,
            "authentication_methods": doc.authentication,
        }

        # If challenge provided, sign it as proof-of-possession
        if challenge and did == self._did:
            proof = hmac.new(
                self._secret_key,
                challenge.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            result["challenge_response"] = proof

        return result

    # ─── Private Methods ──────────────────────────────────────────────────

    def _build_canonical_payload(
        self,
        action: str,
        target_node: str,
        parameters: Dict[str, Any],
        timestamp: str,
    ) -> str:
        """Build a canonical string representation for signing."""
        canonical = {
            "did": self._did,
            "action": action,
            "target_node": target_node,
            "parameters": parameters,
            "timestamp": timestamp,
        }
        # Sort keys for deterministic serialization
        return json.dumps(canonical, sort_keys=True, separators=(",", ":"))

    def _persist_audit_entry(self, entry: AuditEntry) -> None:
        """Persist an audit entry to the local JSON log file."""
        try:
            log_file = self._audit_log_dir / f"audit_{self._unique_id}.jsonl"
            with open(log_file, "a") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")
        except Exception as e:
            logger.warning(f"Failed to persist audit entry: {e}")

    def _deep_anonymize(self, data: Any, fields: List[str]) -> Any:
        """Recursively anonymize fields in nested data structures."""
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if key in fields and value is not None:
                    # Hash the value for anonymization
                    hash_val = hashlib.sha256(str(value).encode()).hexdigest()[:16]
                    # For biometric fields, set to None (LGPD Art. 11)
                    biometric_fields = ["face_encoding", "biometric", "fingerprint", "retina"]
                    plate_fields = ["plate", "license_plate"]
                    if key in plate_fields:
                        result[key] = "[REDACTED]"
                    elif key in biometric_fields:
                        result[key] = None
                    else:
                        result[key] = f"anon_{hash_val}"
                else:
                    result[key] = self._deep_anonymize(value, fields)
            return result
        elif isinstance(data, list):
            return [self._deep_anonymize(item, fields) for item in data]
        return data

    def __repr__(self) -> str:
        return f"KAISIdentity(did='{self._did}', node_type='{self._node_type}', location='{self._location}')"

    def __str__(self) -> str:
        return self._did
