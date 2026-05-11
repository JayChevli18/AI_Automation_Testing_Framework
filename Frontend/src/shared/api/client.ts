import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

import { attachStatus, parseApiErrorPayload, type ParsedApiError } from "./error-envelope";

declare module "axios" {
  export interface AxiosRequestConfig {
    /** When false, do not attach a generated `x-request-id` (e.g. multipart to third parties). */
    attachRequestId?: boolean;
  }
}

const apiBaseURL =
  typeof window === "undefined"
    ? (process.env.API_BACKEND_ORIGIN ?? "http://127.0.0.1:8000")
    : "";

export const apiClient = axios.create({
  baseURL: apiBaseURL,
  timeout: 600_000,
  headers: { "Content-Type": "application/json" },
});

function newRequestId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (config.attachRequestId === false) return config;
  const headers = config.headers ?? {};
  if (!headers["x-request-id"] && !headers["X-Request-Id"]) {
    headers["x-request-id"] = newRequestId();
  }
  config.headers = headers;
  return config;
});

apiClient.interceptors.response.use(
  (res) => res,
  (error: AxiosError<unknown>) => {
    const status = error.response?.status ?? 0;
    const parsed = parseApiErrorPayload(error.response?.data);
    if (parsed) {
      (error as AxiosError & { apiError?: ParsedApiError }).apiError = attachStatus(
        parsed,
        status,
      );
    }
    return Promise.reject(error);
  },
);

export function getApiError(error: unknown): ParsedApiError | null {
  const direct = (error as { apiError?: ParsedApiError } | null)?.apiError;
  if (direct) return direct;
  if (!axios.isAxiosError(error)) return null;
  const extended = error as AxiosError & { apiError?: ParsedApiError };
  if (extended.apiError) return extended.apiError;
  const parsed = parseApiErrorPayload(error.response?.data);
  if (!parsed) return null;
  return attachStatus(parsed, error.response?.status ?? 0);
}
