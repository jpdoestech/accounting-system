<template>
  <div>
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
              <tr><td>Output VAT</td><td class="text-end">{{ vat.output_vat }}</td></tr>
              <tr><td>Input VAT</td><td class="text-end">{{ vat.input_vat }}</td></tr>
              <tr class="fw-bold border-top">
                <td>Net VAT Payable</td>
                <td class="text-end">{{ vat.net_vat_payable }}</td>
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
          <div class="d-flex flex-wrap gap-2">
            <button class="btn btn-sm btn-outline-secondary" @click="loadBook('general-journal')">General Journal</button>
            <button class="btn btn-sm btn-outline-secondary" @click="loadBook('sales-book')">Sales Book</button>
            <button class="btn btn-sm btn-outline-secondary" @click="loadBook('purchase-book')">Purchase Book</button>
            <button class="btn btn-sm btn-outline-secondary" @click="loadBook('cash-receipts-book')">Cash Receipts</button>
            <button class="btn btn-sm btn-outline-secondary" @click="loadBook('cash-disbursements-book')">Cash Disbursements</button>
          </div>
          <pre v-if="bookResult" class="small mt-3 mb-0 bg-light p-2 rounded" style="max-height: 300px; overflow: auto">{{ bookResult }}</pre>
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
                  <td class="text-end">{{ row.income_payment }}</td>
                  <td class="text-end">{{ row.tax_withheld }}</td>
                </tr>
              </tbody>
              <tfoot>
                <tr class="fw-bold border-top">
                  <td>Total</td>
                  <td class="text-end">{{ preview.total_income_payment }}</td>
                  <td class="text-end">{{ preview.total_tax_withheld }}</td>
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
                <td class="text-end">{{ c.total_tax_withheld }}</td>
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

const businessStore = useBusinessStore();
const dateFrom = ref("");
const dateTo = ref("");
const vat = ref(null);
const bookResult = ref("");
const vendors = ref([]);
const certificates = ref([]);
const preview = ref(null);
const error = ref("");

const certForm = reactive({ vendor_id: "", period_start: "", period_end: "" });

async function loadVat() {
  const params = {};
  if (dateFrom.value) params.date_from = dateFrom.value;
  if (dateTo.value) params.date_to = dateTo.value;
  const { data } = await api.get(`/businesses/${businessStore.activeBusinessId}/bir/vat-summary`, { params });
  vat.value = data;
}

async function loadBook(bookName) {
  const { data } = await api.get(`/businesses/${businessStore.activeBusinessId}/bir/books/${bookName}`);
  bookResult.value = JSON.stringify(data, null, 2);
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
  const { data } = await api.get(`/businesses/${businessStore.activeBusinessId}/vendors`);
  vendors.value = data;
  await loadCertificates();
});
</script>
