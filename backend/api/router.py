"""
NEXUS — Central API router.
Aggregates all route modules.
"""

from fastapi import APIRouter

from backend.api.routes.topology import router as topology_router
from backend.api.routes.simulation import router as simulation_router
from backend.api.routes.optimizer import router as optimizer_router

api_router = APIRouter()
api_router.include_router(topology_router)
api_router.include_router(simulation_router)
api_router.include_router(optimizer_router)

