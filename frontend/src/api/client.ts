import { ApiError, formatApiDetail } from "./errors";

const apiBase = () => (import.meta.env.VITE_API_URL?.replace(/\/$/, "") ?? "");

export type ApiRequestOptions = RequestInit & {
  /** When omitted, caller should pass token from auth (see requestJson). */
  token?: string | null;
  skipAuth?: boolean;
};

export async function requestJson<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const { token, skipAuth, headers: initHeaders, ...rest } = options;
  const headers = new Headers(initHeaders);
  if (!headers.has("Content-Type") && rest.body != null) {
    headers.set("Content-Type", "application/json");
  }
  if (!skipAuth && token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const url = `${apiBase()}${path.startsWith("/") ? path : `/${path}`}`;
  const res = await fetch(url, { ...rest, headers });

  if (!res.ok) {
    let detail: unknown;
    try {
      detail = (await res.json()) as { detail?: unknown };
    } catch {
      detail = res.statusText;
    }
    const message =
      detail && typeof detail === "object" && detail !== null && "detail" in detail
        ? formatApiDetail((detail as { detail: unknown }).detail)
        : formatApiDetail(detail);
    throw new ApiError(res.status, message || res.statusText);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json() as Promise<T>;
}

/** Health and other routes that do not require a Bearer token. */
export async function requestJsonPublic<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  return requestJson<T>(path, { ...init, skipAuth: true });
}
