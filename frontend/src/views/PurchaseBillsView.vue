<template>
  <div class="view-root">
    <div class="page-header">
      <div>
        <span class="eyebrow">Purchases</span>
        <h4 class="mb-0">Purchase Bills</h4>
      </div>
      <div class="d-flex align-items-center gap-2">
        <div class="search-box">
          <i class="bi bi-search"></i>
          <input v-model="search" type="text" class="form-control form-control-sm" placeholder="Search no., vendor, description…" />
        </div>
        <button class="btn btn-primary btn-sm" @click="openCreate">
          <i class="bi bi-plus-lg"></i> New Bill
        </button>
      </div>
    </div>

    <div v-if="postError" class="alert alert-danger py-2 small">{{ postError }}</div>

    <div class="card view-scroll-area">
      <div class="table-scroll">
        <table class="table table-hover mb-0 data-grid data-grid--purchase-bills">
          <colgroup>
            <col style="width: 3%" />
            <col style="width: 13%" />
            <col style="width: 11%" />
            <col style="width: 31%" />
            <col style="width: 13%" />
            <col style="width: 11%" />
            <col style="width: 18%" />
          </colgroup>
          <thead>
            <tr>
              <th></th>
              <th class="ps-3">No.</th>
              <th>Date</th>
              <th>Vendor</th>
              <th class="text-end">Grand Total</th>
              <th>Status</th>
              <th class="table-actions pe-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="bill in pagedItems" :key="bill.id">
              <tr class="row-expandable" @click="toggleExpand(bill.id)">
                <td class="text-center text-muted">
                  <i class="bi" :class="expandedId === bill.id ? 'bi-chevron-down' : 'bi-chevron-right'"></i>
                </td>
                <td class="ps-3 fw-medium">{{ bill.bill_number }}</td>
                <td class="text-muted small">{{ bill.bill_date }}</td>
                <td class="text-muted text-truncate">{{ vendorName(bill.vendor_id) }}</td>
                <td class="text-end figure">{{ formatMoney(bill.grand_total) }}</td>
                <td>
                  <span class="badge-pill" :class="bill.status === 'Posted' ? 'badge-pill--green' : 'badge-pill--muted'">
                    {{ bill.status }}
                  </span>
                </td>
                <td class="table-actions pe-3" @click.stop>
                  <span v-if="bill.status === 'Draft'" class="row-action-links">
                    <button class="row-action-link" @click="openEdit(bill.id)">Edit</button>
                    <button class="row-action-link row-action-link--danger" @click="askDelete(bill)">Delete</button>
                    <button class="row-action-link" :disabled="postingId === bill.id" @click="onPost(bill.id)">
                      Post
                    </button>
                  </span>
                </td>
              </tr>
              <tr v-if="expandedId === bill.id" class="row-detail">
                <td colspan="7" class="p-0">
                  <div class="row-detail__inner">
                    <div v-if="loadingDetail" class="text-muted small py-2">Loading lines…</div>
                    <table v-else class="table table-sm mb-0 row-detail__table">
                      <thead>
                        <tr>
                          <th>Description</th>
                          <th>Account</th>
                          <th>Item</th>
                          <th class="text-end">Qty</th>
                          <th class="text-end">Unit Price</th>
                          <th>VAT</th>
                          <th>W/T</th>
                          <th class="text-end">Line Total</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(line, i) in detailLines" :key="i">
                          <td>{{ line.description }}</td>
                          <td class="text-muted">{{ accountLabel(line.expense_account_id) }}</td>
                          <td class="text-muted">{{ itemLabel(line.item_id) }}</td>
                          <td class="text-end figure">{{ formatNumber(line.quantity) }}</td>
                          <td class="text-end figure">{{ formatMoney(line.unit_price) }}</td>
                          <td class="text-muted">{{ line.tax_rule_code || "—" }}</td>
                          <td class="text-muted">{{ line.withholding_tax_rule_code || "—" }}</td>
                          <td class="text-end figure">{{ formatMoney(line.line_amount) }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
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

      <div v-if="!bills.length" class="empty-state">
        <i class="bi bi-file-earmark-text"></i>
        No bills yet. Click "New Bill" to record your first purchase.
      </div>
      <div v-else-if="!filtered.length" class="empty-state">
        <i class="bi bi-search"></i>
        No bills match "{{ search }}".
      </div>
    </div>

    <FormModal
      v-model:show="showForm"
      :title="editingId ? 'Edit Bill' : 'New Purchase Bill'"
      :is-dirty="isDirty"
      size="lg"
    >
      <form @submit.prevent="onSubmit">
        <div class="mb-2">
          <label class="form-label">Vendor</label>
          <select v-model="form.vendor_id" class="form-select" required>
            <option value="">— Select —</option>
            <option v-for="v in vendors" :key="v.id" :value="v.id">{{ v.name }}</option>
          </select>
        </div>
        <div class="row g-2 mb-2">
          <div class="col-6">
            <label class="form-label">Bill No.</label>
            <input v-model="form.bill_number" class="form-control" required />
          </div>
          <div class="col-6">
            <label class="form-label">Date</label>
            <input v-model="form.bill_date" type="date" class="form-control" required />
          </div>
        </div>

        <hr />
        <div v-for="(line, i) in lines" :key="i" class="mb-2 border rounded p-2">
          <input v-model="line.description" class="form-control form-control-sm mb-1" placeholder="Description" required />
          <select v-model="line.expense_account_id" class="form-select form-select-sm mb-1" required>
            <option value="">— expense account —</option>
            <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.code }} — {{ a.name }}</option>
          </select>
          <select v-model="line.item_id" class="form-select form-select-sm mb-1">
            <option value="">— not an inventory item —</option>
            <option v-for="it in items" :key="it.id" :value="it.id">{{ it.sku }} — {{ it.name }}</option>
          </select>
          <div class="row g-1">
            <div class="col-3">
              <input v-model="line.quantity" type="number" step="0.01" class="form-control form-control-sm" placeholder="Qty" />
            </div>
            <div class="col-3">
              <input v-model="line.unit_price" type="number" step="0.01" class="form-control form-control-sm" placeholder="Unit price" required />
            </div>
            <div class="col-3">
              <select v-model="line.tax_rule_code" class="form-select form-select-sm">
                <option value="">No VAT</option>
                <option v-for="r in vatRules" :key="r.rule_code" :value="r.rule_code">{{ r.rule_code }}</option>
              </select>
            </div>
            <div class="col-2">
              <select v-model="line.withholding_tax_rule_code" class="form-select form-select-sm">
                <option value="">No W/T</option>
                <option v-for="r in withholdingRules" :key="r.rule_code" :value="r.rule_code">{{ r.rule_code }}</option>
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
      title="Delete bill"
      :message="pendingDelete ? `Delete draft bill ${pendingDelete.bill_number}? This can't be undone.` : ''"
      :busy="deleting"
      @confirm="confirmDelete"
      @cancel="pendingDelete = null"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import api from "../services/api";
import PaginationBar from "../components/PaginationBar.vue";
import ConfirmDialog from "../components/ConfirmDialog.vue";
import FormModal from "../components/FormModal.vue";
import { usePagination } from "../composables/usePagination";
import { useTextFilter } from "../composables/useTextFilter";
import { useBusinessStore } from "../stores/business";
import { formatMoney, formatNumber } from "../utils/format";

const businessStore = useBusinessStore();
const bills = ref([]);
const vendors = ref([]);
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

const vatRules = computed(() => taxRules.value.filter((r) => r.tax_type === "VAT"));
const withholdingRules = computed(() => taxRules.value.filter((r) => r.tax_type === "Withholding"));

function vendorName(id) {
  return vendors.value.find((v) => v.id === id)?.name || "—";
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

const { query: search, filtered } = useTextFilter(bills, (bill) => [
  bill.bill_number,
  bill.bill_date,
  vendorName(bill.vendor_id),
  bill.status,
]);
const { page, pageSize, pagedItems, totalItems } = usePagination(filtered);

const grandTotal = computed(() =>
  filtered.value.reduce((sum, bill) => sum + Number(bill.grand_total || 0), 0)
);

const expandedId = ref(null);
const detailLines = ref([]);
const loadingDetail = ref(false);

async function toggleExpand(billId) {
  if (expandedId.value === billId) {
    expandedId.value = null;
    detailLines.value = [];
    return;
  }
  expandedId.value = billId;
  loadingDetail.value = true;
  try {
    const { data } = await api.get(`/businesses/${businessStore.activeBusinessId}/purchase-bills/${billId}`);
    detailLines.value = data.lines;
  } finally {
    loadingDetail.value = false;
  }
}

function blankForm() {
  return {
    vendor_id: "",
    bill_number: "",
    bill_date: new Date().toISOString().slice(0, 10),
  };
}

function blankLine() {
  return {
    description: "",
    expense_account_id: "",
    quantity: "1",
    unit_price: "",
    tax_rule_code: "",
    withholding_tax_rule_code: "",
    item_id: "",
  };
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

async function loadAll() {
  const businessId = businessStore.activeBusinessId;
  if (!businessId) return;
  const [billsRes, vendorsRes, acctRes, taxRes, itemsRes] = await Promise.all([
    api.get(`/businesses/${businessId}/purchase-bills`),
    api.get(`/businesses/${businessId}/vendors`),
    api.get(`/businesses/${businessId}/accounts`),
    api.get(`/businesses/${businessId}/tax-rules`),
    api.get(`/businesses/${businessId}/inventory-items`),
  ]);
  bills.value = billsRes.data;
  vendors.value = vendorsRes.data;
  accounts.value = acctRes.data;
  taxRules.value = taxRes.data.filter((r) => r.status === "Active");
  items.value = itemsRes.data;
}

async function openEdit(billId) {
  error.value = "";
  const { data: bill } = await api.get(`/businesses/${businessStore.activeBusinessId}/purchase-bills/${billId}`);
  editingId.value = bill.id;
  form.vendor_id = bill.vendor_id;
  form.bill_number = bill.bill_number;
  form.bill_date = bill.bill_date;
  lines.value = bill.lines.length
    ? bill.lines.map((l) => ({
        description: l.description,
        expense_account_id: l.expense_account_id,
        quantity: String(l.quantity),
        unit_price: String(l.unit_price),
        tax_rule_code: l.tax_rule_code || "",
        withholding_tax_rule_code: l.withholding_tax_rule_code || "",
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
      .filter((l) => l.expense_account_id && l.unit_price)
      .map((l) => ({
        ...l,
        tax_rule_code: l.tax_rule_code || null,
        withholding_tax_rule_code: l.withholding_tax_rule_code || null,
        item_id: l.item_id || null,
      })),
  };
}

async function onSubmit() {
  error.value = "";
  submitting.value = true;
  try {
    const businessId = businessStore.activeBusinessId;
    if (editingId.value) {
      await api.put(`/businesses/${businessId}/purchase-bills/${editingId.value}`, buildPayload());
    } else {
      await api.post(`/businesses/${businessId}/purchase-bills`, buildPayload());
    }
    showForm.value = false;
    resetForm();
    await loadAll();
  } catch (err) {
    error.value = err.response?.data?.detail || "Could not save bill.";
  } finally {
    submitting.value = false;
  }
}

async function onPost(billId) {
  postError.value = "";
  postingId.value = billId;
  try {
    await api.post(`/businesses/${businessStore.activeBusinessId}/purchase-bills/${billId}/post`);
    await loadAll();
  } catch (err) {
    postError.value = err.response?.data?.detail || "Could not post bill.";
  } finally {
    postingId.value = null;
  }
}

function askDelete(bill) {
  pendingDelete.value = bill;
}

async function confirmDelete() {
  if (!pendingDelete.value) return;
  deleting.value = true;
  try {
    await api.delete(`/businesses/${businessStore.activeBusinessId}/purchase-bills/${pendingDelete.value.id}`);
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
  padding: 0.5rem 1rem 0.75rem 2.5rem;
}

.row-detail__table {
  background: transparent;
}

.row-detail__table thead th {
  font-size: 0.68rem;
  color: var(--text-muted);
  background: transparent;
  border-bottom: 1px solid var(--border);
}
</style>
