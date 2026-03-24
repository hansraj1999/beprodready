import type { Edge, Node } from "@xyflow/react";
import type { ArchitectNodeData, NodeKind } from "../types/graph";
import { defaultLabelForKind } from "../types/graph";

const KINDS: NodeKind[] = ["api", "db", "cache", "queue"];

function asKind(v: unknown): NodeKind {
  if (typeof v === "string" && KINDS.includes(v as NodeKind)) {
    return v as NodeKind;
  }
  return "api";
}

function nodeId(raw: Record<string, unknown>): string {
  if (typeof raw.id === "string" && raw.id.length > 0) return raw.id;
  return crypto.randomUUID();
}

/**
 * Maps API / JSON graph nodes into React Flow nodes.
 */
export function nodesFromApiPayload(rows: unknown[]): Node<ArchitectNodeData>[] {
  return rows.map((row) => {
    const o = row as Record<string, unknown>;
    const id = nodeId(o);
    const dataObj =
      o.data && typeof o.data === "object" && o.data !== null
        ? (o.data as Record<string, unknown>)
        : {};
    const kind = asKind(o.type ?? dataObj.kind);
    const pos =
      o.position && typeof o.position === "object" && o.position !== null
        ? (o.position as Record<string, unknown>)
        : {};
    const position = {
      x: Number(pos.x ?? 0),
      y: Number(pos.y ?? 0),
    };
    const label =
      typeof dataObj.label === "string"
        ? dataObj.label
        : typeof o.label === "string"
          ? o.label
          : defaultLabelForKind(kind);
    const description =
      typeof dataObj.description === "string" ? dataObj.description : "";

    return {
      id,
      type: kind,
      position,
      data: { kind, label, description },
    };
  });
}

export function edgesFromApiPayload(rows: unknown[]): Edge[] {
  return rows.map((row, index) => {
    const e = row as Record<string, unknown>;
    const source = String(e.source ?? "");
    const target = String(e.target ?? "");
    const id =
      typeof e.id === "string" && e.id.length > 0
        ? e.id
        : `e-${source}-${target}-${index}`;
    return {
      id,
      source,
      target,
      animated: true,
    };
  });
}
