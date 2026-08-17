<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h4 class="mb-0">Fixed Assets</h4>
      <button class="btn btn-primary btn-sm" @click="showForm = !showForm">
        <i class="bi bi-plus-lg"></i> New Asset
      </button>
    </div>

    <form v-if="showForm" @submit.prevent="onCreate" class="card p-3 mb-4">
      <div class="row g-2">
        <div class="col-md-2">
          <label class="form-label">Asset Code</label>
          <input v-model="form.asset_code" class="form-control" required />
        </div>
        <div class="col-md-3">
          <label class="form-label">Name</label>
          <input v-model="form.name" class="form-control" required />
        </div>
        <div class="col-md-2">
          <label class="form-label">Acquisition Date</label>
          <input v-model="form.acquisition_date" type="date" class="form-control" required />
        </div>
        <div class="col-md-2">
          <label class="form-label">Cost</label>
          <input v-model="form.acquisition_cost" type="number" step="0.01" class="form-control" required />
        </div>
        <div class="col-md-1">
          <label class="form-label">Salvage</label>
          <input v-model="form.salvage_value" type="number" step="0.01" class="form-control" />
        </div>
        <div class="col-md-2">
          <label class="form-label">Life (months)</label>
          <input v-model.number="form.useful_life_months" type="number" class="form-control" required />
        </div>

        <div class="col-md-4">
          <label class="form-label">Asset Account</label>
          <select v-model="form.asset_account_id" class="form-select" required>
            <option value="">— account —</option>
            <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.code }} — {{ a.name }}</option>
          </select>
        </div>
        <div class="col-md-4">
          <label class="form-label">Accum. Depreciation Account</label>
          <select v-model="form.accumulated_depreciation_account_id" class="form-select" required>
            <option value="">— account —</option>
            <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.code }} — {{ a.name }}</option>
          </select>
        </div>
        <div class="col-md-4">
          <label class="form-label">Depreciation Expense Account</label>
          <select v-model="form.depreciation_expense_account_id" class="form-select" required>
            <option value="">— account —</option>
            <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.code }} — {{ a.name }}</option>
          </select>
        </div>
      </div>
      <div v-if="error" class="alert alert-danger py-2 small mt-2 mb-0">{{ error }}</div>
      <button type="submit" class="btn btn-success mt-2" :disabled="submitting">Add Asset</button>
    </form>

    <table class="table table-sm table-hover bg-white">
      <thead>
        <tr>
          <th>Code</th>
          <th>Name</th>
          <th class="text-end">Cost</th>
          <th class="text-end">Accum. Dep.</th>
          <th class="text-end">Book Value</th>
          <th>Status</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="a in assets" :key="a.id">
          <td class="text-muted">{{ a.asset_code }}</td>
          <td>{{ a.name }}</td>
          <td class="text-end">{{ a.acquisition_cost }}</td>
          <td class="text-end">{{ a.accumulated_depreciation }}</td>
          <td class="text-end">{{ (Number(a.acquisition_cost) - Number(a.accumulated_depreciation)).toFixed(2) }}</td>
          <td>
            <span :class="a.status === 'Active' ? 'badge text-bg-success' : 'badge text-bg-secondary'">
              {{ a.status }}
            </span>
          </td>
          <td class="text-end">
            <button class="btn btn-sm btn-outline-primary" @click="onDepreciate(a)" :disabled="a.status !== 'Active'">
              Post Depreciation
            </button>
          </td>
        </tr>
        <tr v-if="!assets.length">
          <td colspan="7" class="text-muted text-center py-3">No fixed assets yet.</td>
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
const assets = ref([]);
const accounts = ref([]);
const showForm = ref(false);
const submitting = ref(false);
const error = ref("");

const form = reactive({
  asset_code: "",
  name: "",
  acquisition_date: new Date().toISOString().slice(0, 10),
  acquisition_cost: "",
  salvage_value: "0.00",
  useful_life_months: 36,
  asset_account_id: "",
  accumulated_depreciation_account_id: "",
  depreciation_expense_account_id: "",
});

async function loadAll() {
  const businessId = businessStore.activeBusinessId;
  if (!businessId) return;
  const [assetsRes, acctRes] = await Promise.all([
    api.get(`/businesses/${businessId}/fixed-assets`),
    api.get(`/businesses/${businessId}/accounts`),
  ]);
  assets.value = assetsRes.data;
  accounts.value = acctRes.data;
}

async function onCreate() {
  error.value = "";
  submitting.value = true;
  try {
    await api.post(`/businesses/${businessStore.activeBusinessId}/fixed-assets`, form);
    form.asset_code = "";
    form.name = "";
    form.acquisition_cost = "";
    showForm.value = false;
    await loadAll();
  } catch (err) {
    error.value = err.response?.data?.detail || "Could not create asset.";
  } finally {
    submitting.value = false;
  }
}

async function onDepreciate(asset) {
  const today = new Date();
  try {
    await api.post(`/businesses/${businessStore.activeBusinessId}/fixed-assets/${asset.id}/depreciate`, {
      period_year: today.getFullYear(),
      period_month: today.getMonth() + 1,
      entry_date: today.toISOString().slice(0, 10),
    });
    await loadAll();
  } catch (err) {
    error.value = err.response?.data?.detail || "Could not post depreciation.";
  }
}

onMounted(loadAll);
watch(() => businessStore.activeBusinessId, loadAll);
</script>
