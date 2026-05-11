import { attachStatus, parseApiErrorPayload, type ParsedApiError } from "@/shared/api/error-envelope";
import { API_TESTS } from "@/shared/constants/api-paths";

export type UploadResult = {
  success: boolean;
  file_id: string;
  filename: string;
  stored_path: string;
};

function newRequestId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export async function uploadTestFile(file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  const path = `${API_TESTS}/upload`;
  const res = await fetch(path, {
    method: "POST",
    body: form,
    headers: { "x-request-id": newRequestId() },
  });
  const data: unknown = await res.json().catch(() => ({}));
  if (!res.ok) {
    const parsed = parseApiErrorPayload(data);
    const err = new Error(parsed?.message ?? res.statusText) as Error & { apiError?: ParsedApiError };
    if (parsed) err.apiError = attachStatus(parsed, res.status);
    throw err;
  }
  const body = data as UploadResult;
  if (!body.success || !body.file_id) {
    throw new Error("Upload failed");
  }
  return body;
}
