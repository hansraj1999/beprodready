import type { Edge, Node } from "@xyflow/react";
import type { ArchitectNodeData, GraphExport } from "../types/graph";

export function toGraphExport(nodes: Node<ArchitectNodeData>[], edges: Edge[]): GraphExport {
  return {
    nodes: nodes.map((n) => ({
      id: n.id,
      type: n.data.kind,
      label: n.data.label,
      position: { x: n.position.x, y: n.position.y },
      data: {
        kind: n.data.kind,
        label: n.data.label,
        description: n.data.description ?? "",
      },
    })),
    edges: edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      label: typeof e.label === "string" ? e.label : undefined,
    })),
  };
}

export function downloadJson(filename: string, data: unknown): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export async function copyJsonToClipboard(data: unknown): Promise<void> {
  await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
}
