/**
 * Axios instance with JWT auth header injection and centralized 401
 * handling. On a 401, tries exactly one silent refresh (Phase 11's
 * refresh token) before falling back to logging out and redirecting
 * to login -- so a merely-expired access token doesn't interrupt the
 * user's work, but a genuinely invalid session still sends them back
 * to sign in rather than looping forever.
 */
import axios from "axios";
import { useAuthStore } from "../stores/auth";
import router from "../router";

const api = axios.create({ baseURL: "/api/v1" });

api.interceptors.request.use((config) => {
  const auth = useAuthStore();
  if (auth.token) {
    config.headers.Authorization = `Bearer ${auth.token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retried) {
      originalRequest._retried = true;
      const auth = useAuthStore();

      try {
        const newAccessToken = await auth.refreshAccessToken();
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        return api(originalRequest);
      } catch {
        auth.logout();
        router.push({ name: "login" });
      }
    }

    return Promise.reject(error);
  }
);

export default api;
