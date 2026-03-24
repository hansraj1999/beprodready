import type { ReactNode } from "react";

type Props = {
  onExportFile: () => void;
  onCopyJson: () => void;
  apiStatus: string;
  notice?: string | null;
  authSlot?: ReactNode;
};

export function Toolbar({ onExportFile, onCopyJson, apiStatus, notice, authSlot }: Props) {
  return (
    <header className="toolbar">
      <div className="toolbar__brand">
        <span className="toolbar__logo">Archai</span>
        <span className="toolbar__muted">system canvas</span>
      </div>
      {authSlot ? <div className="toolbar__auth">{authSlot}</div> : null}
      <div className="toolbar__actions">
        <span className="toolbar__status" data-testid="api-status">
          {notice ?? apiStatus}
        </span>
        <button type="button" className="toolbar__btn" onClick={onCopyJson}>
          Copy JSON
        </button>
        <button type="button" className="toolbar__btn toolbar__btn--primary" onClick={onExportFile}>
          Export graph.json
        </button>
      </div>
    </header>
  );
}
