"""
Quota monitoring routes.

Models the Antigravity Cockpit extension's quota dashboard data.
"""

from typing import Any, Dict, List

from fastapi import APIRouter

router = APIRouter(prefix="/api/quota", tags=["quota"])


# Mock quota data for Phase 0 — will be wired to real API in Phase 5
_MOCK_QUOTAS: List[Dict[str, Any]] = [
    {
        "model": "gemini-2.5-pro",
        "pool": "Premium",
        "used": 142,
        "limit": 500,
        "unit": "requests/day",
        "reset_at": "2026-02-16T00:00:00Z",
    },
    {
        "model": "gemini-2.5-flash",
        "pool": "Standard",
        "used": 867,
        "limit": 1500,
        "unit": "requests/day",
        "reset_at": "2026-02-16T00:00:00Z",
    },
    {
        "model": "gemini-2.0-flash",
        "pool": "Standard",
        "used": 234,
        "limit": 1500,
        "unit": "requests/day",
        "reset_at": "2026-02-16T00:00:00Z",
    },
]

_SETTINGS: Dict[str, Any] = {
    "warning_threshold": 25,
    "danger_threshold": 10,
    "auto_refresh_seconds": 60,
}


@router.get("/")
async def get_quotas() -> List[Dict[str, Any]]:
    """Get current quota usage for all models.

    Returns:
        List of quota usage dicts.
    """
    return _MOCK_QUOTAS


@router.get("/pools")
async def get_pools() -> List[Dict[str, Any]]:
    """Get quota data grouped by pool.

    Returns:
        List of pool group dicts.
    """
    pools: Dict[str, List[Dict[str, Any]]] = {}
    for q in _MOCK_QUOTAS:
        pool_name = q["pool"]
        if pool_name not in pools:
            pools[pool_name] = []
        pools[pool_name].append(q)

    return [
        {"pool": name, "models": models}
        for name, models in pools.items()
    ]


@router.get("/settings")
async def get_quota_settings() -> Dict[str, Any]:
    """Get quota dashboard settings.

    Returns:
        Settings dict with thresholds and refresh interval.
    """
    return _SETTINGS


@router.post("/settings")
async def update_quota_settings(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Update quota dashboard settings.

    Args:
        payload: Dict with threshold and refresh settings.

    Returns:
        Updated settings dict.
    """
    if "warning_threshold" in payload:
        _SETTINGS["warning_threshold"] = payload["warning_threshold"]
    if "danger_threshold" in payload:
        _SETTINGS["danger_threshold"] = payload["danger_threshold"]
    if "auto_refresh_seconds" in payload:
        _SETTINGS["auto_refresh_seconds"] = payload["auto_refresh_seconds"]
    return _SETTINGS
