import axios, { AxiosError } from "axios";

import type { ApiError } from "@/lib/types/document";

const baseURL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export const apiClient = axios.create({
  baseURL,
  timeout: 120000,
  headers: {
    Accept: "application/json",
  },
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiError>) => {
    const message =
      error.response?.data?.error?.message ??
      error.message ??
      "An unexpected error occurred";
    return Promise.reject(new Error(message));
  }
);
