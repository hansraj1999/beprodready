from fastapi import APIRouter

from app.routers import (
    evaluate,
    generate_system,
    graphs,
    health,
    interview,
    payment,
    simulate,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(graphs.router, prefix="/graphs", tags=["graphs"])
api_router.include_router(payment.router, prefix="/payment", tags=["payment"])
api_router.include_router(evaluate.router, prefix="/evaluate", tags=["evaluate"])
api_router.include_router(interview.router, prefix="/interview", tags=["interview"])
api_router.include_router(simulate.router, prefix="/simulate", tags=["simulate"])
api_router.include_router(
    generate_system.router, prefix="/generate-system", tags=["generate-system"]
)
