// src/services/auth.service.ts
import api from "@/lib/api";
import { clearTokens, getTokens, saveTokens } from "@/utils/storage";

let isRefreshing = false;
let failedQueue: any[] = [];

export async function refreshToken() {
  const { refreshToken } = getTokens();

  const res = await api.post("/auth/refresh/", {
    refresh_token: refreshToken,
  });

  saveTokens(res.data);
  return res.data.access_token;
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;

    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;

      try {
        const newToken = await refreshToken();
        original.headers.Authorization = `Bearer ${newToken}`;
        return api(original);
      } catch {
        clearTokens();
        window.location.href = "/login";
      }
    }

    return Promise.reject(error);
  }
);
