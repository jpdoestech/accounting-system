<template>
  <div class="view-root">
    <div class="page-header">
      <div>
        <span class="eyebrow">Sales</span>
        <h4 class="mb-0">Sales Invoices</h4>
      </div>
      <div class="d-flex align-items-center gap-2">
        <div class="search-box">
          <i class="bi bi-search"></i>
          <input v-model="search" type="text" class="form-control form-control-sm" placeholder="Search no., customer, description…" />
        </div>
        <button class="btn btn-primary btn-sm" @click="openCreate">
          <i class="bi bi-plus-lg"></i> New Sales Invoice
        </button>
      </div>
    </div>

    <div v-if="postError" class="alert alert-danger py-2 small">{{ postError }}</div>

    <div class="card view-scroll-area">
      <div class="table-scroll">
        <table class="table table-hover mb-0">
          <colgroup>
            <col style="width: 32px" />
            <col style="width: 13%" />
            <col style="width: 11%" />
            <col style="width: 24%" />
            <col style="width: 13%" />
            <col style="width: 11%" />
            <col style="width: 130px" />
          </colgroup>
          <thead>
            <tr>
              <th></th>
              <th class="ps-3">No.</th>
              <th>Date</th>
              <th>Customer</th>
              <th class="text-end">Total</th>
              <th>Status</th>
              <th class="table-actions pe-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="inv in pagedItems" :key="inv.id">
              <tr class="invoice-row" @click="toggleExpand(inv.id)">
                <td class="text-center text-muted">
                  <i class="bi" :class="expandedId === inv.id ? 'bi-chevron-down' : 'bi-chevron-right'"></i>
                </td>
                <td class="ps-3 fw-medium">{{ inv.invoice_number }}</td>
                <td class="text-muted small">{{ inv.invoice_date }}</td>
                <td class="text-muted text-truncate">{{ customerName(inv.customer_id) }}</td>
                <td class="text-end figure">{{ formatMoney(inv.grand_total) }}</td>
                <td>
                  <span class="badge-pill" :class="inv.status === 'Posted' ? 'badge-pill--green' : 'badge-pill--muted'">
                    {{ inv.status }}
                  </span>
                </td>
                <td class="table-actions pe-3" @click.stop>
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
              <tr v-if="expandedId === inv.id" class="invoice-detail-row">
                <td colspan="7" class="p-0">
                  <div class="invoice-detail">
                    <div v-if="loadingDetail" class="text-muted small py-2">Loading lines…</div>
                    <table v-else class="table table-sm mb-0 invoice-detail__table">
                      <thead>
                        <tr>
                          <th>Description</th>
                          <th>Account</th>
                          <th>Item</th>
                          <th class="text-end">Qty</th>
                          <th class="text-end">Unit Price</th>
                          <th>Tax</th>
                          <th class="text-end">Line Total</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(line, i) in detailLines" :key="i">
                          <td>{{ line.description }}</td>
                          <td class="text-muted">{{ accountLabel(line.revenue_account_id) }}</td>
                          <td class="text-muted">{{ itemLabel(line.item_id) }}</td>
                          <td class="text-end figure">{{ formatNumber(line.quantity) }}</td>
                          <td class="text-end figure">{{ formatMoney(line.unit_price) }}</td>
                          <td class="text-muted">{{ line.tax_rule_code || "—" }}</td>
                          <td class="text-end figure">{{ formatMoney(line.line_amount) }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
          <tfoot v-if="filtered.length">
            <tr>
              <td colspan="4" class="ps-3 text-end fw-semibold">Grand Total (all filtered invoices)</td>
              <td class="text-end figure fw-semibold">{{ formatMoney(grandTotal) }}</td>
              <td colspan="2"></td>
            </tr>
          </tfoot>
        </table>
      </div>

      <PaginationBar
        v-if="filtered.length"
        v-model:page="page"
        v-model:page-size="pageSize"
        :total-items="totalItems"
      />

      <div v-if="!invoices.length" class="empty-state">
        <i class="bi bi-receipt"></i>
        No invoices yet. Click "New Sales Invoice" to create your first one.
      </div>
      <div v-else-if="!filtered.length" class="empty-state">
        <i class="bi bi-search"></i>
        No invoices match "{{ search }}".
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
import { useTextFilter } from "../composables/useTextFilter";
import { formatMoney, formatNumber } from "../utils/format";

const businessStore = useBusinessStore();
const invoices = ref([]);
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
function accountLabel(id) {
  const a = accounts.value.find((x) => x.id === id);
  return a ? `${a.code} — ${a.name}` : "—";
}
function itemLabel(id) {
  if (!id) return "—";
  const it = items.value.find((x) => x.id === id);
  return it ? `${it.sku} — ${it.name}` : "—";
}

const { query: search, filtered } = useTextFilter(invoices, (inv) => [
  inv.invoice_number,
  inv.invoice_date,
  customerName(inv.customer_id),
  inv.status,
]);
const { page, pageSize, pagedItems, totalItems } = usePagination(filtered);

// Grand total across every invoice matching the current search (not
// just the current page) -- what "grand total" means to an
// accountant is the total of everything they're looking at, not one
// screenful of it.
const grandTotal = computed(() => filtered.value.reduce((sum, inv) => sum + Number(inv.grand_total || 0), 0));

// Expand-in-place row detail: click a row to reveal its line items
// (description/account/item/qty/price/tax) without leaving the list.
const expandedId = ref(null);
const detailLines = ref([]);
const loadingDetail = ref(false);

async function toggleExpand(invoiceId) {
  if (expandedId.value === invoiceId) {
    expandedId.value = null;
    detailLines.value = [];
    return;
  }
  expandedId.value = invoiceId;
  loadingDetail.value = true;
  try {
    const { data } = await api.get(`/businesses/${businessStore.activeBusinessId}/sales-invoices/${invoiceId}`);
    detailLines.value = data.lines;
  } finally {
    loadingDetail.value = false;
  }
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

<style scoped>
.invoice-row {
  cursor: pointer;
}

.invoice-detail-row td {
  background: #fafbfc;
}

.invoice-detail {
  padding: 0.5rem 1rem 0.75rem 2.5rem;
}

.invoice-detail__table {
  background: transparent;
}

.invoice-detail__table thead th {
  font-size: 0.68rem;
  color: var(--text-muted);
  background: transparent;
  border-bottom: 1px solid var(--border);
}
</style>
