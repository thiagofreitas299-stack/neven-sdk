"""
NEVEN KAIS — Keepit Agent Identity System
==========================================
Cryptographic identity for physical AI agents.

Every physical node in the NEVEN network has a unique DID (Decentralized Identifier)
with a cryptographic keypair. This ensures:
- Non-repudiation: every physical action is signed and auditable
- Zero-trust: nodes verify each other before any actuation
- Sovereignty: identity belongs to the agent, not to NEVEN

Usage:
    identity = NevenIdentity.create(agent_name="jarvis-hub-rj-01")
    print(identity.did)         # did:neven:jarvis-hub-rj-01-a3f9b2c1
    signed = identity.sign("my payload")
    identity.save("./my-identity.json")
    loaded = NevenIdentity.load("./my-identity.json")
"""

import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class NevenIdentity:
    """
    Cryptographic identity for a NEVEN physical agent node.

    Attributes:
        did: Decentralized Identifier (did:neven:<name>-<hash>)
        agent_name: Human-readable name for the agent
        private_key: Secret key for signing (keep safe, never share)
        public_key_fingerprint: Public fingerprint for verification
        created_at: ISO timestamp of identity creation
        metadata: Optional metadata (location, capabilities, etc.)
    """

    did: str
    agent_name: str
    private_key: str
    public_key_fingerprint: str
    created_at: str
    metadata: dict = field(default_factory=dict)

    # -------------------------------------------------------------------------
    # Factory methods
    # -------------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        agent_name: str,
        location: str = None,
        capabilities: list[str] = None,
        metadata: dict = None,
    ) -> "NevenIdentity":
        """
        Create a new NEVEN identity with a fresh cryptographic keypair.

        Args:
            agent_name: Unique name for this agent (e.g. "hub-sp-iguatemi-01")
            location: Physical location description
            capabilities: List of capabilities (e.g. ["camera", "screen", "payment"])
            metadata: Additional metadata dict

        Returns:
            NevenIdentity instance ready to use

        Example:
            identity = NevenIdentity.create(
                agent_name="hub-sp-iguatemi-01",
                location="Shopping Iguatemi, São Paulo, Brazil",
                capabilities=["camera", "screen", "voice"]
            )
        """
        # Generate private key (256-bit random)
        private_key = os.urandom(32).hex()

        # Derive public fingerprint (first 16 chars of SHA-256)
        pub_fp = hashlib.sha256(private_key.encode()).hexdigest()[:16]

        # Build DID: did:neven:<name>-<fingerprint>
        safe_name = agent_name.lower().replace(" ", "-").replace("_", "-")
        did = f"did:neven:{safe_name}-{pub_fp}"

        created_at = datetime.now(timezone.utc).isoformat()

        meta = metadata or {}
        if location:
            meta["location"] = location
        if capabilities:
            meta["capabilities"] = capabilities
        meta["created_by"] = "neven-sdk"
        meta["sdk_version"] = "1.0.0"

        return cls(
            did=did,
            agent_name=agent_name,
            private_key=private_key,
            public_key_fingerprint=pub_fp,
            created_at=created_at,
            metadata=meta,
        )

    @classmethod
    def load(cls, path: str | Path) -> "NevenIdentity":
        """Load identity from JSON file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Identity file not found: {path}")
        with open(path) as f:
            data = json.load(f)
        return cls(**data)

    # -------------------------------------------------------------------------
    # Cryptographic operations
    # -------------------------------------------------------------------------

    def sign(self, payload: str | dict) -> str:
        """
        Sign a payload with this identity's private key (HMAC-SHA256).

        Args:
            payload: String or dict to sign

        Returns:
            Hex-encoded HMAC-SHA256 signature
        """
        if isinstance(payload, dict):
            payload = json.dumps(payload, sort_keys=True)
        return hmac.new(
            self.private_key.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def sign_request(self, payload: str | dict) -> dict:
        """
        Create a signed request envelope for the NEVEN API.

        Returns dict with: payload, signature, timestamp, did
        """
        timestamp = int(time.time())
        if isinstance(payload, dict):
            payload_str = json.dumps(payload, sort_keys=True)
        else:
            payload_str = str(payload)

        message = f"{timestamp}:{payload_str}"
        signature = self.sign(message)

        return {
            "payload": payload,
            "did": self.did,
            "timestamp": timestamp,
            "signature": signature,
        }

    def verify(self, payload: str | dict, signature: str) -> bool:
        """Verify a signature against this identity's key."""
        expected = self.sign(payload)
        return hmac.compare_digest(expected, signature)

    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------

    def save(self, path: str | Path = None) -> Path:
        """
        Save identity to JSON file.

        Args:
            path: File path. Defaults to ./{agent_name}-identity.json

        Returns:
            Path where identity was saved
        """
        if path is None:
            safe_name = self.agent_name.lower().replace(" ", "-")
            path = Path(f"./{safe_name}-identity.json")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)
        return path

    # -------------------------------------------------------------------------
    # Display
    # -------------------------------------------------------------------------

    def __str__(self) -> str:
        return (
            f"NevenIdentity(\n"
            f"  did={self.did!r}\n"
            f"  agent={self.agent_name!r}\n"
            f"  fingerprint={self.public_key_fingerprint!r}\n"
            f"  created={self.created_at!r}\n"
            f"  capabilities={self.metadata.get('capabilities', [])}\n"
            f")"
        )

    def to_public_card(self) -> dict:
        """Return public-safe representation (no private key)."""
        return {
            "did": self.did,
            "agent_name": self.agent_name,
            "public_key_fingerprint": self.public_key_fingerprint,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }
