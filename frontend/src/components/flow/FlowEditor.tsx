import { useCallback, useEffect, type Dispatch, type SetStateAction } from "react";
import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  addEdge,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Edge,
  type Node,
  type OnConnect,
  type OnEdgesChange,
  type OnNodesChange,
  type OnNodesDelete,
  type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import type { ArchitectNodeData, NodeKind } from "../../types/graph";
import { defaultLabelForKind } from "../../types/graph";
import { PaletteNode } from "./PaletteNode";

const nodeTypes: NodeTypes = {
  api: PaletteNode,
  db: PaletteNode,
  cache: PaletteNode,
  queue: PaletteNode,
};

function newNodeId(): string {
  return crypto.randomUUID();
}

export type FlowDocumentState = {
  nodes: Node<ArchitectNodeData>[];
  edges: Edge[];
  setNodes: Dispatch<SetStateAction<Node<ArchitectNodeData>[]>>;
  setEdges: Dispatch<SetStateAction<Edge[]>>;
  onNodesChange: OnNodesChange<Node<ArchitectNodeData>>;
  onEdgesChange: OnEdgesChange;
};

export function useFlowDocument(): FlowDocumentState {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<ArchitectNodeData>>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  return { nodes, edges, setNodes, setEdges, onNodesChange, onEdgesChange };
}

type InnerProps = {
  flow: FlowDocumentState;
  onSelectionChange: (nodeId: string | null) => void;
  /** Increment after loading a graph so the view fits new nodes. */
  fitViewNonce?: number;
};

function FlowCanvas({ flow, onSelectionChange, fitViewNonce = 0 }: InnerProps) {
  const { screenToFlowPosition, fitView } = useReactFlow();
  const { nodes, edges, onNodesChange, onEdgesChange, setNodes, setEdges } = flow;

  const onConnect: OnConnect = useCallback(
    (params) => setEdges((eds) => addEdge({ ...params, animated: true }, eds)),
    [setEdges],
  );

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const raw = e.dataTransfer.getData("application/archai-kind");
      if (!raw) return;
      const kind = raw as NodeKind;
      const position = screenToFlowPosition({ x: e.clientX, y: e.clientY });
      const node: Node<ArchitectNodeData> = {
        id: newNodeId(),
        type: kind,
        position,
        data: {
          kind,
          label: defaultLabelForKind(kind),
          description: "",
        },
      };
      setNodes((nds) => [...nds, node]);
    },
    [screenToFlowPosition, setNodes],
  );

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node<ArchitectNodeData>) => {
      onSelectionChange(node.id);
    },
    [onSelectionChange],
  );

  const onPaneClick = useCallback(() => {
    onSelectionChange(null);
  }, [onSelectionChange]);

  const onNodesDelete: OnNodesDelete<Node<ArchitectNodeData>> = useCallback(
    (deleted) => {
      const ids = new Set(deleted.map((n) => n.id));
      setEdges((eds) => eds.filter((edge) => !ids.has(edge.source) && !ids.has(edge.target)));
      onSelectionChange(null);
    },
    [setEdges, onSelectionChange],
  );

  useEffect(() => {
    if (!fitViewNonce) return;
    const id = requestAnimationFrame(() => {
      fitView({ padding: 0.15, duration: 250 });
    });
    return () => cancelAnimationFrame(id);
  }, [fitViewNonce, fitView]);

  return (
    <div className="flow-editor" onDrop={onDrop} onDragOver={onDragOver}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        onNodesDelete={onNodesDelete}
        nodeTypes={nodeTypes}
        fitView
        snapToGrid
        snapGrid={[16, 16]}
        deleteKeyCode={["Backspace", "Delete"]}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="var(--flow-dot)" />
        <Controls className="flow-controls" />
        <MiniMap
          className="flow-minimap"
          maskColor="rgba(0,0,0,0.12)"
          nodeStrokeWidth={2}
        />
      </ReactFlow>
    </div>
  );
}

export function FlowEditorShell({
  flow,
  onSelectionChange,
  fitViewNonce,
}: {
  flow: FlowDocumentState;
  onSelectionChange: (nodeId: string | null) => void;
  fitViewNonce?: number;
}) {
  return (
    <ReactFlowProvider>
      <FlowCanvas flow={flow} onSelectionChange={onSelectionChange} fitViewNonce={fitViewNonce} />
    </ReactFlowProvider>
  );
}
