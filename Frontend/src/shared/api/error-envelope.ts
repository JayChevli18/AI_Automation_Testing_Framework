/** Matches FastAPI `main._error_envelope` JSON shape on error responses. */

export type ApiErrorEnvelope = {
  success: false;
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
    request_id: string | null;
  };
};

export type ParsedApiError = {
  status: number;
  code: string;
  message: string;
  requestId: string | null;
  details: Record<string, unknown>;
};

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

export function parseApiErrorPayload(data: unknown): ParsedApiError | null {
  if (!isRecord(data)) return null;
  if (data.success !== false) return null;
  const err = data.error;
  if (!isRecord(err)) return null;
  const code = typeof err.code === "string" ? err.code : "UNKNOWN";
  const message = typeof err.message === "string" ? err.message : "Request failed";
  const request_id = err.request_id;
  const requestId =
    typeof request_id === "string" || request_id === null ? request_id : null;
  const details = isRecord(err.details) ? err.details : {};
  return {
    status: 0,
    code,
    message,
    requestId,
    details,
  };
}

export function attachStatus(parsed: ParsedApiError, status: number): ParsedApiError {
  return { ...parsed, status };
}
