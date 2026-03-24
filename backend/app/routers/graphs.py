from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.graph import GraphCreate, GraphRead, GraphSummary, GraphUpdate
from app.services import graph_service
from app.services.graph_errors import GraphForbiddenError, GraphNotFoundError

router = APIRouter()


@router.get("", response_model=list[GraphSummary])
async def list_graphs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[GraphSummary]:
    return await graph_service.list_graphs_for_user(db, current_user.id)


@router.post("", response_model=GraphRead, status_code=status.HTTP_201_CREATED)
async def create_graph(
    payload: GraphCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GraphRead:
    try:
        return await graph_service.create_graph(db, payload, current_user.id)
    except ValueError as exc:
        if str(exc) == "owner_not_found":
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Owner user not found",
            ) from exc
        raise


@router.get("/{graph_id}", response_model=GraphRead)
async def get_graph(
    graph_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GraphRead:
    try:
        return await graph_service.get_graph_for_user(db, graph_id, current_user.id)
    except GraphNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Graph not found")
    except GraphForbiddenError:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this graph",
        )


@router.put("/{graph_id}", response_model=GraphRead)
async def update_graph(
    graph_id: UUID,
    payload: GraphUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GraphRead:
    try:
        return await graph_service.update_graph_for_user(
            db, graph_id, current_user.id, payload
        )
    except GraphNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Graph not found")
    except GraphForbiddenError:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Not allowed to modify this graph",
        )


@router.delete("/{graph_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_graph(
    graph_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        await graph_service.delete_graph_for_user(db, graph_id, current_user.id)
    except GraphNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Graph not found")
    except GraphForbiddenError:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Not allowed to delete this graph",
        )
