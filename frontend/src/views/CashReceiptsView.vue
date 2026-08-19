<template>
  <div class="view-root">
    <div class="page-header">
      <div>
        <span class="eyebrow">Banking</span>
        <h4 class="mb-0">Cash Receipts</h4>
      </div>
      <button class="btn btn-primary btn-sm" @click="openCreate">
        <i class="bi bi-plus-lg"></i> New Receipt
      </button>
    </div>

    <div v-if="postError" class="alert alert-danger py-2 small">{{ postError }}</div>

    <div class="card view-scroll-area">
      <div class="table-scroll">
        <table class="table table-hover mb-0">
          <thead>
            <tr>
              <th class="ps-3">No.</th>
              <th>Date</th>
              <th>Customer</th>
              <th class="text-end">Amount</th>
              <th>Status</th>
              <th class="table-actions pe-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in pagedItems" :key="r.id">
              <td class="ps-3 fw-medium">{{ r.receipt_number }}</td>
              <td class="text-muted small">{{ r.receipt_date }}</td>
              <td class="text-muted">{{ customerName(r.customer_id) }}</td>
              <td class="text-end figure">{{ r.amount }}</td>
              <td>
                <span class="badge-pill" :class="r.status === 'Posted' ? 'badge-pill--green' : 'badge-pill--muted'">
                  {{ r.status }}
                </span>
              </td>
              <td class="table-actions pe-3">
                <span v-if="r.status === 'Draft'" class="row-action-links">
                  <button class="row-action-link" @click="openEdit(r.id)">Edit</button>
                  <button class="row-action-link row-action-link--danger" @click="askDelete(r)">Delete</button>
                  <button class="row-action-link" :disabled="postingId === r.id" @click="onPost(r.id)">
                    Post
                  </button>
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <PaginationBar
        v-if="receipts.length"
        v-model:page="page"
        v-model:page-size="pageSize"
        :total-items="totalItems"
      />

      <div v-if="!receipts.length" class="empty-state">
        <i class="bi bi-cash-coin"></i>
        No receipts yet. Click "New Receipt" to record money coming in.
      </div>
    </div>

    <FormModal
      v-model:show="showForm"
      :title="editingId ? 'Edit Receipt' : 'New Cash Receipt'"
      :is-dirty="isDirty"
      size="md"
    >
      <form @submit.prevent="onSubmit">
        <div class="row g-2">
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

        <div v-if="error" class="alert alert-danger py-2 small mt-3 mb-0">{{ error }}</div>
        <div class="d-flex justify-content-end gap-2 mt-3">
          <button type="button" class="btn btn-outline-secondary" @click="showForm = false">Cancel</button>
          <button type="submit" class="btn btn-primary" :disabled="submitting">
            <span v-if="submitting" class="spinner-border spinner-border-sm me-1"></span>
            {{ editingId ? "Save changes" : "Create Draft" }}
          </button>
        </div>
      </form>
    </FormModal>

    <ConfirmDialog
      :show="!!pendingDelete"
      title="Delete receipt"
      :message="pendingDelete ? `Delete draft receipt ${pendingDelete.receipt_number}? This can't be undone.` : ''"
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
import FormModal from "../components/FormModal.vue";
import { usePagination } from "../composables/usePagination";

const businessStore = useBusinessStore();
const receipts = ref([]);
const { page, pageSize, pagedItems, totalItems } = usePagination(receipts);
const bankAccounts = ref([]);
const customers = ref([]);
const invoices = ref([]);
const error = ref("");
const submitting = ref(false);
const postError = ref("");
const postingId = ref(null);
const editingId = ref(null);
const showForm = ref(false);

const pendingDelete = ref(null);
const deleting = ref(false);

const unpaidInvoices = computed(() => invoices.value.filter((i) => i.status === "Posted"));

function customerName(id) {
  return customers.value.find((c) => c.id === id)?.name || "—";
}

function blankForm() {
  return {
    bank_account_id: "",
    customer_id: "",
    receipt_number: "",
    receipt_date: new Date().toISOString().slice(0, 10),
    amount: "",
    invoice_id: "",
  };
}

const form = reactive(blankForm());
const pristineSnapshot = ref("");
const isDirty = computed(() => JSON.stringify(form) !== pristineSnapshot.value);

function snapshot() {
  pristineSnapshot.value = JSON.stringify(form);
}

function resetForm() {
  editingId.value = null;
  error.value = "";
  Object.assign(form, blankForm());
}

function openCreate() {
  resetForm();
  showForm.value = true;
  snapshot();
}

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

async function openEdit(receiptId) {
  error.value = "";
  const { data: receipt } = await api.get(`/businesses/${businessStore.activeBusinessId}/cash-receipts/${receiptId}`);
  editingId.value = receipt.id;
  form.bank_account_id = receipt.bank_account_id;
  form.customer_id = receipt.customer_id;
  form.receipt_number = receipt.receipt_number;
  form.receipt_date = receipt.receipt_date;
  form.amount = String(receipt.amount);
  form.invoice_id = receipt.allocations?.[0]?.sales_invoice_id || "";
  showForm.value = true;
  snapshot();
}

function buildPayload() {
  const allocations = form.invoice_id ? [{ document_id: form.invoice_id, amount_applied: form.amount }] : [];
  return {
    bank_account_id: form.bank_account_id,
    customer_id: form.customer_id,
    receipt_number: form.receipt_number,
    receipt_date: form.receipt_date,
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
      await api.put(`/businesses/${businessId}/cash-receipts/${editingId.value}`, buildPayload());
    } else {
      await api.post(`/businesses/${businessId}/cash-receipts`, buildPayload());
    }
    showForm.value = false;
    resetForm();
    await loadAll();
  } catch (err) {
    error.value = err.response?.data?.detail || "Could not save receipt.";
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

function askDelete(receipt) {
  pendingDelete.value = receipt;
}

async function confirmDelete() {
  if (!pendingDelete.value) return;
  deleting.value = true;
  try {
    await api.delete(`/businesses/${businessStore.activeBusinessId}/cash-receipts/${pendingDelete.value.id}`);
    if (editingId.value === pendingDelete.value.id) {
      showForm.value = false;
      resetForm();
    }
    pendingDelete.value = null;
    await loadAll();
  } finally {
    deleting.value = false;
  }
}

onMounted(loadAll);
</script>
