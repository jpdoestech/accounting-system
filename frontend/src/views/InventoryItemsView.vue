<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h4 class="mb-0">Inventory Items</h4>
      <button class="btn btn-primary btn-sm" @click="showForm = !showForm">
        <i class="bi bi-plus-lg"></i> New Item
      </button>
    </div>

    <form v-if="showForm" @submit.prevent="onCreate" class="card p-3 mb-4">
      <div class="row g-2">
        <div class="col-md-2">
          <label class="form-label">SKU</label>
          <input v-model="form.sku" class="form-control" required />
        </div>
        <div class="col-md-3">
          <label class="form-label">Name</label>
          <input v-model="form.name" class="form-control" required />
        </div>
        <div class="col-md-2">
          <label class="form-label">Unit</label>
          <input v-model="form.unit_of_measure" class="form-control" placeholder="pcs" />
        </div>
        <div class="col-md-3">
          <label class="form-label">Inventory Account</label>
          <select v-model="form.inventory_account_id" class="form-select" required>
            <option value="">— account —</option>
            <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.code }} — {{ a.name }}</option>
          </select>
        </div>
        <div class="col-md-2">
          <label class="form-label">COGS Account</label>
          <select v-model="form.cogs_account_id" class="form-select" required>
            <option value="">— account —</option>
            <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.code }} — {{ a.name }}</option>
          </select>
        </div>
      </div>
      <div v-if="error" class="alert alert-danger py-2 small mt-2 mb-0">{{ error }}</div>
      <button type="submit" class="btn btn-success mt-2" :disabled="submitting">Add Item</button>
    </form>

    <table class="table table-sm table-hover bg-white">
      <thead>
        <tr>
          <th>SKU</th>
          <th>Name</th>
          <th class="text-end">Qty on Hand</th>
          <th class="text-end">Avg. Cost</th>
          <th class="text-end">Stock Value</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in items" :key="item.id">
          <td class="text-muted">{{ item.sku }}</td>
          <td>{{ item.name }}</td>
          <td class="text-end">{{ item.quantity_on_hand }}</td>
          <td class="text-end">{{ item.average_cost }}</td>
          <td class="text-end">{{ (Number(item.quantity_on_hand) * Number(item.average_cost)).toFixed(2) }}</td>
        </tr>
        <tr v-if="!items.length">
          <td colspan="5" class="text-muted text-center py-3">No inventory items yet.</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from "vue";
import api from "../services/api";
import { useBusinessStore } from "../stores/business";

const businessStore = useBusinessStore();
const items = ref([]);
const accounts = ref([]);
const showForm = ref(false);
const submitting = ref(false);
const error = ref("");

const form = reactive({
  sku: "",
  name: "",
  unit_of_measure: "",
  inventory_account_id: "",
  cogs_account_id: "",
});

async function loadAll() {
  const businessId = businessStore.activeBusinessId;
  if (!businessId) return;
  const [itemsRes, acctRes] = await Promise.all([
    api.get(`/businesses/${businessId}/inventory-items`),
    api.get(`/businesses/${businessId}/accounts`),
  ]);
  items.value = itemsRes.data;
  accounts.value = acctRes.data;
}

async function onCreate() {
  error.value = "";
  submitting.value = true;
  try {
    await api.post(`/businesses/${businessStore.activeBusinessId}/inventory-items`, form);
    form.sku = "";
    form.name = "";
    form.unit_of_measure = "";
    showForm.value = false;
    await loadAll();
  } catch (err) {
    error.value = err.response?.data?.detail || "Could not create item.";
  } finally {
    submitting.value = false;
  }
}

onMounted(loadAll);
watch(() => businessStore.activeBusinessId, loadAll);
</script>
