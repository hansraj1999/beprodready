import logging
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.graph import Graph
from app.schemas.graph import GraphCreate, GraphRead, GraphSummary, GraphUpdate
from app.services import usage_service
from app.services.graph_errors import GraphForbiddenError, GraphNotFoundError
from app.services.user_service import get_user

logger = logging.getLogger(__name__)


def _to_read(graph: Graph) -> GraphRead:
    data = graph.graph_data or {}
    return GraphRead(
        id=graph.id,
        owner_id=graph.owner_id,
        name=graph.name,
        description=graph.description,
        nodes=list(data.get("nodes") or []),
        edges=list(data.get("edges") or []),
        created_at=graph.created_at,
        updated_at=graph.updated_at,
    )


async def create_graph(
    db: AsyncSession, payload: GraphCreate, owner_id: UUID
) -> GraphRead:
    owner = await get_user(db, owner_id)
    if owner is None:
        raise ValueError("owner_not_found")

    graph_data = {"nodes": payload.nodes, "edges": payload.edges}
    graph = Graph(
        owner_id=owner_id,
        name=payload.name,
        description=payload.description,
        graph_data=graph_data,
    )
    db.add(graph)
    await db.flush()
    await usage_service.record_usage(
        db,
        action="graph.create",
        user_id=owner_id,
        graph_id=graph.id,
        metadata={"name": payload.name},
    )
    await db.commit()
    await db.refresh(graph)
    logger.info(
        "graph.created",
        extra={"graph_id": str(graph.id), "owner_id": str(owner_id)},
    )
    return _to_read(graph)


async def list_graphs_for_user(db: AsyncSession, user_id: UUID) -> list[GraphSummary]:
    result = await db.execute(
        select(Graph)
        .where(Graph.owner_id == user_id)
        .order_by(Graph.updated_at.desc())
    )
    graphs = result.scalars().all()
    return [
        GraphSummary(
            id=g.id,
            name=g.name,
            description=g.description,
            updated_at=g.updated_at,
        )
        for g in graphs
    ]


async def get_graph_for_user(
    db: AsyncSession, graph_id: UUID, user_id: UUID
) -> GraphRead:
    result = await db.execute(select(Graph).where(Graph.id == graph_id))
    graph = result.scalar_one_or_none()
    if graph is None:
        raise GraphNotFoundError
    if graph.owner_id != user_id:
        raise GraphForbiddenError

    snapshot = _to_read(graph)
    await usage_service.record_usage(
        db,
        action="graph.read",
        user_id=graph.owner_id,
        graph_id=graph.id,
    )
    await db.commit()
    logger.debug("graph.read", extra={"graph_id": str(graph_id)})
    return snapshot


async def update_graph_for_user(
    db: AsyncSession, graph_id: UUID, user_id: UUID, payload: GraphUpdate
) -> GraphRead:
    result = await db.execute(select(Graph).where(Graph.id == graph_id))
    graph = result.scalar_one_or_none()
    if graph is None:
        raise GraphNotFoundError
    if graph.owner_id != user_id:
        raise GraphForbiddenError

    if payload.name is not None:
        graph.name = payload.name
    if payload.description is not None:
        graph.description = payload.description
    if payload.nodes is not None or payload.edges is not None:
        data = dict(graph.graph_data or {})
        if payload.nodes is not None:
            data["nodes"] = payload.nodes
        if payload.edges is not None:
            data["edges"] = payload.edges
        graph.graph_data = data

    await db.flush()
    await usage_service.record_usage(
        db,
        action="graph.update",
        user_id=graph.owner_id,
        graph_id=graph.id,
    )
    await db.commit()
    await db.refresh(graph)
    logger.info("graph.updated", extra={"graph_id": str(graph_id)})
    return _to_read(graph)


async def delete_graph_for_user(
    db: AsyncSession, graph_id: UUID, user_id: UUID
) -> None:
    result = await db.execute(select(Graph).where(Graph.id == graph_id))
    graph = result.scalar_one_or_none()
    if graph is None:
        raise GraphNotFoundError
    if graph.owner_id != user_id:
        raise GraphForbiddenError

    gid = graph.id
    owner = graph.owner_id
    await usage_service.record_usage(
        db,
        action="graph.delete",
        user_id=owner,
        graph_id=gid,
    )
    await db.execute(delete(Graph).where(Graph.id == graph_id))
    await db.commit()
    logger.info("graph.deleted", extra={"graph_id": str(graph_id)})
