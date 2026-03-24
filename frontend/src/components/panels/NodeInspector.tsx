import type { Dispatch, SetStateAction } from "react";
import type { Node } from "@xyflow/react";
import type { ArchitectNodeData } from "../../types/graph";

type Props = {
  selectedId: string | null;
  nodes: Node<ArchitectNodeData>[];
  setNodes: Dispatch<SetStateAction<Node<ArchitectNodeData>[]>>;
};

export function NodeInspector({ selectedId, nodes, setNodes }: Props) {
  const node = selectedId ? nodes.find((n) => n.id === selectedId) : undefined;

  if (!node) {
    return (
      <aside className="inspector">
        <div className="inspector__head">
          <h2 className="inspector__title">Node</h2>
        </div>
        <p className="inspector__empty">Select a node to edit label and notes.</p>
      </aside>
    );
  }

  const patch = (partial: Partial<ArchitectNodeData>) => {
    setNodes((prev) =>
      prev.map((n) =>
        n.id === node.id
          ? { ...n, data: { ...n.data, ...partial } }
          : n,
      ),
    );
  };

  return (
    <aside className="inspector">
      <div className="inspector__head">
        <h2 className="inspector__title">Node</h2>
        <span className="inspector__kind">{node.data.kind.toUpperCase()}</span>
      </div>
      <div className="inspector__fields">
        <label className="inspector__label">
          Label
          <input
            className="inspector__input"
            value={node.data.label}
            onChange={(e) => patch({ label: e.target.value })}
            maxLength={120}
          />
        </label>
        <label className="inspector__label">
          Description
          <textarea
            className="inspector__textarea"
            value={node.data.description ?? ""}
            onChange={(e) => patch({ description: e.target.value })}
            rows={5}
            placeholder="Ports, SLAs, tech choices…"
          />
        </label>
      </div>
    </aside>
  );
}
