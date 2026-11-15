export class ApiError extends Error {
  readonly status: number;
  /** A stable machine-readable reason: "meal_not_found", "wrong_password", "expired". */
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

type Body = { json: unknown } | { form: Record<string, string> } | undefined;

async function request<T>(method: string, path: string, body?: Body): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  let payload: BodyInit | undefined;
  if (body && "json" in body) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body.json);
  } else if (body) {
    payload = new URLSearchParams(body.form);
  }

  const response = await fetch(path, { method, credentials: "same-origin", cache: "no-store", headers, body: payload });
  const data: unknown = await response.json().catch(() => null);

  // Pages answer a lost session with a redirect to the sign-in form, the API with 401.
  if (response.status === 401 || (response.redirected && new URL(response.url).pathname.startsWith("/auth/login"))) {
    toLogin();
    throw new ApiError("Authentication required", 401, "authentication_required");
  }
  if (!response.ok) {
    const info = (data ?? {}) as { message?: string; error?: string; code?: string; status?: string };
    const code = info.code ?? (info.status && info.status !== "error" ? info.status : (info.message ?? info.error));
    throw new ApiError(info.message ?? info.error ?? `HTTP ${response.status}`, response.status, code);
  }
  return data as T;
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body: unknown = {}) => request<T>("POST", path, { json: body }),
  put: <T>(path: string, body: unknown = {}) => request<T>("PUT", path, { json: body }),
  patch: <T>(path: string, body: unknown = {}) => request<T>("PATCH", path, { json: body }),
  del: <T>(path: string) => request<T>("DELETE", path),
  /** For the account routes that read form fields. */
  postForm: <T>(path: string, fields: Record<string, string>) => request<T>("POST", path, { form: fields }),
};

/** The reason an action failed, when the server gave one. */
export const errorCode = (error: unknown): string | undefined => (error instanceof ApiError ? error.code : undefined);
