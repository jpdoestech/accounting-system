<template>
  <div class="view-root">
    <div class="page-header">
      <div>
        <span class="eyebrow">Banking</span>
        <h4 class="mb-0">Cash Disbursements</h4>
      </div>
      <div class="d-flex align-items-center gap-2">
        <div class="search-box">
          <i class="bi bi-search"></i>
          <input v-model="search" type="text" class="form-control form-control-sm" placeholder="Search no., vendor…" />
        </div>
        <button class="btn btn-primary btn-sm" @click="openCreate">
          <i class="bi bi-plus-lg"></i> New Payment
        </button>
      </div>
    </div>

    <div v-if="postError" class="alert alert-danger py-2 small">{{ postError }}</div>

    <div class="card view-scroll-area">
      <div class="table-scroll">
        <table class="table table-hover mb-0 data-grid data-grid--cash-disbursements">
          <colgroup>
            <col style="width: 3%" />
            <col style="width: 15%" />
            <col style="width: 12%" />
            <col style="width: 31%" />
            <col style="width: 14%" />
            <col style="width: 11%" />
            <col style="width: 14%" />
          </colgroup>
          <thead>
            <tr>
              <th></th>
              <th class="ps-3">No.</th>
              <th>Date</th>
              <th>Vendor</th>
              <th class="text-end">Amount</th>
              <th>Status</th>
              <th class="table-actions pe-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="d in pagedItems" :key="d.id">
              <tr class="row-expandable" @click="toggleExpand(d.id)">
                <td class="text-center text-muted">
                  <i class="bi" :class="expandedId === d.id ? 'bi-chevron-down' : 'bi-chevron-right'"></i>
                </td>
                <td class="ps-3 fw-medium">{{ d.payment_number }}</td>
                <td class="text-muted small">{{ d.payment_date }}</td>
                <td class="text-muted text-truncate">{{ vendorName(d.vendor_id) }}</td>
                <td class="text-end figure">{{ formatMoney(d.amount) }}</td>
                <td>
                  <span class="badge-pill" :class="d.status === 'Posted' ? 'badge-pill--green' : 'badge-pill--muted'">
                    {{ d.status }}
                  </span>
                </td>
                <td class="table-actions pe-3" @click.stop>
                  <span v-if="d.status === 'Draft'" class="row-action-links">
                    <button class="row-action-link" @click="openEdit(d.id)">Edit</button>
                    <button class="row-action-link row-action-link--danger" @click="askDelete(d)">Delete</button>
                    <button class="row-action-link" :disabled="postingId === d.id" @click="onPost(d.id)">
                      Post
                    </button>
                  </span>
                </td>
              </tr>
              <tr v-if="expandedId === d.id" class="row-detail">
                <td colspan="7" class="row-detail__inner">
                  <div class="small">
                    <span class="text-muted">Bank account:</span> {{ bankAccountName(d.bank_account_id) }}
                  </div>
                  <div v-if="d.allocations?.length" class="small mt-1">
                    <span class="text-muted">Applied to:</span>
                    <span v-for="(a, i) in d.allocations" :key="i">
                      {{ billNumber(a.purchase_bill_id) }} ({{ formatMoney(a.amount_applied) }})<span v-if="i < d.allocations.length - 1">, </span>
                    </span>
                  </div>
                  <div v-else class="small text-muted mt-1">Not applied to any bill (unapplied payment).</div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <PaginationBar
        v-if="filtered.length"
        v-model:page="page"
        v-model:page-size="pageSize"
        :total-items="totalItems"
      >
        <template #summary>
          <span class="fw-semibold">Grand Total:</span>
          <span class="figure fw-semibold">{{ formatMoney(grandTotal) }}</span>
        </template>
      </PaginationBar>

      <div v-if="!disbursements.length" class="empty-state">
        <i class="bi bi-credit-card"></i>
        No payments yet. Click "New Payment" to record money going out.
      </div>
      <div v-else-if="!filtered.length" class="empty-state">
        <i class="bi bi-search"></i>
        No payments match "{{ search }}".
      </div>
    </div>

    <FormModal
      v-model:show="showForm"
      :title="editingId ? 'Edit Payment' : 'New Payment'"
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
import FormModal from "../components/FormModal.vue";
import { usePagination } from "../composables/usePagination";
import { useTextFilter } from "../composables/useTextFilter";
import { formatMoney } from "../utils/format";

const businessStore = useBusinessStore();
const disbursements = ref([]);
const bankAccounts = ref([]);
const vendors = ref([]);
const bills = ref([]);
const error = ref("");
const submitting = ref(false);
const postError = ref("");
const postingId = ref(null);
const editingId = ref(null);
const showForm = ref(false);

const pendingDelete = ref(null);
const deleting = ref(false);

const postedBills = computed(() => bills.value.filter((b) => b.status === "Posted"));

function vendorName(id) {
  return vendors.value.find((v) => v.id === id)?.name || "—";
}
function bankAccountName(id) {
  return bankAccounts.value.find((b) => b.id === id)?.name || "—";
}
function billNumber(id) {
  return bills.value.find((b) => b.id === id)?.bill_number || "—";
}

const { query: search, filtered } = useTextFilter(disbursements, (d) => [
  d.payment_number,
  d.payment_date,
  vendorName(d.vendor_id),
  d.status,
]);
const { page, pageSize, pagedItems, totalItems } = usePagination(filtered);

const grandTotal = computed(() => filtered.value.reduce((sum, d) => sum + Number(d.amount || 0), 0));

const expandedId = ref(null);
function toggleExpand(disbursementId) {
  expandedId.value = expandedId.value === disbursementId ? null : disbursementId;
}

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
  showForm.value = true;
  snapshot();
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
    showForm.value = false;
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

<style scoped>
.row-expandable {
  cursor: pointer;
}

.row-detail td {
  background: #fafbfc;
}

.row-detail__inner {
  padding: 0.6rem 1rem 0.75rem 2.5rem !important;
}
</style>
