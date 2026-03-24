SYSTEM_GENERATE_GRAPH = """You output only valid JSON (no markdown fences). Design a system architecture as a graph.

Schema:
{
  "nodes": [ Node, ... ],
  "edges": [ Edge, ... ]
}

Node object (all required):
- "id": unique string, alphanumeric/underscore, no spaces
- "type": exactly one of: "api", "db", "cache", "queue"
- "label": short human-readable name (e.g. "API Gateway", "Trip Service")
- "position": { "x": number, "y": number } — spread on a canvas roughly 0–900 (x) and 0–520 (y), avoid stacking all at origin
- "data": { "kind": same string as type, "label": same as top-level label, "description": one sentence on responsibility }

Edge object:
- "id": unique string
- "source": id of source node
- "target": id of target node
- "label": optional short flow label (e.g. "HTTPS", "publish", "read")

Rules:
- 5–12 nodes typical; include sensible data paths (client → gateway → services → cache/queue/db as appropriate).
- Every edge must reference existing node ids.
- Prefer clear layering: external traffic → API → domain services → async (queue) → storage (db) with cache where it helps.
"""

USER_GENERATE_TEMPLATE = """System to design (be specific, use standard patterns):

{prompt}

Return the JSON object only."""
