<template>
  <div class="row g-4">
    <div class="col-lg-6">
      <h4>Cash Disbursements</h4>
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
          <tr v-for="d in disbursements" :key="d.id">
            <td>{{ d.payment_number }}</td>
            <td class="text-muted small">{{ d.payment_date }}</td>
            <td class="text-end">{{ d.amount }}</td>
            <td>
              <span :class="d.status === 'Posted' ? 'badge text-bg-success' : 'badge text-bg-secondary'">
                {{ d.status }}
              </span>
            </td>
            <td class="text-end">
              <button v-if="d.status === 'Draft'" class="btn btn-sm btn-outline-primary" @click="onPost(d.id)">
                Post
              </button>
            </td>
          </tr>
          <tr v-if="!disbursements.length">
            <td colspan="5" class="text-muted text-center py-3">No payments yet.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="col-lg-6">
      <h4>New Payment</h4>
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
            <label class="form-label">Vendor</label>
            <select v-model="form.vendor_id" class="form-select" required>
              <option value="">— select —</option>
              <option v-for="v in vendors" :key="v.id" :value="v.id">{{ v.name }}</option>
            </select>
          </div>
          <div class="col-6">
            <label class="form-label">Payment No. / Check No.</label>
            <input v-model="form.payment_number" class="form-control" required />
          </div>
          <div class="col-6">
            <label class="form-label">Date</label>
            <input v-model="form.payment_date" type="date" class="form-control" required />
          </div>
          <div class="col-6">
            <label class="form-label">Amount</label>
            <input v-model="form.amount" type="number" step="0.01" class="form-control" required />
          </div>
          <div class="col-6">
            <label class="form-label">Apply to Bill (optional)</label>
            <select v-model="form.bill_id" class="form-select">
              <option value="">— unapplied —</option>
              <option v-for="b in postedBills" :key="b.id" :value="b.id">
                {{ b.bill_number }} ({{ b.amount_due_to_vendor }})
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
const disbursements = ref([]);
const bankAccounts = ref([]);
const vendors = ref([]);
const bills = ref([]);
const error = ref("");
const submitting = ref(false);

const postedBills = computed(() => bills.value.filter((b) => b.status === "Posted"));

const form = reactive({
  bank_account_id: "",
  vendor_id: "",
  payment_number: "",
  payment_date: new Date().toISOString().slice(0, 10),
  amount: "",
  bill_id: "",
});

async function loadAll() {
  const businessId = businessStore.activeBusinessId;
  if (!businessId) return;
  const [dRes, bankRes, vRes, billRes] = await Promise.all([
    api.get(`/businesses/${businessId}/cash-disbursements`),
    api.get(`/businesses/${businessId}/bank-accounts`),
    api.get(`/businesses/${businessId}/vendors`),
    api.get(`/businesses/${businessId}/purchase-bills`),
  ]);
  disbursements.value = dRes.data;
  bankAccounts.value = bankRes.data;
  vendors.value = vRes.data;
  bills.value = billRes.data;
}

async function onCreate() {
  error.value = "";
  submitting.value = true;
  try {
    const allocations = form.bill_id ? [{ document_id: form.bill_id, amount_applied: form.amount }] : [];
    await api.post(`/businesses/${businessStore.activeBusinessId}/cash-disbursements`, {
      bank_account_id: form.bank_account_id,
      vendor_id: form.vendor_id,
      payment_number: form.payment_number,
      payment_date: form.payment_date,
      amount: form.amount,
      allocations,
    });
    form.payment_number = "";
    form.amount = "";
    form.bill_id = "";
    await loadAll();
  } catch (err) {
    error.value = err.response?.data?.detail || "Could not create payment.";
  } finally {
    submitting.value = false;
  }
}

async function onPost(disbursementId) {
  await api.post(`/businesses/${businessStore.activeBusinessId}/cash-disbursements/${disbursementId}/post`);
  await loadAll();
}

onMounted(loadAll);
</script>
