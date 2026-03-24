export type NodeKind = "api" | "db" | "cache" | "queue";

export interface ArchitectNodeData extends Record<string, unknown> {
  kind: NodeKind;
  label: string;
  description?: string;
}

/** Payload aligned with backend `nodes` / `edges` JSON. */
export interface GraphExport {
  nodes: ExportedNode[];
  edges: ExportedEdge[];
}

export interface ExportedNode {
  id: string;
  type: NodeKind;
  label: string;
  position: { x: number; y: number };
  data: ArchitectNodeData;
}

export interface ExportedEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
}

export const PALETTE_ITEMS: { kind: NodeKind; label: string; hint: string }[] = [
  { kind: "api", label: "API", hint: "HTTP / gateway service" },
  { kind: "db", label: "DB", hint: "Database" },
  { kind: "cache", label: "Cache", hint: "Redis / CDN" },
  { kind: "queue", label: "Queue", hint: "Kafka / SQS" },
];

export function defaultLabelForKind(kind: NodeKind): string {
  return PALETTE_ITEMS.find((p) => p.kind === kind)?.label ?? kind;
}
