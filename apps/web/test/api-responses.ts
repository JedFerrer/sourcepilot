export function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

export function emptyResponse(status = 204): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => undefined,
  } as Response;
}
