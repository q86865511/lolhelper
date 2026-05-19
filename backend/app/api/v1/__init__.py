"""API v1 router aggregation."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, meta, stats

api_v1_router = APIRouter()
api_v1_router.include_router(auth.router)
api_v1_router.include_router(meta.router)
api_v1_router.include_router(stats.router)
