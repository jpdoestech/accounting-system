<template>
  <div class="row g-4">
    <div class="col-lg-6">
      <h4>Cash Receipts</h4>
      <div v-if="postError" class="alert alert-danger py-2 small">{{ postError }}</div>
      <table class="table table-sm table-hover bg-white">
        <thead>
          <tr>
            <th>No.</th>
            <th>Date</th>
            <th class="text-end">Amount</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in receipts" :key="r.id">
            <td>{{ r.receipt_number }}</td>
            <td class="text-muted small">{{ r.receipt_date }}</td>
            <td class="text-end">{{ r.amount }}</td>
            <td>
              <span :class="r.status === 'Posted' ? 'badge text-bg-success' : 'badge text-bg-secondary'">
                {{ r.status }}
              </span>
            </td>
            <td class="text-end">
              <button
                v-if="r.status === 'Draft'"
                class="btn btn-sm btn-outline-primary"
                :disabled="postingId === r.id"
                @click="onPost(r.id)"
              >
                <span v-if="postingId === r.id" class="spinner-border spinner-border-sm me-1"></span>
                Post
              </button>
            </td>
          </tr>
          <tr v-if="!receipts.length">
            <td colspan="5" class="text-muted text-center py-3">No receipts yet.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="col-lg-6">
      <h4>New Receipt</h4>
      <form @submit.prevent="onCreate" class="card p-3">
        <div class="row g-2 mb-2">
          <div class="col-6">
            <label class="form-label">Bank Account</label>
            <select v-model="form.bank_account_id" class="form-select" required>
              <option value="">— select —</option>
              <option v-for="b in bankAccounts" :key="b.id" :value="b.id">{{ b.name }}</option>
            </select>
          </div>
          <div class="col-6">
            <label class="form-label">Customer</label>
            <select v-model="form.customer_id" class="form-select" required>
              <option value="">— select —</option>
              <option v-for="c in customers" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </div>
          <div class="col-6">
            <label class="form-label">Receipt No.</label>
            <input v-model="form.receipt_number" class="form-control" required />
          </div>
          <div class="col-6">
            <label class="form-label">Date</label>
            <input v-model="form.receipt_date" type="date" class="form-control" required />
          </div>
          <div class="col-6">
            <label class="form-label">Amount</label>
            <input v-model="form.amount" type="number" step="0.01" class="form-control" required />
          </div>
          <div class="col-6">
            <label class="form-label">Apply to Invoice (optional)</label>
            <select v-model="form.invoice_id" class="form-select">
              <option value="">— unapplied —</option>
              <option v-for="inv in unpaidInvoices" :key="inv.id" :value="inv.id">
                {{ inv.invoice_number }} ({{ inv.grand_total }})
              </option>
            </select>
          </div>
        </div>

        <div v-if="error" class="alert alert-danger py-2 small">{{ error }}</div>
        <button type="submit" class="btn btn-primary" :disabled="submitting">
          <span v-if="submitting" class="spinner-border spinner-border-sm me-1"></span>
          Create Draft
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import api from "../services/api";
import { useBusinessStore } from "../stores/business";

const businessStore = useBusinessStore();
const receipts = ref([]);
const bankAccounts = ref([]);
const customers = ref([]);
const invoices = ref([]);
const error = ref("");
const submitting = ref(false);
const postError = ref("");
const postingId = ref(null);

const unpaidInvoices = computed(() => invoices.value.filter((i) => i.status === "Posted"));

const form = reactive({
  bank_account_id: "",
  customer_id: "",
  receipt_number: "",
  receipt_date: new Date().toISOString().slice(0, 10),
  amount: "",
  invoice_id: "",
});

async function loadAll() {
  const businessId = businessStore.activeBusinessId;
  if (!businessId) return;
  const [rRes, bRes, cRes, iRes] = await Promise.all([
    api.get(`/businesses/${businessId}/cash-receipts`),
    api.get(`/businesses/${businessId}/bank-accounts`),
    api.get(`/businesses/${businessId}/customers`),
    api.get(`/businesses/${businessId}/sales-invoices`),
  ]);
  receipts.value = rRes.data;
  bankAccounts.value = bRes.data;
  customers.value = cRes.data;
  invoices.value = iRes.data;
}

async function onCreate() {
  error.value = "";
  submitting.value = true;
  try {
    const allocations = form.invoice_id
      ? [{ document_id: form.invoice_id, amount_applied: form.amount }]
      : [];
    await api.post(`/businesses/${businessStore.activeBusinessId}/cash-receipts`, {
      bank_account_id: form.bank_account_id,
      customer_id: form.customer_id,
      receipt_number: form.receipt_number,
      receipt_date: form.receipt_date,
      amount: form.amount,
      allocations,
    });
    form.receipt_number = "";
    form.amount = "";
    form.invoice_id = "";
    await loadAll();
  } catch (err) {
    error.value = err.response?.data?.detail || "Could not create receipt.";
  } finally {
    submitting.value = false;
  }
}

async function onPost(receiptId) {
  postError.value = "";
  postingId.value = receiptId;
  try {
    await api.post(`/businesses/${businessStore.activeBusinessId}/cash-receipts/${receiptId}/post`);
    await loadAll();
  } catch (err) {
    postError.value = err.response?.data?.detail || "Could not post receipt.";
  } finally {
    postingId.value = null;
  }
}

onMounted(loadAll);
</script>
