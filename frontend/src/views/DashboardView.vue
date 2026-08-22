<template>
  <div v-if="businessStore.loading" class="text-muted">Loading businesses…</div>

  <div v-else-if="!businessStore.businesses.length" class="text-center py-5">
    <i class="bi bi-building display-4 text-muted"></i>
    <h5 class="mt-3">No business set up yet</h5>
    <p class="text-muted">Create your first business profile to get started.</p>
    <router-link to="/business/new" class="btn btn-primary">
      <i class="bi bi-plus-lg"></i> Create Business
    </router-link>
  </div>

  <div v-else class="view-root">
    <div class="page-header">
      <div>
        <span class="eyebrow">Overview</span>
        <h4 class="mb-0">{{ businessStore.activeBusiness?.business_name || businessStore.activeBusiness?.registered_name }}</h4>
        <p class="text-muted small mb-0">
          TIN: {{ businessStore.activeBusiness?.tin || "—" }} ·
          VAT status: {{ businessStore.activeBusiness?.vat_registration_status || "—" }} ·
          Currency: {{ businessStore.activeBusiness?.currency_code }}
        </p>
      </div>
      <router-link
        :to="{ name: 'business-settings', params: { id: businessStore.activeBusinessId } }"
        class="btn btn-outline-secondary btn-sm"
      >
        <i class="bi bi-gear"></i> Business Settings
      </router-link>
    </div>

    <div v-if="loading" class="text-muted small">Loading dashboard…</div>

    <template v-else>
      <div v-if="!currentPeriodOpen" class="alert alert-warning py-2 small d-flex align-items-center gap-2">
        <i class="bi bi-exclamation-triangle"></i>
        <span>
          No open accounting period covers today's date, so nothing can be posted yet.
          <router-link to="/fiscal-periods">Set one up in Fiscal Periods.</router-link>
        </span>
      </div>

      <!-- KPI cards -->
      <div class="row g-3 mb-4">
        <div class="col-md-3">
          <div class="card kpi-card">
            <div class="kpi-card__label">Cash &amp; Bank</div>
            <div class="kpi-card__value">{{ formatMoney(kpi.cash) }}</div>
            <router-link to="/bank-accounts" class="kpi-card__link">View bank accounts</router-link>
            <div v-if="unpostedOpeningBalances" class="kpi-card__note">
              <i class="bi bi-info-circle"></i>
              Looks low? Bank accounts created before an Opening Balance Equity account was
              configured don't get posted automatically. Set one in
              <router-link :to="{ name: 'business-settings', params: { id: businessStore.activeBusinessId } }">Business Settings</router-link>
              so future accounts post themselves, and record this one manually with a
              <router-link to="/journal-entries">journal entry</router-link> in the meantime.
            </div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="card kpi-card">
            <div class="kpi-card__label">Accounts Receivable</div>
            <div class="kpi-card__value" v-if="hasArAccount">{{ formatMoney(kpi.ar) }}</div>
            <div class="kpi-card__value text-muted small" v-else>Not configured</div>
            <router-link to="/sales-invoices" class="kpi-card__link">View sales invoices</router-link>
          </div>
        </div>
        <div class="col-md-3">
          <div class="card kpi-card">
            <div class="kpi-card__label">Accounts Payable</div>
            <div class="kpi-card__value" v-if="hasApAccount">{{ formatMoney(kpi.ap) }}</div>
            <div class="kpi-card__value text-muted small" v-else>Not configured</div>
            <router-link to="/purchase-bills" class="kpi-card__link">View purchase bills</router-link>
          </div>
        </div>
        <div class="col-md-3">
          <div class="card kpi-card">
            <div class="kpi-card__label">Net Income (YTD)</div>
            <div class="kpi-card__value" :class="Number(kpi.netIncome) < 0 ? 'text-danger' : ''">
              {{ formatMoney(kpi.netIncome) }}
            </div>
            <router-link to="/financial-statements">View statements</router-link>
          </div>
        </div>
      </div>

      <div class="row g-3">
        <!-- Needs attention -->
        <div class="col-lg-5">
          <div class="card p-3">
            <h6 class="mb-3">Needs attention</h6>
            <ul class="list-unstyled mb-0">
              <li v-for="item in attentionItems" :key="item.label" class="attention-row">
                <router-link :to="item.to" class="d-flex justify-content-between align-items-center">
                  <span>{{ item.label }}</span>
                  <span class="badge-pill" :class="item.count ? 'badge-pill--gold' : 'badge-pill--muted'">
                    {{ item.count }}
                  </span>
                </router-link>
              </li>
            </ul>
            <div v-if="!attentionItems.some((i) => i.count)" class="text-muted small mt-2">
              Nothing waiting on you right now.
            </div>
          </div>
        </div>

        <!-- Recent activity -->
        <div class="col-lg-7">
          <div class="card p-3">
            <h6 class="mb-3">Recent activity</h6>
            <table class="table table-sm mb-0">
              <tbody>
                <tr v-for="(item, i) in recentActivity" :key="i">
                  <td class="text-muted small" style="width: 100px">{{ item.date }}</td>
                  <td>
                    <router-link :to="item.to">{{ item.label }}</router-link>
                    <span class="badge-pill badge-pill--muted ms-1">{{ item.type }}</span>
                  </td>
                  <td class="text-end figure">{{ formatMoney(item.amount) }}</td>
                </tr>
                <tr v-if="!recentActivity.length">
                  <td colspan="3" class="text-muted text-center py-3">No activity yet.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from "vue";
import api from "../services/api";
import { useBusinessStore } from "../stores/business";
import { formatMoney } from "../utils/format";

const businessStore = useBusinessStore();
const loading = ref(true);
const currentPeriodOpen = ref(true);
const hasArAccount = ref(false);
const hasApAccount = ref(false);

const kpi = ref({ cash: 0, ar: 0, ap: 0, netIncome: 0 });
const unpostedOpeningBalances = ref(false);
const attentionItems = ref([]);
const recentActivity = ref([]);

function today() {
  return new Date().toISOString().slice(0, 10);
}

async function loadDashboard() {
  const businessId = businessStore.activeBusinessId;
  if (!businessId) return;
  loading.value = true;
  try {
    const [settingsRes, bankAccountsRes, balanceSheetRes, periodsRes, invoicesRes, billsRes, receiptsRes, disbursementsRes] =
      await Promise.all([
        api.get(`/businesses/${businessId}/settings`),
        api.get(`/businesses/${businessId}/bank-accounts`),
        api.get(`/businesses/${businessId}/reports/balance-sheet`, { params: { as_of_date: today() } }),
        api.get(`/businesses/${businessId}/periods`),
        api.get(`/businesses/${businessId}/sales-invoices`),
        api.get(`/businesses/${businessId}/purchase-bills`),
        api.get(`/businesses/${businessId}/cash-receipts`),
        api.get(`/businesses/${businessId}/cash-disbursements`),
      ]);

    const settings = settingsRes.data;
    const bankAccounts = bankAccountsRes.data;
    const bs = balanceSheetRes.data;

    // Cash & Bank: sum whatever the balance sheet reports for each bank
    // account's own GL account -- this is the real current balance
    // (opening balance + everything posted since), not just the
    // opening_balance the bank account was set up with.
    const bankAccountGlIds = new Set(bankAccounts.map((b) => b.gl_account_id));
    kpi.value.cash = bs.assets
      .filter((line) => bankAccountGlIds.has(line.account_id))
      .reduce((sum, line) => sum + Number(line.amount), 0);

    const statedOpeningBalances = bankAccounts.reduce((sum, b) => sum + Number(b.opening_balance || 0), 0);
    unpostedOpeningBalances.value = statedOpeningBalances > 0 && kpi.value.cash < statedOpeningBalances;

    hasArAccount.value = !!settings.ar_account_id;
    hasApAccount.value = !!settings.ap_account_id;
    kpi.value.ar = hasArAccount.value
      ? Number(bs.assets.find((l) => l.account_id === settings.ar_account_id)?.amount || 0)
      : 0;
    kpi.value.ap = hasApAccount.value
      ? Number(bs.liabilities.find((l) => l.account_id === settings.ap_account_id)?.amount || 0)
      : 0;
    kpi.value.netIncome = Number(bs.net_income_to_date);

    const periods = periodsRes.data;
    currentPeriodOpen.value = periods.some(
      (p) => p.status === "Open" && p.start_date <= today() && p.end_date >= today()
    );

    const invoices = invoicesRes.data;
    const bills = billsRes.data;
    const receipts = receiptsRes.data;
    const disbursements = disbursementsRes.data;

    attentionItems.value = [
      { label: "Draft sales invoices", count: invoices.filter((i) => i.status === "Draft").length, to: "/sales-invoices" },
      { label: "Draft purchase bills", count: bills.filter((b) => b.status === "Draft").length, to: "/purchase-bills" },
      { label: "Draft cash receipts", count: receipts.filter((r) => r.status === "Draft").length, to: "/cash-receipts" },
      { label: "Draft payments", count: disbursements.filter((d) => d.status === "Draft").length, to: "/cash-disbursements" },
    ];

    // Recent activity: the last few POSTED items across every document
    // type, newest first -- a quick "what just happened" glance.
    const activity = [
      ...invoices
        .filter((i) => i.status === "Posted")
        .map((i) => ({ date: i.invoice_date, label: `Invoice ${i.invoice_number}`, type: "Sales", amount: i.grand_total, to: "/sales-invoices" })),
      ...bills
        .filter((b) => b.status === "Posted")
        .map((b) => ({ date: b.bill_date, label: `Bill ${b.bill_number}`, type: "Purchase", amount: b.amount_due_to_vendor, to: "/purchase-bills" })),
      ...receipts
        .filter((r) => r.status === "Posted")
        .map((r) => ({ date: r.receipt_date, label: `Receipt ${r.receipt_number}`, type: "Receipt", amount: r.amount, to: "/cash-receipts" })),
      ...disbursements
        .filter((d) => d.status === "Posted")
        .map((d) => ({ date: d.payment_date, label: `Payment ${d.payment_number}`, type: "Payment", amount: d.amount, to: "/cash-disbursements" })),
    ];
    activity.sort((a, b) => b.date.localeCompare(a.date));
    recentActivity.value = activity.slice(0, 8);
  } finally {
    loading.value = false;
  }
}

onMounted(loadDashboard);
watch(() => businessStore.activeBusinessId, loadDashboard);
</script>

<style scoped>
.kpi-card {
  padding: 1rem;
}

.kpi-card__label {
  font-size: 0.75rem;
  color: var(--text-muted);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.kpi-card__value {
  font-family: var(--font-body);
  font-size: 1.4rem;
  font-weight: 700;
  margin: 0.25rem 0 0.5rem;
}

.kpi-card__link {
  font-size: 0.78rem;
}

.kpi-card__note {
  font-size: 0.72rem;
  color: var(--text-muted);
  margin-top: 0.5rem;
  line-height: 1.4;
}

.attention-row {
  padding: 0.4rem 0;
  border-bottom: 1px solid var(--border-light);
}

.attention-row:last-child {
  border-bottom: none;
}

.attention-row a {
  color: var(--text);
  text-decoration: none;
}

.attention-row a:hover {
  color: var(--blue);
}
</style>
