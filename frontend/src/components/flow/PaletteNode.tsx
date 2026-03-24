import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import type { ArchitectNodeData } from "../../types/graph";

type ArchNode = Node<ArchitectNodeData>;

const ACCENTS: Record<string, { border: string; badge: string }> = {
  api: { border: "var(--node-api)", badge: "rgba(59, 130, 246, 0.2)" },
  db: { border: "var(--node-db)", badge: "rgba(16, 185, 129, 0.2)" },
  cache: { border: "var(--node-cache)", badge: "rgba(245, 158, 11, 0.25)" },
  queue: { border: "var(--node-queue)", badge: "rgba(168, 85, 247, 0.22)" },
};

export function PaletteNode({ data, selected }: NodeProps<ArchNode>) {
  const kind = data.kind;
  const accent = ACCENTS[kind] ?? ACCENTS.api;

  return (
    <div
      className="palette-node"
      style={{ borderColor: accent.border, boxShadow: selected ? `0 0 0 2px ${accent.border}` : undefined }}
    >
      <Handle type="target" position={Position.Left} className="palette-node__handle" />
      <div className="palette-node__badge" style={{ background: accent.badge }}>
        {kind.toUpperCase()}
      </div>
      <div className="palette-node__title">{data.label}</div>
      {data.description ? <div className="palette-node__desc">{data.description}</div> : null}
      <Handle type="source" position={Position.Right} className="palette-node__handle" />
    </div>
  );
}
