import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../api/errors";
import { createGraph, getGraph, listGraphs, updateGraph } from "../api/graphs";
import { evaluateGraph } from "../api/evaluate";
import { startInterview } from "../api/interview";
import type { EvaluateResponse, GraphSummary, InterviewStartResponse } from "../types/api";
import type { FlowDocumentState } from "./flow/FlowEditor";
import { toGraphExport } from "../utils/exportGraph";
import { edgesFromApiPayload, nodesFromApiPayload } from "../utils/importGraph";

type Props = {
  flow: FlowDocumentState;
  graphName: string;
  onGraphNameChange: (name: string) => void;
  graphId: string | null;
  onGraphIdChange: (id: string | null) => void;
  onGraphLoaded: () => void;
  onApiError: (message: string | null) => void;
  onEvaluation: (r: EvaluateResponse | null) => void;
  onInterviewStarted: (r: InterviewStartResponse) => void;
  onInterviewClear: () => void;
};

export function RemoteGraphBar({
  flow,
  graphName,
  onGraphNameChange,
  graphId,
  onGraphIdChange,
  onGraphLoaded,
  onApiError,
  onEvaluation,
  onInterviewStarted,
  onInterviewClear,
}: Props) {
  const { getIdToken, user, firebaseConfigured } = useAuth();
  const [summaries, setSummaries] = useState<GraphSummary[]>([]);
  const [loadId, setLoadId] = useState("");
  const [busy, setBusy] = useState(false);

  const requireToken = useCallback(async () => {
    const token = await getIdToken();
    if (!token) {
      throw new Error("Sign in with Firebase to use the API");
    }
    return token;
  }, [getIdToken]);

  const refreshList = useCallback(async () => {
    if (!user || !firebaseConfigured) return;
    try {
      const token = await requireToken();
      const list = await listGraphs(token);
      setSummaries(list);
    } catch (e) {
      onApiError(
        e instanceof ApiError
          ? e.message
          : e instanceof Error
            ? e.message
            : "Failed to list graphs",
      );
    }
  }, [user, firebaseConfigured, requireToken, onApiError]);

  useEffect(() => {
    void refreshList();
  }, [refreshList]);

  const run = async (fn: () => Promise<void>) => {
    onApiError(null);
    setBusy(true);
    try {
      await fn();
    } catch (e) {
      const msg =
        e instanceof ApiError
          ? e.message
          : e instanceof Error
            ? e.message
            : "Request failed";
      onApiError(msg);
    } finally {
      setBusy(false);
    }
  };

  const onSave = () =>
    run(async () => {
      const token = await requireToken();
      const payload = { ...toGraphExport(flow.nodes, flow.edges), name: graphName.trim() || "Untitled" };
      if (graphId) {
        await updateGraph(token, graphId, {
          name: payload.name,
          nodes: payload.nodes,
          edges: payload.edges,
        });
      } else {
        const created = await createGraph(token, payload);
        onGraphIdChange(created.id);
        onGraphNameChange(created.name);
      }
      await refreshList();
    });

  const onLoadSelected = () =>
    run(async () => {
      const id = loadId.trim();
      if (!id) return;
      const token = await requireToken();
      const g = await getGraph(token, id);
      flow.setNodes(nodesFromApiPayload(g.nodes));
      flow.setEdges(edgesFromApiPayload(g.edges));
      onGraphIdChange(g.id);
      onGraphNameChange(g.name);
      onGraphLoaded();
    });

  const onNew = () => {
    onApiError(null);
    onGraphIdChange(null);
    onGraphNameChange("Untitled architecture");
    flow.setNodes([]);
    flow.setEdges([]);
    onEvaluation(null);
    onInterviewClear();
  };

  const onEvaluate = () =>
    run(async () => {
      const token = await requireToken();
      const r = await evaluateGraph(token, toGraphExport(flow.nodes, flow.edges));
      onEvaluation(r);
    });

  const onInterview = () =>
    run(async () => {
      const token = await requireToken();
      const r = await startInterview(token);
      onInterviewStarted(r);
    });

  const canRemote = Boolean(user && firebaseConfigured);

  return (
    <div className="remote-graph-bar">
      <input
        className="remote-graph-bar__name"
        type="text"
        value={graphName}
        onChange={(e) => onGraphNameChange(e.target.value)}
        placeholder="Graph name"
        maxLength={255}
        disabled={busy || !canRemote}
        aria-label="Graph name"
      />
      <button
        type="button"
        className="toolbar__btn toolbar__btn--primary"
        disabled={busy || !canRemote}
        onClick={() => void onSave()}
      >
        Save
      </button>
      <div className="remote-graph-bar__load">
        <select
          className="remote-graph-bar__select"
          value={loadId}
          onChange={(e) => setLoadId(e.target.value)}
          disabled={busy || !canRemote}
          aria-label="Saved graphs"
        >
          <option value="">Load…</option>
          {summaries.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="toolbar__btn"
          disabled={busy || !canRemote || !loadId}
          onClick={() => void onLoadSelected()}
        >
          Load
        </button>
        <button type="button" className="toolbar__btn" disabled={busy} onClick={onNew}>
          New
        </button>
      </div>
      <button
        type="button"
        className="toolbar__btn"
        disabled={busy || !canRemote}
        onClick={() => void onEvaluate()}
      >
        Evaluate
      </button>
      <button
        type="button"
        className="toolbar__btn"
        disabled={busy || !canRemote}
        onClick={() => void onInterview()}
      >
        Interview
      </button>
      {graphId ? (
        <span className="remote-graph-bar__id" title="Current graph id">
          id: {graphId.slice(0, 8)}…
        </span>
      ) : null}
    </div>
  );
}
