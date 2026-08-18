<template>
  <div class="row g-4">
    <div class="col-lg-6">
      <h4>Cash Disbursements</h4>
      <div v-if="postError" class="alert alert-danger py-2 small">{{ postError }}</div>
      <table class="table table-sm table-hover bg-white">
        <thead>
          <tr>
            <th>No.</th>
            <th>Date</th>
            <th class="text-end">Amount</th>
            <th>Status</th>
            <th class="text-end">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="d in pagedItems" :key="d.id">
            <td>{{ d.payment_number }}</td>
            <td class="text-muted small">{{ d.payment_date }}</td>
            <td class="text-end">{{ d.amount }}</td>
            <td>
              <span :class="d.status === 'Posted' ? 'badge text-bg-success' : 'badge text-bg-secondary'">
                {{ d.status }}
              </span>
            </td>
            <td class="text-end">
              <span v-if="d.status === 'Draft'" class="row-action-links justify-content-end">
                <button class="row-action-link" @click="openEdit(d.id)">Edit</button>
                <button class="row-action-link row-action-link--danger" @click="askDelete(d)">Delete</button>
                <button
                  class="btn btn-sm btn-outline-primary ms-1"
                  :disabled="postingId === d.id"
                  @click="onPost(d.id)"
                >
                  <span v-if="postingId === d.id" class="spinner-border spinner-border-sm me-1"></span>
                  Post
                </button>
              </span>
            </td>
          </tr>
          <tr v-if="!disbursements.length">
            <td colspan="5" class="text-muted text-center py-3">No payments yet.</td>
          </tr>
        </tbody>
      </table>
      <PaginationBar
        v-if="disbursements.length"
        v-model:page="page"
        v-model:page-size="pageSize"
        :total-items="totalItems"
      />
    </div>

    <div class="col-lg-6">
      <div class="d-flex align-items-center justify-content-between">
        <h4>{{ editingId ? "Edit Payment" : "New Payment" }}</h4>
        <button v-if="editingId" type="button" class="btn btn-sm btn-link" @click="resetForm">Cancel edit</button>
      </div>
      <form @submit.prevent="onSubmit" class="card p-3">
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
          {{ editingId ? "Save changes" : "Create Draft" }}
        </button>
      </form>
    </div>

    <ConfirmDialog
      :show="!!pendingDelete"
      title="Delete payment"
      :message="pendingDelete ? `Delete draft payment ${pendingDelete.payment_number}? This can't be undone.` : ''"
      :busy="deleting"
      @confirm="confirmDelete"
      @cancel="pendingDelete = null"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import api from "../services/api";
import { useBusinessStore } from "../stores/business";
import PaginationBar from "../components/PaginationBar.vue";
import ConfirmDialog from "../components/ConfirmDialog.vue";
import { usePagination } from "../composables/usePagination";

const businessStore = useBusinessStore();
const disbursements = ref([]);
const { page, pageSize, pagedItems, totalItems } = usePagination(disbursements);
const bankAccounts = ref([]);
const vendors = ref([]);
const bills = ref([]);
const error = ref("");
const submitting = ref(false);
const postError = ref("");
const postingId = ref(null);
const editingId = ref(null);

const pendingDelete = ref(null);
const deleting = ref(false);

const postedBills = computed(() => bills.value.filter((b) => b.status === "Posted"));

function blankForm() {
  return {
    bank_account_id: "",
    vendor_id: "",
    payment_number: "",
    payment_date: new Date().toISOString().slice(0, 10),
    amount: "",
    bill_id: "",
  };
}

const form = reactive(blankForm());

function resetForm() {
  editingId.value = null;
  error.value = "";
  Object.assign(form, blankForm());
}

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

async function openEdit(disbursementId) {
  error.value = "";
  const { data: disbursement } = await api.get(
    `/businesses/${businessStore.activeBusinessId}/cash-disbursements/${disbursementId}`
  );
  editingId.value = disbursement.id;
  form.bank_account_id = disbursement.bank_account_id;
  form.vendor_id = disbursement.vendor_id;
  form.payment_number = disbursement.payment_number;
  form.payment_date = disbursement.payment_date;
  form.amount = String(disbursement.amount);
  form.bill_id = disbursement.allocations?.[0]?.purchase_bill_id || "";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function buildPayload() {
  const allocations = form.bill_id ? [{ document_id: form.bill_id, amount_applied: form.amount }] : [];
  return {
    bank_account_id: form.bank_account_id,
    vendor_id: form.vendor_id,
    payment_number: form.payment_number,
    payment_date: form.payment_date,
    amount: form.amount,
    allocations,
  };
}

async function onSubmit() {
  error.value = "";
  submitting.value = true;
  try {
    const businessId = businessStore.activeBusinessId;
    if (editingId.value) {
      await api.put(`/businesses/${businessId}/cash-disbursements/${editingId.value}`, buildPayload());
    } else {
      await api.post(`/businesses/${businessId}/cash-disbursements`, buildPayload());
    }
    resetForm();
    await loadAll();
  } catch (err) {
    error.value = err.response?.data?.detail || "Could not save payment.";
  } finally {
    submitting.value = false;
  }
}

async function onPost(disbursementId) {
  postError.value = "";
  postingId.value = disbursementId;
  try {
    await api.post(`/businesses/${businessStore.activeBusinessId}/cash-disbursements/${disbursementId}/post`);
    await loadAll();
  } catch (err) {
    postError.value = err.response?.data?.detail || "Could not post payment.";
  } finally {
    postingId.value = null;
  }
}

function askDelete(disbursement) {
  pendingDelete.value = disbursement;
}

async function confirmDelete() {
  if (!pendingDelete.value) return;
  deleting.value = true;
  try {
    await api.delete(`/businesses/${businessStore.activeBusinessId}/cash-disbursements/${pendingDelete.value.id}`);
    if (editingId.value === pendingDelete.value.id) resetForm();
    pendingDelete.value = null;
    await loadAll();
  } finally {
    deleting.value = false;
  }
}

onMounted(loadAll);
</script>
