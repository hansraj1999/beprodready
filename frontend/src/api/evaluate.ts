import { requestJson } from "./client";
import type { EvaluateResponse } from "../types/api";
import type { GraphExport } from "../types/graph";

export function evaluateGraph(token: string, graph: GraphExport): Promise<EvaluateResponse> {
  return requestJson<EvaluateResponse>("/api/v1/evaluate", {
    method: "POST",
    token,
    body: JSON.stringify({
      nodes: graph.nodes as unknown as Record<string, unknown>[],
      edges: graph.edges as unknown as Record<string, unknown>[],
    }),
  });
}
