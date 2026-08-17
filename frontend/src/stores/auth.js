/**
 * Auth store: holds the access + refresh JWT pair and current user,
 * persisted to localStorage so a page refresh doesn't log the user
 * out. The refresh token (Phase 11) lets api.js silently obtain a new
 * access token when one expires, instead of forcing a re-login.
 */
import { defineStore } from "pinia";
import axios from "axios";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    token: localStorage.getItem("pas_token") || null,
    refreshToken: localStorage.getItem("pas_refresh_token") || null,
    user: JSON.parse(localStorage.getItem("pas_user") || "null"),
  }),

  getters: {
    isAuthenticated: (state) => !!state.token,
  },

  actions: {
    async login(email, password) {
      const form = new URLSearchParams();
      form.append("username", email);
      form.append("password", password);

      const { data } = await axios.post("/api/v1/auth/login", form, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });

      this.setTokens(data.access_token, data.refresh_token);
    },

    async register(email, password, fullName) {
      await axios.post("/api/v1/auth/register", {
        email,
        password,
        full_name: fullName,
      });
    },

    async refreshAccessToken() {
      if (!this.refreshToken) {
        throw new Error("No refresh token available.");
      }
      const { data } = await axios.post("/api/v1/auth/refresh", {
        refresh_token: this.refreshToken,
      });
      this.setTokens(data.access_token, data.refresh_token);
      return data.access_token;
    },

    setTokens(accessToken, refreshToken) {
      this.token = accessToken;
      this.refreshToken = refreshToken;
      localStorage.setItem("pas_token", accessToken);
      if (refreshToken) {
        localStorage.setItem("pas_refresh_token", refreshToken);
      }
    },

    logout() {
      this.token = null;
      this.refreshToken = null;
      this.user = null;
      localStorage.removeItem("pas_token");
      localStorage.removeItem("pas_refresh_token");
      localStorage.removeItem("pas_user");
    },
  },
});
