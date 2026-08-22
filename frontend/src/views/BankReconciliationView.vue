<template>
  <div v-if="bankAccount" class="view-scroll-page">
    <div class="page-header">
      <div>
        <span class="eyebrow">Banking</span>
        <h4 class="mb-0">Reconcile — {{ bankAccount.name }}</h4>
      </div>
      <router-link to="/bank-accounts" class="btn btn-outline-secondary btn-sm">
        <i class="bi bi-arrow-left"></i> Back to Bank Accounts
      </router-link>
    </div>

    <div class="row g-4">
      <div class="col-lg-7">
        <div class="card p-3">
          <h6 class="mb-3">Uncleared transactions</h6>
          <p class="text-muted small">
            Check off every receipt and payment that appears on your bank statement — only Posted,
            not-yet-cleared transactions for this account show up here.
          </p>

          <div class="uncleared-scroll">
            <table class="table table-sm mb-0">
              <thead>
                <tr>
                  <th style="width: 32px"></th>
                  <th>Date</th>
                  <th>No.</th>
                  <th>Type</th>
                  <th class="text-end">Amount</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in unclearedReceipts" :key="'r-' + r.id">
                  <td><input type="checkbox" v-model="checkedReceiptIds" :value="r.id" /></td>
                  <td class="text-muted small">{{ r.receipt_date }}</td>
                  <td>{{ r.receipt_number }}</td>
                  <td><span class="badge-pill badge-pill--green">Receipt</span></td>
                  <td class="text-end figure">{{ formatMoney(r.amount) }}</td>
                </tr>
                <tr v-for="d in unclearedDisbursements" :key="'d-' + d.id">
                  <td><input type="checkbox" v-model="checkedDisbursementIds" :value="d.id" /></td>
                  <td class="text-muted small">{{ d.payment_date }}</td>
                  <td>{{ d.payment_number }}</td>
                  <td><span class="badge-pill badge-pill--gold">Payment</span></td>
                  <td class="text-end figure">{{ formatMoney(d.amount) }}</td>
                </tr>
                <tr v-if="!unclearedReceipts.length && !unclearedDisbursements.length">
                  <td colspan="5" class="text-muted text-center py-3">Nothing left to clear — everything Posted is already reconciled.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="card p-3 mt-3">
          <h6 class="mb-3">Past reconciliations</h6>
          <table class="table table-sm mb-0">
            <thead>
              <tr>
                <th>Statement Date</th>
                <th class="text-end">Statement Balance</th>
                <th class="text-end">Book Balance</th>
                <th class="text-end">Difference</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="rec in reconciliations" :key="rec.id">
                <td>{{ rec.statement_date }}</td>
                <td class="text-end figure">{{ formatMoney(rec.statement_ending_balance) }}</td>
                <td class="text-end figure">{{ formatMoney(rec.book_balance) }}</td>
                <td class="text-end figure" :class="Number(rec.difference) !== 0 ? 'text-danger' : ''">
                  {{ formatMoney(rec.difference) }}
                </td>
                <td>
                  <span class="badge-pill" :class="rec.status === 'Completed' ? 'badge-pill--green' : 'badge-pill--gold'">
                    {{ rec.status }}
                  </span>
                </td>
              </tr>
              <tr v-if="!reconciliations.length">
                <td colspan="5" class="text-muted text-center py-3">No reconciliations yet.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="col-lg-5">
        <div class="card p-3">
          <h6 class="mb-3">Statement details</h6>
          <div class="mb-2">
            <label class="form-label">Statement Date</label>
            <input v-model="statementDate" type="date" class="form-control" />
          </div>
          <div class="mb-3">
            <label class="form-label">Statement Ending Balance</label>
            <input v-model="statementEndingBalance" type="number" step="0.01" class="form-control" />
          </div>

          <div class="reconcile-summary mb-3">
            <div class="d-flex justify-content-between">
              <span class="text-muted">Selected receipts</span>
              <span class="figure">+{{ formatMoney(selectedReceiptsTotal) }}</span>
            </div>
            <div class="d-flex justify-content-between">
              <span class="text-muted">Selected payments</span>
              <span class="figure">-{{ formatMoney(selectedDisbursementsTotal) }}</span>
            </div>
            <div class="d-flex justify-content-between fw-semibold border-top mt-1 pt-1">
              <span>Projected book balance</span>
              <span class="figure">{{ formatMoney(projectedBookBalance) }}</span>
            </div>
            <div class="d-flex justify-content-between fw-semibold" :class="projectedDifference !== 0 ? 'text-danger' : 'text-success'">
              <span>Difference vs. statement</span>
              <span class="figure">{{ formatMoney(projectedDifference) }}</span>
            </div>
          </div>

          <div v-if="error" class="alert alert-danger py-2 small">{{ error }}</div>
          <button class="btn btn-primary w-100" :disabled="submitting || !statementDate || statementEndingBalance === ''" @click="onReconcile">
            <span v-if="submitting" class="spinner-border spinner-border-sm me-1"></span>
            Reconcile
          </button>
          <p class="text-muted small mt-2 mb-0">
            <i class="bi bi-info-circle me-1"></i>
            If the difference isn't zero, this still saves as a Draft reconciliation so you can see
            exactly how far off things are and keep investigating — nothing is hidden or forced to
            balance.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import api from "../services/api";
import { useBusinessStore } from "../stores/business";
import { formatMoney } from "../utils/format";

const props = defineProps({ businessId: String, bankAccountId: String });
const businessStore = useBusinessStore();

const bankAccount = ref(null);
const receipts = ref([]);
const disbursements = ref([]);
const reconciliations = ref([]);

const checkedReceiptIds = ref([]);
const checkedDisbursementIds = ref([]);

const statementDate = ref(new Date().toISOString().slice(0, 10));
const statementEndingBalance = ref("");
const error = ref("");
const submitting = ref(false);

const unclearedReceipts = computed(() =>
  receipts.value.filter((r) => r.status === "Posted" && !r.is_cleared)
);
const unclearedDisbursements = computed(() =>
  disbursements.value.filter((d) => d.status === "Posted" && !d.is_cleared)
);

const selectedReceiptsTotal = computed(() =>
  unclearedReceipts.value
    .filter((r) => checkedReceiptIds.value.includes(r.id))
    .reduce((sum, r) => sum + Number(r.amount), 0)
);
const selectedDisbursementsTotal = computed(() =>
  unclearedDisbursements.value
    .filter((d) => checkedDisbursementIds.value.includes(d.id))
    .reduce((sum, d) => sum + Number(d.amount), 0)
);

// Mirrors the backend's own math exactly (opening_balance + cleared
// receipts - cleared disbursements) so what you see here before
// submitting matches what the reconciliation will actually record.
const projectedBookBalance = computed(() => {
  if (!bankAccount.value) return 0;
  return Number(bankAccount.value.opening_balance) + selectedReceiptsTotal.value - selectedDisbursementsTotal.value;
});
const projectedDifference = computed(() => {
  const stmt = Number(statementEndingBalance.value) || 0;
  return Math.round((stmt - projectedBookBalance.value) * 100) / 100;
});

async function loadAll() {
  const businessId = businessStore.activeBusinessId;
  const [bankRes, receiptsRes, disbRes, reconRes] = await Promise.all([
    api.get(`/businesses/${businessId}/bank-accounts`),
    api.get(`/businesses/${businessId}/cash-receipts`),
    api.get(`/businesses/${businessId}/cash-disbursements`),
    api.get(`/businesses/${businessId}/bank-accounts/${props.bankAccountId}/reconciliations`),
  ]);
  bankAccount.value = bankRes.data.find((b) => b.id === props.bankAccountId) || null;
  receipts.value = receiptsRes.data.filter((r) => r.bank_account_id === props.bankAccountId);
  disbursements.value = disbRes.data.filter((d) => d.bank_account_id === props.bankAccountId);
  reconciliations.value = reconRes.data;
}

async function onReconcile() {
  error.value = "";
  submitting.value = true;
  try {
    await api.post(`/businesses/${businessStore.activeBusinessId}/bank-accounts/${props.bankAccountId}/reconcile`, {
      statement_date: statementDate.value,
      statement_ending_balance: statementEndingBalance.value,
      receipt_ids_to_clear: checkedReceiptIds.value,
      disbursement_ids_to_clear: checkedDisbursementIds.value,
    });
    checkedReceiptIds.value = [];
    checkedDisbursementIds.value = [];
    statementEndingBalance.value = "";
    await loadAll();
  } catch (err) {
    error.value = err.response?.data?.detail || "Could not reconcile.";
  } finally {
    submitting.value = false;
  }
}

onMounted(loadAll);
</script>

<style scoped>
.uncleared-scroll {
  max-height: 320px;
  overflow-y: auto;
}

.reconcile-summary > div {
  padding: 0.2rem 0;
}
</style>
