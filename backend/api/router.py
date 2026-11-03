"""
NEXUS — Central API router.
Aggregates all route modules.
"""

from fastapi import APIRouter

from backend.api.routes.cascade import router as cascade_router
from backend.api.routes.monitor import router as monitor_router
from backend.api.routes.optimizer import router as optimizer_router
from backend.api.routes.recovery import router as recovery_router
from backend.api.routes.simulation import router as simulation_router
from backend.api.routes.topology import router as topology_router

api_router = APIRouter()
api_router.include_router(topology_router)
api_router.include_router(simulation_router)
api_router.include_router(cascade_router)
api_router.include_router(optimizer_router)
api_router.include_router(recovery_router)
api_router.include_router(monitor_router)
