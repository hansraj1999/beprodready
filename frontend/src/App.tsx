import { useCallback, useEffect, useState } from "react";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { requestJsonPublic } from "./api/client";
import { FlowEditorShell, useFlowDocument } from "./components/flow/FlowEditor";
import { NodeInspector } from "./components/panels/NodeInspector";
import { ServerPanel, interviewStateFromStart } from "./components/panels/ServerPanel";
import type { InterviewState } from "./components/panels/ServerPanel";
import { RemoteGraphBar } from "./components/RemoteGraphBar";
import { Sidebar } from "./components/sidebar/Sidebar";
import { Toolbar } from "./components/Toolbar";
import { AuthBar } from "./components/AuthBar";
import "./App.css";
import { copyJsonToClipboard, downloadJson, toGraphExport } from "./utils/exportGraph";
import type { EvaluateResponse, InterviewStartResponse } from "./types/api";

function AppShell() {
  const flow = useFlowDocument();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [apiStatus, setApiStatus] = useState("checking…");
  const [copyHint, setCopyHint] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [graphName, setGraphName] = useState("Untitled architecture");
  const [graphId, setGraphId] = useState<string | null>(null);
  const [fitViewNonce, setFitViewNonce] = useState(0);
  const [evaluation, setEvaluation] = useState<EvaluateResponse | null>(null);
  const [interview, setInterview] = useState<InterviewState | null>(null);

  const { firebaseConfigured } = useAuth();

  useEffect(() => {
    requestJsonPublic<{ status?: string }>("/api/v1/health")
      .then((data) => setApiStatus(`API: ${data.status ?? "ok"}`))
      .catch(() => setApiStatus("API offline"));
  }, []);

  const buildExport = useCallback(() => toGraphExport(flow.nodes, flow.edges), [flow.nodes, flow.edges]);

  const onExportFile = useCallback(() => {
    downloadJson("graph.json", buildExport());
  }, [buildExport]);

  const onCopyJson = useCallback(async () => {
    try {
      await copyJsonToClipboard(buildExport());
      setCopyHint("Copied to clipboard");
      window.setTimeout(() => setCopyHint(null), 2000);
    } catch {
      setCopyHint("Copy failed");
      window.setTimeout(() => setCopyHint(null), 2500);
    }
  }, [buildExport]);

  const onGraphLoaded = useCallback(() => {
    setFitViewNonce((n) => n + 1);
  }, []);

  const onInterviewStarted = useCallback((r: InterviewStartResponse) => {
    setInterview(interviewStateFromStart(r));
    setApiError(null);
  }, []);

  return (
    <div className="shell">
      <Sidebar />
      <main className="main-panel">
        <Toolbar
          authSlot={<AuthBar />}
          apiStatus={apiStatus}
          notice={copyHint}
          onExportFile={onExportFile}
          onCopyJson={() => void onCopyJson()}
        />
        <RemoteGraphBar
          flow={flow}
          graphName={graphName}
          onGraphNameChange={setGraphName}
          graphId={graphId}
          onGraphIdChange={setGraphId}
          onGraphLoaded={onGraphLoaded}
          onApiError={setApiError}
          onEvaluation={setEvaluation}
          onInterviewStarted={onInterviewStarted}
          onInterviewClear={() => setInterview(null)}
        />
        {apiError ? (
          <div className="error-banner" role="alert">
            <span className="error-banner__text">{apiError}</span>
            <button type="button" className="error-banner__dismiss" onClick={() => setApiError(null)}>
              Dismiss
            </button>
          </div>
        ) : null}
        {!firebaseConfigured ? (
          <div className="config-hint">
            Protected API calls need Firebase. Add <code>VITE_FIREBASE_*</code> to <code>.env</code> and sign in.
          </div>
        ) : null}
        <div className="canvas-area">
          <FlowEditorShell
            flow={flow}
            onSelectionChange={setSelectedId}
            fitViewNonce={fitViewNonce}
          />
        </div>
      </main>
      <div className="right-stack">
        <NodeInspector selectedId={selectedId} nodes={flow.nodes} setNodes={flow.setNodes} />
        <ServerPanel
          evaluation={evaluation}
          interview={interview}
          onInterviewUpdate={setInterview}
          onInterviewReset={() => setInterview(null)}
          onApiError={setApiError}
        />
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppShell />
    </AuthProvider>
  );
}
