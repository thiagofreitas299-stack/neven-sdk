"""
NEVEN Pricing Tier System

Defines tier limits, rate limiting middleware, tier validation decorators,
and usage tracking for the NEVEN platform.

Tiers:
    - Free:       3 nodes, 100 req/hr
    - Starter:    5 nodes, 1000 req/hr
    - Business:   50 nodes, 10000 req/hr
    - Enterprise: Unlimited
"""

import time
import logging
import functools
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("neven.tiers")


# ─── Tier Definitions ─────────────────────────────────────────────────────────

class TierName(str, Enum):
    """Available pricing tiers."""
    FREE = "free"
    STARTER = "starter"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


@dataclass
class TierLimits:
    """Limits for a pricing tier."""
    name: TierName
    max_nodes: int
    max_requests_per_hour: int
    max_sessions: int
    max_events_per_second: int
    websocket_enabled: bool
    analytics_enabled: bool
    priority_support: bool
    custom_safety_rules: bool
    sla_uptime: float  # percentage

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name.value,
            "max_nodes": self.max_nodes if self.max_nodes >= 0 else "unlimited",
            "max_requests_per_hour": self.max_requests_per_hour if self.max_requests_per_hour >= 0 else "unlimited",
            "max_sessions": self.max_sessions if self.max_sessions >= 0 else "unlimited",
            "max_events_per_second": self.max_events_per_second if self.max_events_per_second >= 0 else "unlimited",
            "websocket_enabled": self.websocket_enabled,
            "analytics_enabled": self.analytics_enabled,
            "priority_support": self.priority_support,
            "custom_safety_rules": self.custom_safety_rules,
            "sla_uptime": self.sla_uptime,
        }


# ─── Tier Registry ────────────────────────────────────────────────────────────

TIER_DEFINITIONS: Dict[TierName, TierLimits] = {
    TierName.FREE: TierLimits(
        name=TierName.FREE,
        max_nodes=3,
        max_requests_per_hour=100,
        max_sessions=1,
        max_events_per_second=5,
        websocket_enabled=False,
        analytics_enabled=False,
        priority_support=False,
        custom_safety_rules=False,
        sla_uptime=95.0,
    ),
    TierName.STARTER: TierLimits(
        name=TierName.STARTER,
        max_nodes=5,
        max_requests_per_hour=1000,
        max_sessions=5,
        max_events_per_second=50,
        websocket_enabled=True,
        analytics_enabled=True,
        priority_support=False,
        custom_safety_rules=False,
        sla_uptime=99.0,
    ),
    TierName.BUSINESS: TierLimits(
        name=TierName.BUSINESS,
        max_nodes=50,
        max_requests_per_hour=10000,
        max_sessions=50,
        max_events_per_second=500,
        websocket_enabled=True,
        analytics_enabled=True,
        priority_support=True,
        custom_safety_rules=True,
        sla_uptime=99.9,
    ),
    TierName.ENTERPRISE: TierLimits(
        name=TierName.ENTERPRISE,
        max_nodes=-1,  # unlimited
        max_requests_per_hour=-1,  # unlimited
        max_sessions=-1,  # unlimited
        max_events_per_second=-1,  # unlimited
        websocket_enabled=True,
        analytics_enabled=True,
        priority_support=True,
        custom_safety_rules=True,
        sla_uptime=99.99,
    ),
}


def get_tier(tier_name: str) -> TierLimits:
    """Get tier limits by name."""
    try:
        return TIER_DEFINITIONS[TierName(tier_name.lower())]
    except (ValueError, KeyError):
        return TIER_DEFINITIONS[TierName.FREE]


# ─── Usage Tracker ────────────────────────────────────────────────────────────

@dataclass
class UsageRecord:
    """Tracks usage for a single API key."""
    api_key: str
    tier: TierName
    requests_this_hour: int = 0
    hour_start: float = field(default_factory=time.time)
    total_requests: int = 0
    total_blocked: int = 0
    nodes_used: int = 0
    active_sessions: int = 0
    last_request_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        tier_limits = TIER_DEFINITIONS[self.tier]
        return {
            "api_key": self.api_key[:12] + "..." if len(self.api_key) > 12 else self.api_key,
            "tier": self.tier.value,
            "requests_this_hour": self.requests_this_hour,
            "max_requests_per_hour": tier_limits.max_requests_per_hour if tier_limits.max_requests_per_hour >= 0 else "unlimited",
            "total_requests": self.total_requests,
            "total_blocked": self.total_blocked,
            "nodes_used": self.nodes_used,
            "active_sessions": self.active_sessions,
            "last_request_at": self.last_request_at,
            "usage_percentage": self._usage_percentage(),
        }

    def _usage_percentage(self) -> float:
        tier_limits = TIER_DEFINITIONS[self.tier]
        if tier_limits.max_requests_per_hour < 0:
            return 0.0
        if tier_limits.max_requests_per_hour == 0:
            return 100.0
        return round(
            (self.requests_this_hour / tier_limits.max_requests_per_hour) * 100, 2
        )


class UsageTracker:
    """
    Tracks API usage per API key with sliding-window rate limiting.
    """

    def __init__(self):
        self._records: Dict[str, UsageRecord] = {}
        self._tier_map: Dict[str, TierName] = {}

    def register_key(self, api_key: str, tier: TierName = TierName.FREE) -> None:
        """Register an API key with a tier."""
        self._tier_map[api_key] = tier
        if api_key not in self._records:
            self._records[api_key] = UsageRecord(api_key=api_key, tier=tier)

    def get_tier_for_key(self, api_key: str) -> TierName:
        """Get the tier for an API key."""
        return self._tier_map.get(api_key, TierName.FREE)

    def check_rate_limit(self, api_key: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if a request is within rate limits.

        Returns:
            Tuple of (allowed: bool, info: dict)
        """
        tier = self.get_tier_for_key(api_key)
        limits = TIER_DEFINITIONS[tier]

        # Enterprise has no limits
        if limits.max_requests_per_hour < 0:
            self._record_request(api_key, tier)
            return True, {"remaining": "unlimited", "tier": tier.value}

        record = self._get_or_create_record(api_key, tier)

        # Reset counter if hour has passed
        now = time.time()
        if now - record.hour_start >= 3600:
            record.requests_this_hour = 0
            record.hour_start = now

        # Check limit
        if record.requests_this_hour >= limits.max_requests_per_hour:
            record.total_blocked += 1
            remaining = 0
            reset_in = int(3600 - (now - record.hour_start))
            return False, {
                "remaining": remaining,
                "tier": tier.value,
                "reset_in_seconds": reset_in,
                "limit": limits.max_requests_per_hour,
            }

        # Allow and record
        self._record_request(api_key, tier)
        remaining = limits.max_requests_per_hour - record.requests_this_hour
        return True, {"remaining": remaining, "tier": tier.value}

    def get_usage(self, api_key: str) -> Dict[str, Any]:
        """Get usage statistics for an API key."""
        tier = self.get_tier_for_key(api_key)
        record = self._get_or_create_record(api_key, tier)
        return record.to_dict()

    def get_all_usage(self) -> Dict[str, Any]:
        """Get usage statistics for all tracked keys."""
        return {key: record.to_dict() for key, record in self._records.items()}

    def _get_or_create_record(self, api_key: str, tier: TierName) -> UsageRecord:
        """Get or create a usage record."""
        if api_key not in self._records:
            self._records[api_key] = UsageRecord(api_key=api_key, tier=tier)
        return self._records[api_key]

    def _record_request(self, api_key: str, tier: TierName) -> None:
        """Record a successful request."""
        record = self._get_or_create_record(api_key, tier)
        record.requests_this_hour += 1
        record.total_requests += 1
        record.last_request_at = datetime.now(timezone.utc).isoformat()


# ─── Global Usage Tracker Instance ────────────────────────────────────────────

_usage_tracker = UsageTracker()


def get_usage_tracker() -> UsageTracker:
    """Get the global usage tracker instance."""
    return _usage_tracker


# ─── FastAPI Rate Limiter Middleware ──────────────────────────────────────────

class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that enforces tier-based rate limits.

    Extracts the API key from the Authorization header and checks
    against the configured tier limits.
    """

    def __init__(self, app, usage_tracker: Optional[UsageTracker] = None):
        super().__init__(app)
        self.tracker = usage_tracker or get_usage_tracker()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks and docs
        path = request.url.path
        if path in ("/health", "/docs", "/redoc", "/openapi.json", "/metrics", "/"):
            return await call_next(request)

        # Extract API key from Authorization header
        auth_header = request.headers.get("Authorization", "")
        api_key = ""
        if auth_header.startswith("Bearer "):
            api_key = auth_header[7:]

        if not api_key:
            # Allow unauthenticated requests with Free tier limits
            api_key = "anonymous"

        # Check rate limit
        allowed, info = self.tracker.check_rate_limit(api_key)

        if not allowed:
            return Response(
                content=f'{{"error": "Rate limit exceeded", "tier": "{info["tier"]}", '
                        f'"reset_in_seconds": {info.get("reset_in_seconds", 0)}, '
                        f'"limit": {info.get("limit", 0)}}}',
                status_code=429,
                media_type="application/json",
                headers={
                    "X-RateLimit-Limit": str(info.get("limit", 0)),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(info.get("reset_in_seconds", 0)),
                    "Retry-After": str(info.get("reset_in_seconds", 0)),
                },
            )

        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(info.get("remaining", "unlimited"))
        response.headers["X-RateLimit-Tier"] = info.get("tier", "free")
        return response


# ─── Tier Validation Decorator ────────────────────────────────────────────────

def require_tier(minimum_tier: TierName):
    """
    Decorator that requires a minimum tier for an endpoint.

    Usage:
        @require_tier(TierName.BUSINESS)
        async def premium_endpoint(request: Request):
            ...
    """
    tier_order = {
        TierName.FREE: 0,
        TierName.STARTER: 1,
        TierName.BUSINESS: 2,
        TierName.ENTERPRISE: 3,
    }

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Try to extract request from args/kwargs
            request = kwargs.get("request")
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request:
                auth_header = request.headers.get("Authorization", "")
                api_key = auth_header[7:] if auth_header.startswith("Bearer ") else "anonymous"
                tracker = get_usage_tracker()
                current_tier = tracker.get_tier_for_key(api_key)

                if tier_order.get(current_tier, 0) < tier_order.get(minimum_tier, 0):
                    raise HTTPException(
                        status_code=403,
                        detail={
                            "error": "Insufficient tier",
                            "current_tier": current_tier.value,
                            "required_tier": minimum_tier.value,
                            "upgrade_url": "https://neventech.com/pricing",
                        },
                    )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# ─── Pricing Display ──────────────────────────────────────────────────────────

def get_pricing_table() -> Dict[str, Any]:
    """Get the full pricing table for display."""
    return {
        "tiers": {name.value: limits.to_dict() for name, limits in TIER_DEFINITIONS.items()},
        "currency": "USD",
        "billing_period": "monthly",
        "prices": {
            "free": 0,
            "starter": 49,
            "business": 299,
            "enterprise": "custom",
        },
    }
