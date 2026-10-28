export class ApiError extends Error {
  readonly status: number;
  readonly code: string | undefined;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

let leaving = false;

/** A lost session sends the visitor to the sign-in page, then back here. */
function toLogin(): void {
  if (leaving) return;
  leaving = true;
  const next = encodeURIComponent(window.location.pathname + window.location.search);
  window.location.assign(`/auth/login?next=${next}`);
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method,
    credentials: "same-origin",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data: unknown = await response.json().catch(() => null);

  if (response.status === 401) {
    toLogin();
    throw new ApiError("Authentication required", 401, "authentication_required");
  }
  if (!response.ok) {
    const info = (data ?? {}) as { message?: string; error?: string; code?: string };
    throw new ApiError(info.message ?? info.error ?? `HTTP ${response.status}`, response.status, info.code);
  }
  return data as T;
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body: unknown = {}) => request<T>("POST", path, body),
  patch: <T>(path: string, body: unknown = {}) => request<T>("PATCH", path, body),
  del: <T>(path: string) => request<T>("DELETE", path),
};
