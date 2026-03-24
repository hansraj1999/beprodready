export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function formatValidationItem(item: unknown): string {
  if (typeof item === "string") return item;
  if (item && typeof item === "object" && "msg" in item) {
    return String((item as { msg: unknown }).msg);
  }
  try {
    return JSON.stringify(item);
  } catch {
    return String(item);
  }
}

/** Normalize FastAPI `detail` (string, object, or validation array). */
export function formatApiDetail(detail: unknown): string {
  if (detail == null) return "Request failed";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const parts = detail.map(formatValidationItem).filter(Boolean);
    return parts.length ? parts.join("; ") : "Request failed";
  }
  if (typeof detail === "object" && detail !== null) {
    const d = detail as Record<string, unknown>;
    if (typeof d.message === "string") return d.message;
  }
  try {
    return JSON.stringify(detail);
  } catch {
    return "Request failed";
  }
}
