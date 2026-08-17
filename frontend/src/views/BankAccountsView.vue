<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h4 class="mb-0">Bank Accounts</h4>
      <button class="btn btn-primary btn-sm" @click="showForm = !showForm">
        <i class="bi bi-plus-lg"></i> New Bank Account
      </button>
    </div>

    <form v-if="showForm" @submit.prevent="onCreate" class="card p-3 mb-4">
      <div class="row g-2">
        <div class="col-md-3">
          <label class="form-label">Name</label>
          <input v-model="form.name" class="form-control" placeholder="BDO Checking" required />
        </div>
        <div class="col-md-3">
          <label class="form-label">GL Account</label>
          <select v-model="form.gl_account_id" class="form-select" required>
            <option value="">— account —</option>
            <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.code }} — {{ a.name }}</option>
          </select>
        </div>
        <div class="col-md-2">
          <label class="form-label">Bank Name</label>
          <input v-model="form.bank_name" class="form-control" />
        </div>
        <div class="col-md-2">
          <label class="form-label">Opening Balance</label>
          <input v-model="form.opening_balance" type="number" step="0.01" class="form-control" />
        </div>
        <div class="col-md-2">
          <label class="form-label">As of</label>
          <input v-model="form.opening_balance_date" type="date" class="form-control" />
        </div>
      </div>
      <div v-if="error" class="alert alert-danger py-2 small mt-2 mb-0">{{ error }}</div>
      <button type="submit" class="btn btn-success mt-2" :disabled="submitting">Add Bank Account</button>
    </form>

    <table class="table table-sm table-hover bg-white">
      <thead>
        <tr>
          <th>Name</th>
          <th>Bank</th>
          <th class="text-end">Opening Balance</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="b in bankAccounts" :key="b.id">
          <td>{{ b.name }}</td>
          <td class="text-muted">{{ b.bank_name || "—" }}</td>
          <td class="text-end">{{ b.opening_balance }}</td>
        </tr>
        <tr v-if="!bankAccounts.length">
          <td colspan="3" class="text-muted text-center py-3">No bank accounts yet.</td>
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
const bankAccounts = ref([]);
const accounts = ref([]);
const showForm = ref(false);
const submitting = ref(false);
const error = ref("");

const form = reactive({
  name: "",
  gl_account_id: "",
  bank_name: "",
  opening_balance: "0.00",
  opening_balance_date: new Date().toISOString().slice(0, 10),
});

async function loadAll() {
  const businessId = businessStore.activeBusinessId;
  if (!businessId) return;
  const [bankRes, acctRes] = await Promise.all([
    api.get(`/businesses/${businessId}/bank-accounts`),
    api.get(`/businesses/${businessId}/accounts`),
  ]);
  bankAccounts.value = bankRes.data;
  accounts.value = acctRes.data;
}

async function onCreate() {
  error.value = "";
  submitting.value = true;
  try {
    await api.post(`/businesses/${businessStore.activeBusinessId}/bank-accounts`, form);
    form.name = "";
    form.bank_name = "";
    form.opening_balance = "0.00";
    showForm.value = false;
    await loadAll();
  } catch (err) {
    error.value = err.response?.data?.detail || "Could not create bank account.";
  } finally {
    submitting.value = false;
  }
}

onMounted(loadAll);
watch(() => businessStore.activeBusinessId, loadAll);
</script>
