/**
 * Business store: list of businesses the user has access to, and
 * which one is currently active. Section 12 (multi-business) --
 * every business-scoped API call in the app reads activeBusinessId
 * from here rather than re-deriving it per view.
 */
import { defineStore } from "pinia";
import api from "../services/api";

export const useBusinessStore = defineStore("business", {
  state: () => ({
    businesses: [],
    activeBusinessId: localStorage.getItem("pas_active_business") || null,
    loading: false,
  }),

  getters: {
    activeBusiness: (state) =>
      state.businesses.find((b) => b.id === state.activeBusinessId) || null,
  },

  actions: {
    async fetchBusinesses() {
      this.loading = true;
      try {
        const { data } = await api.get("/businesses");
        this.businesses = data;
        if (!this.activeBusinessId && data.length > 0) {
          this.setActiveBusiness(data[0].id);
        }
      } finally {
        this.loading = false;
      }
    },

    async createBusiness(payload) {
      const { data } = await api.post("/businesses", payload);
      this.businesses.push(data);
      this.setActiveBusiness(data.id);
      return data;
    },

    setActiveBusiness(businessId) {
      this.activeBusinessId = businessId;
      localStorage.setItem("pas_active_business", businessId);
    },
  },
});
