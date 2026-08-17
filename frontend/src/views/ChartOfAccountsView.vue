<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h4 class="mb-0">Chart of Accounts</h4>
      <button class="btn btn-primary btn-sm" @click="showForm = !showForm">
        <i class="bi bi-plus-lg"></i> New Account
      </button>
    </div>

    <form v-if="showForm" @submit.prevent="onCreate" class="card p-3 mb-4">
      <div class="row g-2">
        <div class="col-md-2">
          <label class="form-label">Code</label>
          <input v-model="form.code" class="form-control" required />
        </div>
        <div class="col-md-4">
          <label class="form-label">Name</label>
          <input v-model="form.name" class="form-control" required />
        </div>
        <div class="col-md-3">
          <label class="form-label">Type</label>
          <select v-model="form.account_type" class="form-select" required>
            <option value="">— Select —</option>
            <option v-for="t in accountTypes" :key="t">{{ t }}</option>
          </select>
        </div>
        <div class="col-md-3 d-flex align-items-end">
          <button type="submit" class="btn btn-success w-100" :disabled="submitting">
            Add Account
          </button>
        </div>
      </div>
      <div v-if="error" class="alert alert-danger py-2 small mt-2 mb-0">{{ error }}</div>
    </form>

    <table class="table table-sm table-hover bg-white">
      <thead>
        <tr>
          <th>Code</th>
          <th>Name</th>
          <th>Type</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="a in accounts" :key="a.id">
          <td class="text-muted">{{ a.code }}</td>
          <td>{{ a.name }}</td>
          <td><span class="badge text-bg-light">{{ a.account_type }}</span></td>
          <td class="text-end">
            <router-link
              :to="{ name: 'account-ledger', params: { businessId: businessStore.activeBusinessId, accountId: a.id } }"
              class="small"
            >
              View ledger
            </router-link>
          </td>
        </tr>
        <tr v-if="!accounts.length">
          <td colspan="4" class="text-muted text-center py-3">No accounts yet.</td>
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
const accounts = ref([]);
const showForm = ref(false);
const submitting = ref(false);
const error = ref("");

const accountTypes = [
  "Asset",
  "Liability",
  "Equity",
  "Revenue",
  "Cost of Sales",
  "Expense",
  "Other Income",
  "Other Expense",
];

const form = reactive({ code: "", name: "", account_type: "" });

async function loadAccounts() {
  if (!businessStore.activeBusinessId) return;
  const { data } = await api.get(`/businesses/${businessStore.activeBusinessId}/accounts`);
  accounts.value = data;
}

async function onCreate() {
  error.value = "";
  submitting.value = true;
  try {
    await api.post(`/businesses/${businessStore.activeBusinessId}/accounts`, form);
    form.code = "";
    form.name = "";
    form.account_type = "";
    showForm.value = false;
    await loadAccounts();
  } catch (err) {
    error.value = err.response?.data?.detail || "Could not create account.";
  } finally {
    submitting.value = false;
  }
}

onMounted(loadAccounts);
watch(() => businessStore.activeBusinessId, loadAccounts);
</script>
