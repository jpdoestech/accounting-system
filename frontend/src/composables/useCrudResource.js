/**
 * useCrudResource
 *
 * Shared list/create/update/delete logic for the "master data" screens
 * (customers, vendors, and similar business-scoped resources that hang
 * off /businesses/{id}/<resource>). A view using this only needs to
 * supply the API path and, optionally, how to turn a row into a
 * display label for the delete confirmation.
 *
 * Every call is scoped to businessStore.activeBusinessId and the list
 * automatically reloads when the active business changes.
 */
import { ref, watch, onMounted } from "vue";
import api from "../services/api";
import { useBusinessStore } from "../stores/business";

export function useCrudResource(resourcePath) {
  const businessStore = useBusinessStore();

  const items = ref([]);
  const loading = ref(false);
  const error = ref("");

  function basePath() {
    return `/businesses/${businessStore.activeBusinessId}${resourcePath}`;
  }

  async function load() {
    if (!businessStore.activeBusinessId) {
      items.value = [];
      return;
    }
    loading.value = true;
    error.value = "";
    try {
      const { data } = await api.get(basePath());
      items.value = data;
    } catch (err) {
      error.value = err.response?.data?.detail || "Could not load data.";
    } finally {
      loading.value = false;
    }
  }

  async function create(payload) {
    const { data } = await api.post(basePath(), payload);
    await load();
    return data;
  }

  async function update(id, payload) {
    const { data } = await api.put(`${basePath()}/${id}`, payload);
    await load();
    return data;
  }

  async function remove(id) {
    await api.delete(`${basePath()}/${id}`);
    await load();
  }

  onMounted(load);
  watch(() => businessStore.activeBusinessId, load);

  return { items, loading, error, load, create, update, remove };
}
