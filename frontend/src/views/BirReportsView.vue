<template>
  <div class="view-scroll-page">
    <h4>BIR Compliance</h4>

    <div class="row g-4">
      <div class="col-lg-6">
        <div class="card p-3">
          <h6>VAT Summary</h6>
          <div class="row g-2 mb-3">
            <div class="col-6">
              <label class="form-label small">From</label>
              <input v-model="dateFrom" type="date" class="form-control form-control-sm" />
            </div>
            <div class="col-6">
              <label class="form-label small">To</label>
              <input v-model="dateTo" type="date" class="form-control form-control-sm" />
            </div>
          </div>
          <button class="btn btn-sm btn-outline-primary mb-3" @click="loadVat">Run</button>

          <table v-if="vat" class="table table-sm mb-0">
            <tbody>
              <tr><td>Output VAT</td><td class="text-end figure">{{ formatMoney(vat.output_vat) }}</td></tr>
              <tr><td>Input VAT</td><td class="text-end figure">{{ formatMoney(vat.input_vat) }}</td></tr>
              <tr class="fw-bold border-top">
                <td>Net VAT Payable</td>
                <td class="text-end figure">{{ formatMoney(vat.net_vat_payable) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="card p-3 mt-4">
          <h6>Books of Accounts</h6>
          <p class="text-muted small">
            Generated from posted transactions — General Journal, Sales Book, Purchase
            Book, Cash Receipts Book, Cash Disbursements Book, and the General Ledger
            (per account, from Chart of Accounts).
          </p>
          <div class="d-flex flex-wrap gap-2 mb-3">
            <button
              v-for="b in bookOptions"
              :key="b.key"
              class="btn btn-sm"
              :class="activeBook === b.key ? 'btn-primary' : 'btn-outline-secondary'"
              @click="loadBook(b.key)"
            >
              {{ b.label }}
            </button>
          </div>

          <div v-if="loadingBook" class="text-muted small">Loading…</div>

          <!-- General Journal -->
          <div v-else-if="activeBook === 'general-journal'" class="book-scroll">
            <div v-for="(entry, i) in bookRows" :key="i" class="mb-3 pb-2 border-bottom">
              <div class="d-flex justify-content-between small text-muted">
                <span>{{ entry.entry_date }} · {{ entry.reference || "—" }} · {{ entry.memo || "—" }}</span>
                <span class="badge-pill badge-pill--muted">{{ entry.source }}</span>
              </div>
              <table class="table table-sm mb-0 mt-1">
                <tbody>
                  <tr v-for="(line, j) in entry.lines" :key="j">
                    <td class="text-muted">{{ accountLabel(line.account_id) }}</td>
                    <td class="text-muted small">{{ line.description || "—" }}</td>
                    <td class="text-end figure">{{ line.debit !== "0.00" ? formatMoney(line.debit) : "" }}</td>
                    <td class="text-end figure">{{ line.credit !== "0.00" ? formatMoney(line.credit) : "" }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-if="!bookRows.length" class="text-muted small text-center py-3">No entries in this range.</div>
          </div>

          <!-- Sales Book -->
          <table v-else-if="activeBook === 'sales-book'" class="table table-sm book-scroll">
            <thead><tr><th>No.</th><th>Date</th><th>Customer</th><th class="text-end">Total</th><th>Status</th></tr></thead>
            <tbody>
              <tr v-for="row in bookRows" :key="row.id">
                <td>{{ row.invoice_number }}</td>
                <td class="text-muted small">{{ row.invoice_date }}</td>
                <td class="text-muted">{{ customerLabel(row.customer_id) }}</td>
                <td class="text-end figure">{{ formatMoney(row.grand_total) }}</td>
                <td><span class="badge-pill" :class="row.status === 'Posted' ? 'badge-pill--green' : 'badge-pill--muted'">{{ row.status }}</span></td>
              </tr>
              <tr v-if="!bookRows.length"><td colspan="5" class="text-muted text-center py-3">No invoices in this range.</td></tr>
            </tbody>
          </table>

          <!-- Purchase Book -->
          <table v-else-if="activeBook === 'purchase-book'" class="table table-sm book-scroll">
            <thead><tr><th>No.</th><th>Date</th><th>Vendor</th><th class="text-end">Total</th><th>Status</th></tr></thead>
            <tbody>
              <tr v-for="row in bookRows" :key="row.id">
                <td>{{ row.bill_number }}</td>
                <td class="text-muted small">{{ row.bill_date }}</td>
                <td class="text-muted">{{ vendorLabel(row.vendor_id) }}</td>
                <td class="text-end figure">{{ formatMoney(row.amount_due_to_vendor) }}</td>
                <td><span class="badge-pill" :class="row.status === 'Posted' ? 'badge-pill--green' : 'badge-pill--muted'">{{ row.status }}</span></td>
              </tr>
              <tr v-if="!bookRows.length"><td colspan="5" class="text-muted text-center py-3">No bills in this range.</td></tr>
            </tbody>
          </table>

          <!-- Cash Receipts Book -->
          <table v-else-if="activeBook === 'cash-receipts-book'" class="table table-sm book-scroll">
            <thead><tr><th>No.</th><th>Date</th><th>Customer</th><th class="text-end">Amount</th><th>Status</th></tr></thead>
            <tbody>
              <tr v-for="row in bookRows" :key="row.id">
                <td>{{ row.receipt_number }}</td>
                <td class="text-muted small">{{ row.receipt_date }}</td>
                <td class="text-muted">{{ customerLabel(row.customer_id) }}</td>
                <td class="text-end figure">{{ formatMoney(row.amount) }}</td>
                <td><span class="badge-pill" :class="row.status === 'Posted' ? 'badge-pill--green' : 'badge-pill--muted'">{{ row.status }}</span></td>
              </tr>
              <tr v-if="!bookRows.length"><td colspan="5" class="text-muted text-center py-3">No receipts in this range.</td></tr>
            </tbody>
          </table>

          <!-- Cash Disbursements Book -->
          <table v-else-if="activeBook === 'cash-disbursements-book'" class="table table-sm book-scroll">
            <thead><tr><th>No.</th><th>Date</th><th>Vendor</th><th class="text-end">Amount</th><th>Status</th></tr></thead>
            <tbody>
              <tr v-for="row in bookRows" :key="row.id">
                <td>{{ row.payment_number }}</td>
                <td class="text-muted small">{{ row.payment_date }}</td>
                <td class="text-muted">{{ vendorLabel(row.vendor_id) }}</td>
                <td class="text-end figure">{{ formatMoney(row.amount) }}</td>
                <td><span class="badge-pill" :class="row.status === 'Posted' ? 'badge-pill--green' : 'badge-pill--muted'">{{ row.status }}</span></td>
              </tr>
              <tr v-if="!bookRows.length"><td colspan="5" class="text-muted text-center py-3">No payments in this range.</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="col-lg-6">
        <div class="card p-3">
          <h6>Withholding Tax Certificate (BIR Form 2307)</h6>
          <div class="row g-2 mb-2">
            <div class="col-12">
              <label class="form-label small">Vendor</label>
              <select v-model="certForm.vendor_id" class="form-select form-select-sm">
                <option value="">— select —</option>
                <option v-for="v in vendors" :key="v.id" :value="v.id">{{ v.name }}</option>
              </select>
            </div>
            <div class="col-6">
              <label class="form-label small">Period Start</label>
              <input v-model="certForm.period_start" type="date" class="form-control form-control-sm" />
            </div>
            <div class="col-6">
              <label class="form-label small">Period End</label>
              <input v-model="certForm.period_end" type="date" class="form-control form-control-sm" />
            </div>
          </div>
          <div class="d-flex gap-2 mb-3">
            <button class="btn btn-sm btn-outline-primary" @click="onPreview">Preview</button>
            <button class="btn btn-sm btn-primary" @click="onIssue" :disabled="!preview">Issue Certificate</button>
          </div>

          <div v-if="preview">
            <table class="table table-sm">
              <thead><tr><th>ATC</th><th class="text-end">Income Payment</th><th class="text-end">Tax Withheld</th></tr></thead>
              <tbody>
                <tr v-for="row in preview.breakdown" :key="row.atc_code">
                  <td>{{ row.atc_code }}</td>
                  <td class="text-end figure">{{ formatMoney(row.income_payment) }}</td>
                  <td class="text-end figure">{{ formatMoney(row.tax_withheld) }}</td>
                </tr>
              </tbody>
              <tfoot>
                <tr class="fw-bold border-top">
                  <td>Total</td>
                  <td class="text-end figure">{{ formatMoney(preview.total_income_payment) }}</td>
                  <td class="text-end figure">{{ formatMoney(preview.total_tax_withheld) }}</td>
                </tr>
              </tfoot>
            </table>
          </div>
          <div v-if="error" class="alert alert-danger py-2 small mb-0">{{ error }}</div>
        </div>

        <div class="card p-3 mt-4">
          <h6>Issued Certificates</h6>
          <table class="table table-sm mb-0">
            <thead><tr><th>No.</th><th>Period</th><th class="text-end">Tax Withheld</th></tr></thead>
            <tbody>
              <tr v-for="c in certificates" :key="c.id">
                <td>{{ c.certificate_number }}</td>
                <td class="text-muted small">{{ c.period_start }} – {{ c.period_end }}</td>
                <td class="text-end figure">{{ formatMoney(c.total_tax_withheld) }}</td>
              </tr>
              <tr v-if="!certificates.length">
                <td colspan="3" class="text-muted text-center py-3">None issued yet.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import api from "../services/api";
import { useBusinessStore } from "../stores/business";
import { formatMoney } from "../utils/format";

const businessStore = useBusinessStore();
const dateFrom = ref("");
const dateTo = ref("");
const vat = ref(null);

const bookOptions = [
  { key: "general-journal", label: "General Journal" },
  { key: "sales-book", label: "Sales Book" },
  { key: "purchase-book", label: "Purchase Book" },
  { key: "cash-receipts-book", label: "Cash Receipts" },
  { key: "cash-disbursements-book", label: "Cash Disbursements" },
];
const activeBook = ref("");
const bookRows = ref([]);
const loadingBook = ref(false);

const accounts = ref([]);
const customers = ref([]);
const vendors = ref([]);
const certificates = ref([]);
const preview = ref(null);
const error = ref("");

const certForm = reactive({ vendor_id: "", period_start: "", period_end: "" });

function accountLabel(id) {
  const a = accounts.value.find((x) => x.id === id);
  return a ? `${a.code} — ${a.name}` : "—";
}
function customerLabel(id) {
  return customers.value.find((c) => c.id === id)?.name || "—";
}
function vendorLabel(id) {
  return vendors.value.find((v) => v.id === id)?.name || "—";
}

async function loadVat() {
  const params = {};
  if (dateFrom.value) params.date_from = dateFrom.value;
  if (dateTo.value) params.date_to = dateTo.value;
  const { data } = await api.get(`/businesses/${businessStore.activeBusinessId}/bir/vat-summary`, { params });
  vat.value = data;
}

async function loadBook(bookName) {
  activeBook.value = bookName;
  loadingBook.value = true;
  try {
    const { data } = await api.get(`/businesses/${businessStore.activeBusinessId}/bir/books/${bookName}`);
    bookRows.value = data;
  } finally {
    loadingBook.value = false;
  }
}

async function onPreview() {
  error.value = "";
  preview.value = null;
  try {
    const { data } = await api.get(
      `/businesses/${businessStore.activeBusinessId}/bir/withholding-certificates/preview`,
      { params: certForm }
    );
    preview.value = data;
  } catch (err) {
    error.value = err.response?.data?.detail || "Could not preview certificate.";
  }
}

async function onIssue() {
  error.value = "";
  try {
    const certificate_number = `2307-${certForm.period_start}-${Math.floor(Math.random() * 9000 + 1000)}`;
    await api.post(`/businesses/${businessStore.activeBusinessId}/bir/withholding-certificates`, {
      ...certForm,
      certificate_number,
    });
    preview.value = null;
    await loadCertificates();
  } catch (err) {
    error.value = err.response?.data?.detail || "Could not issue certificate.";
  }
}

async function loadCertificates() {
  const { data } = await api.get(`/businesses/${businessStore.activeBusinessId}/bir/withholding-certificates`);
  certificates.value = data;
}

onMounted(async () => {
  const businessId = businessStore.activeBusinessId;
  const [vendorsRes, accountsRes, customersRes] = await Promise.all([
    api.get(`/businesses/${businessId}/vendors`),
    api.get(`/businesses/${businessId}/accounts`),
    api.get(`/businesses/${businessId}/customers`),
  ]);
  vendors.value = vendorsRes.data;
  accounts.value = accountsRes.data;
  customers.value = customersRes.data;
  await loadCertificates();
});
</script>

<style scoped>
.book-scroll {
  max-height: 320px;
  overflow-y: auto;
}
</style>
