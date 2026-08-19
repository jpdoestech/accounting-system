<template>
  <div>
    <div class="page-header">
      <div>
        <span class="eyebrow">Sales</span>
        <h4 class="mb-0">Sales Invoices</h4>
      </div>
      <button class="btn btn-primary btn-sm" @click="openCreate">
        <i class="bi bi-plus-lg"></i> New Sales Invoice
      </button>
    </div>

    <div v-if="postError" class="alert alert-danger py-2 small">{{ postError }}</div>

    <div class="card">
      <div class="table-scroll">
        <table class="table table-hover mb-0">
          <thead>
            <tr>
              <th class="ps-3">No.</th>
              <th>Date</th>
              <th>Customer</th>
              <th class="text-end">Total</th>
              <th>Status</th>
              <th class="table-actions pe-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="inv in pagedItems" :key="inv.id">
              <td class="ps-3 fw-medium">{{ inv.invoice_number }}</td>
              <td class="text-muted small">{{ inv.invoice_date }}</td>
              <td class="text-muted">{{ customerName(inv.customer_id) }}</td>
              <td class="text-end figure">{{ inv.grand_total }}</td>
              <td>
                <span class="badge-pill" :class="inv.status === 'Posted' ? 'badge-pill--green' : 'badge-pill--muted'">
                  {{ inv.status }}
                </span>
              </td>
              <td class="table-actions pe-3">
                <span v-if="inv.status === 'Draft'" class="row-action-links">
                  <button class="row-action-link" @click="openEdit(inv.id)">Edit</button>
                  <button class="row-action-link row-action-link--danger" @click="askDelete(inv)">Delete</button>
                  <button
                    class="row-action-link"
                    :disabled="postingId === inv.id"
                    @click="onPost(inv.id)"
                  >
                    Post
                  </button>
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <PaginationBar
        v-if="invoices.length"
        v-model:page="page"
        v-model:page-size="pageSize"
        :total-items="totalItems"
      />

      <div v-if="!invoices.length" class="empty-state">
        <i class="bi bi-receipt"></i>
        No invoices yet. Click "New Bill Invoice" to create your first one.
      </div>
    </div>

    <FormModal
      v-model:show="showForm"
      :title="editingId ? 'Edit Invoice' : 'New Sales Invoice'"
      :is-dirty="isDirty"
      size="lg"
    >
      <form @submit.prevent="onSubmit">
        <div class="mb-2">
          <label class="form-label">Customer</label>
          <select v-model="form.customer_id" class="form-select" required>
            <option value="">— Select —</option>
            <option v-for="c in customers" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </div>
        <div class="row g-2 mb-2">
          <div class="col-6">
            <label class="form-label">Invoice No.</label>
            <input v-model="form.invoice_number" class="form-control" required />
          </div>
          <div class="col-6">
            <label class="form-label">Date</label>
            <input v-model="form.invoice_date" type="date" class="form-control" required />
          </div>
        </div>

        <hr />
        <div v-for="(line, i) in lines" :key="i" class="mb-2 border rounded p-2">
          <input v-model="line.description" class="form-control form-control-sm mb-1" placeholder="Description" required />
          <select v-model="line.revenue_account_id" class="form-select form-select-sm mb-1" required>
            <option value="">— revenue account —</option>
            <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.code }} — {{ a.name }}</option>
          </select>
          <select v-model="line.item_id" class="form-select form-select-sm mb-1">
            <option value="">— not an inventory item —</option>
            <option v-for="it in items" :key="it.id" :value="it.id">{{ it.sku }} — {{ it.name }} ({{ it.quantity_on_hand }} on hand)</option>
          </select>
          <div class="row g-1">
            <div class="col-4">
              <input v-model="line.quantity" type="number" step="0.01" class="form-control form-control-sm" placeholder="Qty" />
            </div>
            <div class="col-4">
              <input v-model="line.unit_price" type="number" step="0.01" class="form-control form-control-sm" placeholder="Unit price" required />
            </div>
            <div class="col-3">
              <select v-model="line.tax_rule_code" class="form-select form-select-sm">
                <option value="">No tax</option>
                <option v-for="r in taxRules" :key="r.rule_code" :value="r.rule_code">{{ r.rule_code }}</option>
              </select>
            </div>
            <div class="col-1">
              <button
                v-if="lines.length > 1"
                type="button"
                class="btn btn-sm btn-outline-danger w-100"
                title="Remove line"
                @click="lines.splice(i, 1)"
              >
                <i class="bi bi-x"></i>
              </button>
            </div>
          </div>
        </div>
        <button type="button" class="btn btn-sm btn-outline-secondary mb-3" @click="addLine">
          <i class="bi bi-plus"></i> Add line
        </button>

        <div v-if="error" class="alert alert-danger py-2 small">{{ error }}</div>
        <div class="d-flex justify-content-end gap-2">
          <button type="button" class="btn btn-outline-secondary" @click="requestCloseModal">Cancel</button>
          <button type="submit" class="btn btn-primary" :disabled="submitting">
            <span v-if="submitting" class="spinner-border spinner-border-sm me-1"></span>
            {{ editingId ? "Save changes" : "Create Draft" }}
          </button>
        </div>
      </form>
    </FormModal>

    <ConfirmDialog
      :show="!!pendingDelete"
      title="Delete invoice"
      :message="pendingDelete ? `Delete draft invoice ${pendingDelete.invoice_number}? This can't be undone.` : ''"
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
const invoices = ref([]);
const { page, pageSize, pagedItems, totalItems } = usePagination(invoices);
const customers = ref([]);
const accounts = ref([]);
const taxRules = ref([]);
const items = ref([]);
const error = ref("");
const submitting = ref(false);
const postError = ref("");
const postingId = ref(null);
const editingId = ref(null);
const showForm = ref(false);

const pendingDelete = ref(null);
const deleting = ref(false);

function customerName(id) {
  return customers.value.find((c) => c.id === id)?.name || "—";
}

function blankForm() {
  return {
    customer_id: "",
    invoice_number: "",
    invoice_date: new Date().toISOString().slice(0, 10),
  };
}

function blankLine() {
  return { description: "", revenue_account_id: "", quantity: "1", unit_price: "", tax_rule_code: "", item_id: "" };
}

const form = reactive(blankForm());
const lines = ref([blankLine()]);
const pristineSnapshot = ref("");

const isDirty = computed(() => JSON.stringify({ form, lines: lines.value }) !== pristineSnapshot.value);

function snapshot() {
  pristineSnapshot.value = JSON.stringify({ form, lines: lines.value });
}

function addLine() {
  lines.value.push(blankLine());
}

function resetForm() {
  editingId.value = null;
  error.value = "";
  Object.assign(form, blankForm());
  lines.value = [blankLine()];
}

function openCreate() {
  resetForm();
  showForm.value = true;
  snapshot();
}

function requestCloseModal() {
  // Route through FormModal's own confirm-before-discard logic rather
  // than closing directly, so the Cancel button behaves the same as
  // clicking the backdrop or the X.
  showForm.value = false;
}

async function loadAll() {
  const businessId = businessStore.activeBusinessId;
  if (!businessId) return;
  const [invRes, custRes, acctRes, taxRes, itemsRes] = await Promise.all([
    api.get(`/businesses/${businessId}/sales-invoices`),
    api.get(`/businesses/${businessId}/customers`),
    api.get(`/businesses/${businessId}/accounts`),
    api.get(`/businesses/${businessId}/tax-rules`),
    api.get(`/businesses/${businessId}/inventory-items`),
  ]);
  invoices.value = invRes.data;
  customers.value = custRes.data;
  accounts.value = acctRes.data;
  taxRules.value = taxRes.data.filter((r) => r.status === "Active");
  items.value = itemsRes.data;
}

async function openEdit(invoiceId) {
  error.value = "";
  const { data: invoice } = await api.get(`/businesses/${businessStore.activeBusinessId}/sales-invoices/${invoiceId}`);
  editingId.value = invoice.id;
  form.customer_id = invoice.customer_id;
  form.invoice_number = invoice.invoice_number;
  form.invoice_date = invoice.invoice_date;
  lines.value = invoice.lines.length
    ? invoice.lines.map((l) => ({
        description: l.description,
        revenue_account_id: l.revenue_account_id,
        quantity: String(l.quantity),
        unit_price: String(l.unit_price),
        tax_rule_code: l.tax_rule_code || "",
        item_id: l.item_id || "",
      }))
    : [blankLine()];
  showForm.value = true;
  snapshot();
}

function buildPayload() {
  return {
    ...form,
    lines: lines.value
      .filter((l) => l.revenue_account_id && l.unit_price)
      .map((l) => ({ ...l, tax_rule_code: l.tax_rule_code || null, item_id: l.item_id || null })),
  };
}

async function onSubmit() {
  error.value = "";
  submitting.value = true;
  try {
    const businessId = businessStore.activeBusinessId;
    if (editingId.value) {
      await api.put(`/businesses/${businessId}/sales-invoices/${editingId.value}`, buildPayload());
    } else {
      await api.post(`/businesses/${businessId}/sales-invoices`, buildPayload());
    }
    showForm.value = false;
    resetForm();
    await loadAll();
  } catch (err) {
    error.value = err.response?.data?.detail || "Could not save invoice.";
  } finally {
    submitting.value = false;
  }
}

async function onPost(invoiceId) {
  postError.value = "";
  postingId.value = invoiceId;
  try {
    await api.post(`/businesses/${businessStore.activeBusinessId}/sales-invoices/${invoiceId}/post`);
    await loadAll();
  } catch (err) {
    postError.value = err.response?.data?.detail || "Could not post invoice.";
  } finally {
    postingId.value = null;
  }
}

function askDelete(invoice) {
  pendingDelete.value = invoice;
}

async function confirmDelete() {
  if (!pendingDelete.value) return;
  deleting.value = true;
  try {
    await api.delete(`/businesses/${businessStore.activeBusinessId}/sales-invoices/${pendingDelete.value.id}`);
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
