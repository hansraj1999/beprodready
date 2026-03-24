import { requestJson } from "./client";
import type { GraphRead, GraphSummary } from "../types/api";
import type { GraphExport } from "../types/graph";

export function listGraphs(token: string): Promise<GraphSummary[]> {
  return requestJson<GraphSummary[]>("/api/v1/graphs", { method: "GET", token });
}

export function getGraph(token: string, graphId: string): Promise<GraphRead> {
  return requestJson<GraphRead>(`/api/v1/graphs/${encodeURIComponent(graphId)}`, {
    method: "GET",
    token,
  });
}

export function createGraph(
  token: string,
  body: { name: string; description?: string | null } & GraphExport,
): Promise<GraphRead> {
  return requestJson<GraphRead>("/api/v1/graphs", {
    method: "POST",
    token,
    body: JSON.stringify({
      name: body.name,
      description: body.description ?? null,
      nodes: body.nodes as unknown as Record<string, unknown>[],
      edges: body.edges as unknown as Record<string, unknown>[],
    }),
  });
}

export function updateGraph(
  token: string,
  graphId: string,
  body: {
    name?: string | null;
    description?: string | null;
    nodes?: GraphExport["nodes"];
    edges?: GraphExport["edges"];
  },
): Promise<GraphRead> {
  return requestJson<GraphRead>(`/api/v1/graphs/${encodeURIComponent(graphId)}`, {
    method: "PUT",
    token,
    body: JSON.stringify(body),
  });
}
