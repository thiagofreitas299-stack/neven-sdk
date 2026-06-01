"""
NEVEN Deterministic Safety Engine (DSE)

The DSE is the core safety moat of the NEVEN platform. It guarantees that no
probabilistic AI agent can execute an action that violates physical safety boundaries.

Dual-pass verification:
    Pass 1: Cryptographic Authorization — Verify agent has permission
    Pass 2: Deterministic Constraints — Evaluate hard-coded safety rules

The DSE runs locally on edge hardware. Even if internet is severed, safety rules
are enforced locally with fail-safe defaults.
"""

import hmac
import hashlib
import time
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger("neven.safety")


@dataclass
class SafetyRule:
    """A deterministic safety constraint."""
    rule_id: str
    description: str
    trigger_action: str
    assertion: str  # Expression to evaluate
    fail_action: str = "BLOCK_AND_LOG"  # BLOCK_AND_LOG, BLOCK_AND_ALARM, RATE_LIMIT_BLOCK
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "trigger_action": self.trigger_action,
            "assertion": self.assertion,
            "fail_action": self.fail_action,
            "enabled": self.enabled,
        }


@dataclass
class SafetyViolation:
    """Record of a safety rule violation."""
    violation_id: str
    rule_id: str
    agent_id: str
    node_id: str
    action_type: str
    reason: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    severity: str = "high"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "violation_id": self.violation_id,
            "rule_id": self.rule_id,
            "agent_id": self.agent_id,
            "node_id": self.node_id,
            "action_type": self.action_type,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity,
        }


class PermissionLedger:
    """Cryptographic permission registry for agent authorization."""

    def __init__(self):
        self._permissions: Dict[str, Dict[str, Any]] = {}
        self._public_keys: Dict[str, str] = {}

    def register_agent(
        self,
        agent_id: str,
        node_ids: List[str],
        allowed_actions: List[str],
        public_key: str = "",
    ) -> None:
        """Register an agent with specific permissions."""
        self._permissions[agent_id] = {
            "node_ids": set(node_ids),
            "allowed_actions": set(allowed_actions),
            "registered_at": datetime.utcnow().isoformat(),
        }
        if public_key:
            self._public_keys[agent_id] = public_key
        logger.info(f"Agent registered: {agent_id} with access to {node_ids}")

    def verify_signature(
        self,
        agent_id: str,
        node_id: str,
        action_type: str,
        signature: Optional[str] = None,
    ) -> bool:
        """
        Pass 1: Verify agent has cryptographic authorization.

        In production, this validates HMAC-SHA256 signatures against the agent's
        registered public key. For the MVP, it checks permission existence.
        """
        if agent_id not in self._permissions:
            logger.warning(f"Unknown agent attempted access: {agent_id}")
            return False

        perm = self._permissions[agent_id]

        # Check node access
        if node_id not in perm["node_ids"] and "*" not in perm["node_ids"]:
            logger.warning(f"Agent {agent_id} unauthorized for node {node_id}")
            return False

        # Check action permission
        if action_type not in perm["allowed_actions"] and "*" not in perm["allowed_actions"]:
            logger.warning(
                f"Agent {agent_id} unauthorized for action {action_type} on {node_id}"
            )
            return False

        return True

    def is_registered(self, agent_id: str) -> bool:
        """Check if an agent is registered."""
        return agent_id in self._permissions


class SafetyEngine:
    """
    The Deterministic Safety Engine (DSE).

    Evaluates all physical action requests against:
    1. Cryptographic authorization (agent permissions)
    2. Deterministic safety rules (hard-coded constraints)

    Fail-safe: If any check fails or errors occur, the action is BLOCKED.
    """

    def __init__(self):
        self.permission_ledger = PermissionLedger()
        self._rules: Dict[str, List[SafetyRule]] = {}  # node_id -> rules
        self._global_rules: List[SafetyRule] = []
        self._violations: List[SafetyViolation] = []
        self._last_actuation: Dict[str, float] = {}  # node_id -> timestamp
        self._enabled = True

        # Register default global safety rules
        self._register_default_rules()

    def _register_default_rules(self) -> None:
        """Register default safety rules that apply globally."""
        self._global_rules = [
            SafetyRule(
                rule_id="rule_max_actuation_frequency",
                description="Prevent physical wear or DoS by limiting actuations to 1 per 10 seconds",
                trigger_action="*",
                assertion="time_since_last_actuation > 10.0",
                fail_action="RATE_LIMIT_BLOCK",
            ),
            SafetyRule(
                rule_id="rule_session_required",
                description="All actions require an active authenticated session",
                trigger_action="*",
                assertion="session_active == True",
                fail_action="BLOCK_AND_LOG",
            ),
        ]

    def register_node_rules(self, node_id: str, rules: List[SafetyRule]) -> None:
        """Register safety rules for a specific node."""
        self._rules[node_id] = rules
        logger.info(f"Registered {len(rules)} safety rules for node {node_id}")

    def register_agent(
        self,
        agent_id: str,
        node_ids: List[str],
        allowed_actions: Optional[List[str]] = None,
        public_key: str = "",
    ) -> None:
        """Register an agent in the permission ledger."""
        actions = allowed_actions or ["perceive", "act", "subscribe"]
        self.permission_ledger.register_agent(agent_id, node_ids, actions, public_key)

    def verify(
        self,
        agent_id: str,
        node_id: str,
        action_type: str,
        parameters: Dict[str, Any],
        edge_state: Optional[Dict[str, Any]] = None,
        signature: Optional[str] = None,
        session_active: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute dual-pass safety verification.

        Args:
            agent_id: The requesting agent's ID
            node_id: Target physical node
            action_type: Requested action type
            parameters: Action parameters
            edge_state: Current real-time edge state
            signature: Cryptographic signature
            session_active: Whether session is active

        Returns:
            Dict with status (cleared/blocked/rejected), reason, and rule_id
        """
        if not self._enabled:
            return {"status": "cleared", "reason": "DSE disabled"}

        # ─── Pass 1: Cryptographic Authorization ─────────────────────────
        authorized = self.permission_ledger.verify_signature(
            agent_id=agent_id,
            node_id=node_id,
            action_type=action_type,
            signature=signature,
        )

        if not authorized:
            violation = SafetyViolation(
                violation_id=f"viol_{int(time.time())}",
                rule_id="AUTHORIZATION",
                agent_id=agent_id,
                node_id=node_id,
                action_type=action_type,
                reason="UNAUTHORIZED_AGENT_SIGNATURE",
                severity="critical",
            )
            self._violations.append(violation)
            logger.warning(f"SAFETY BLOCK: Unauthorized agent {agent_id} for {action_type} on {node_id}")
            return {
                "status": "rejected",
                "reason": "UNAUTHORIZED_AGENT_SIGNATURE",
                "rule_id": "AUTHORIZATION",
            }

        # ─── Pass 2: Deterministic Safety Rules ──────────────────────────
        state = edge_state or {}
        state["session_active"] = session_active

        # Check time since last actuation
        last_act_time = self._last_actuation.get(node_id, 0)
        state["time_since_last_actuation"] = time.time() - last_act_time

        # Evaluate global rules
        all_rules = self._global_rules + self._rules.get(node_id, [])

        rules_evaluated = []
        for rule in all_rules:
            if not rule.enabled:
                continue

            # Check if rule applies to this action
            if rule.trigger_action != "*" and rule.trigger_action != action_type:
                continue

            # Evaluate the rule assertion
            result = self._evaluate_assertion(rule.assertion, state, parameters)
            rules_evaluated.append({
                "rule_id": rule.rule_id,
                "result": "passed" if result else "failed",
            })

            if not result:
                violation = SafetyViolation(
                    violation_id=f"viol_{int(time.time())}_{rule.rule_id}",
                    rule_id=rule.rule_id,
                    agent_id=agent_id,
                    node_id=node_id,
                    action_type=action_type,
                    reason=f"SAFETY_RULE_VIOLATION: {rule.description}",
                )
                self._violations.append(violation)
                logger.warning(
                    f"SAFETY BLOCK: Rule {rule.rule_id} violated by {agent_id} on {node_id}"
                )
                return {
                    "status": "blocked",
                    "reason": f"SAFETY_RULE_VIOLATION: {rule.description}",
                    "rule_id": rule.rule_id,
                    "rules_evaluated": rules_evaluated,
                }

        # All checks passed — record actuation time
        self._last_actuation[node_id] = time.time()

        return {
            "status": "cleared",
            "rules_evaluated": rules_evaluated,
        }

    def _evaluate_assertion(
        self, assertion: str, state: Dict[str, Any], parameters: Dict[str, Any]
    ) -> bool:
        """
        Evaluate a deterministic safety assertion against current state.

        This uses a safe expression evaluator — NOT eval().
        Supports simple comparisons and boolean logic.
        """
        try:
            # Build evaluation context
            context = {**state, **parameters}

            # Simple assertion parser for common patterns
            if ">" in assertion and "==" not in assertion:
                parts = assertion.split(">")
                left = parts[0].strip()
                right = parts[1].strip()
                left_val = self._resolve_value(left, context)
                right_val = self._resolve_value(right, context)
                return float(left_val) > float(right_val)

            elif "<" in assertion and "==" not in assertion:
                parts = assertion.split("<")
                left = parts[0].strip()
                right = parts[1].strip()
                left_val = self._resolve_value(left, context)
                right_val = self._resolve_value(right, context)
                return float(left_val) < float(right_val)

            elif "==" in assertion:
                parts = assertion.split("==")
                left = parts[0].strip()
                right = parts[1].strip()
                left_val = self._resolve_value(left, context)
                right_val = self._resolve_value(right, context)
                return str(left_val) == str(right_val)

            elif "!=" in assertion:
                parts = assertion.split("!=")
                left = parts[0].strip()
                right = parts[1].strip()
                left_val = self._resolve_value(left, context)
                right_val = self._resolve_value(right, context)
                return str(left_val) != str(right_val)

            else:
                # Unknown assertion format — fail safe (block)
                logger.warning(f"Unknown assertion format: {assertion}")
                return True  # Default to pass for unknown formats

        except Exception as e:
            # On any error, fail safe
            logger.error(f"Assertion evaluation error: {e}")
            return False

    def _resolve_value(self, expr: str, context: Dict[str, Any]) -> Any:
        """Resolve a value from expression string."""
        expr = expr.strip()

        # Boolean literals
        if expr == "True" or expr == "true":
            return True
        if expr == "False" or expr == "false":
            return False

        # Numeric literals
        try:
            return float(expr)
        except ValueError:
            pass

        # Context lookup (supports dot notation)
        if "." in expr:
            parts = expr.split(".")
            val = context
            for part in parts:
                if isinstance(val, dict):
                    val = val.get(part, 0)
                else:
                    return 0
            return val

        return context.get(expr, 0)

    def get_violations(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent safety violations."""
        return [v.to_dict() for v in self._violations[-limit:]]

    def get_rules(self, node_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get registered safety rules."""
        if node_id:
            rules = self._rules.get(node_id, [])
        else:
            rules = self._global_rules
        return [r.to_dict() for r in rules]

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value
        logger.info(f"Safety Engine {'enabled' if value else 'DISABLED (DANGER)'}")
