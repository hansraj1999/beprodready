import { PALETTE_ITEMS } from "../../types/graph";

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar__head">
        <h2 className="sidebar__title">Components</h2>
        <p className="sidebar__hint">Drag onto the canvas</p>
      </div>
      <ul className="sidebar__list">
        {PALETTE_ITEMS.map((item) => (
          <li key={item.kind}>
            <div
              className={`sidebar__chip sidebar__chip--${item.kind}`}
              draggable
              onDragStart={(e) => {
                e.dataTransfer.setData("application/archai-kind", item.kind);
                e.dataTransfer.effectAllowed = "move";
              }}
            >
              <span className="sidebar__chip-label">{item.label}</span>
              <span className="sidebar__chip-hint">{item.hint}</span>
            </div>
          </li>
        ))}
      </ul>
    </aside>
  );
}
