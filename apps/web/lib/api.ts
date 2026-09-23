export type ApiFieldError = {
  field: string;
  message: string;
};

type ErrorPayload = {
  error?: {
    code?: unknown;
    message?: unknown;
    fields?: unknown;
  };
};

export class ApiClientError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly status?: number,
    public readonly fields?: ApiFieldError[],
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

function parseFields(value: unknown): ApiFieldError[] | undefined {
  if (!Array.isArray(value)) {
    return undefined;
  }

  const fields = value.filter(
    (field): field is ApiFieldError =>
      typeof field === "object" &&
      field !== null &&
      typeof (field as ApiFieldError).field === "string" &&
      typeof (field as ApiFieldError).message === "string",
  );
  return fields.length > 0 ? fields : undefined;
}

function parseApiError(payload: ErrorPayload, status: number): ApiClientError {
  const error = payload.error;
  if (!error || typeof error.code !== "string" || typeof error.message !== "string") {
    return new ApiClientError("We received an unexpected response. Please try again.", "INVALID_RESPONSE", status);
  }

  return new ApiClientError(error.message, error.code, status, parseFields(error.fields));
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, { ...init, credentials: "same-origin" });
  } catch {
    throw new ApiClientError("We could not reach SourcePilot. Please try again.", "NETWORK_ERROR");
  }

  if (response.status === 204) {
    return undefined as T;
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new ApiClientError("We received an unexpected response. Please try again.", "INVALID_RESPONSE", response.status);
  }

  if (!response.ok) {
    throw parseApiError(payload as ErrorPayload, response.status);
  }

  return payload as T;
}
