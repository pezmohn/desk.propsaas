export type ApiErrorKind = "unauthorized" | "forbidden" | "notFound" | "serverError";

export class ApiError extends Error {
  kind: ApiErrorKind;
  status: number;

  constructor(kind: ApiErrorKind, status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
  }
}

type RequestJsonOptions = {
  method?: string;
  body?: unknown;
  notFoundAsNull?: boolean;
  unauthorizedAsNull?: boolean;
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "";

export async function requestJson(
  path: string,
  options: RequestJsonOptions = {},
): Promise<unknown | null> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: options.method || "GET",
    credentials: "include",
    headers: options.body ? { "Content-Type": "application/json" } : undefined,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  if (response.status === 401) {
    if (options.unauthorizedAsNull) {
      return null;
    }
    throw new ApiError("unauthorized", response.status, "Please sign in again.");
  }

  if (response.status === 403) {
    throw new ApiError("forbidden", response.status, "You do not have access to this view.");
  }

  if (response.status === 404) {
    if (options.notFoundAsNull) {
      return null;
    }
    throw new ApiError("notFound", response.status, "The requested record was not found.");
  }

  if (!response.ok) {
    const message = await readErrorMessage(response);
    throw new ApiError(
      "serverError",
      response.status,
      message || `Request failed with ${response.status}.`,
    );
  }

  if (response.status === 204) {
    return undefined;
  }

  return response.json();
}

export function apiErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    return error.message;
  }

  return error instanceof Error ? error.message : fallback;
}

async function readErrorMessage(response: Response): Promise<string> {
  const text = await response.text();
  if (!text) {
    return "";
  }

  try {
    const payload = JSON.parse(text) as { detail?: unknown };
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
    if (Array.isArray(payload.detail)) {
      const first = payload.detail[0] as { msg?: unknown } | undefined;
      if (typeof first?.msg === "string") {
        return first.msg;
      }
    }
  } catch {
    return text;
  }

  return text;
}
