<template>
  <div class="view-scroll-page">
    <h4>Financial Statements</h4>

    <div class="row g-4">
      <div class="col-lg-6">
        <div class="card p-3">
          <h6>Balance Sheet</h6>
          <div class="d-flex gap-2 mb-3">
            <input v-model="bsDate" type="date" class="form-control form-control-sm" />
            <button class="btn btn-sm btn-outline-primary" @click="loadBalanceSheet">Run</button>
          </div>

          <div v-if="bs">
            <div class="small text-muted mb-1">Assets</div>
            <table class="table table-sm">
              <tbody>
                <tr v-for="l in bs.assets" :key="l.account_id">
                  <td>{{ l.account_code }} — {{ l.account_name }}</td>
                  <td class="text-end figure">{{ formatMoney(l.amount) }}</td>
                </tr>
                <tr class="fw-bold border-top">
                  <td>Total Assets</td>
                  <td class="text-end figure">{{ formatMoney(bs.total_assets) }}</td>
                </tr>
              </tbody>
            </table>

            <div class="small text-muted mb-1">Liabilities</div>
            <table class="table table-sm">
              <tbody>
                <tr v-for="l in bs.liabilities" :key="l.account_id">
                  <td>{{ l.account_code }} — {{ l.account_name }}</td>
                  <td class="text-end figure">{{ formatMoney(l.amount) }}</td>
                </tr>
                <tr class="fw-bold border-top">
                  <td>Total Liabilities</td>
                  <td class="text-end figure">{{ formatMoney(bs.total_liabilities) }}</td>
                </tr>
              </tbody>
            </table>

            <div class="small text-muted mb-1">Equity</div>
            <table class="table table-sm">
              <tbody>
                <tr v-for="l in bs.equity" :key="l.account_id">
                  <td>{{ l.account_code }} — {{ l.account_name }}</td>
                  <td class="text-end figure">{{ formatMoney(l.amount) }}</td>
                </tr>
                <tr>
                  <td>Net Income (current)</td>
                  <td class="text-end figure">{{ formatMoney(bs.net_income_to_date) }}</td>
                </tr>
                <tr class="fw-bold border-top">
                  <td>Total Equity</td>
                  <td class="text-end figure">{{ formatMoney(bs.total_equity) }}</td>
                </tr>
                <tr class="fw-bold border-top">
                  <td>Total Liabilities + Equity</td>
                  <td class="text-end figure">{{ formatMoney(bs.total_liabilities_and_equity) }}</td>
                </tr>
              </tbody>
            </table>
            <div :class="bs.is_balanced ? 'text-success small' : 'text-danger small'">
              {{ bs.is_balanced ? "Balanced" : "Not balanced — check for a data issue" }}
            </div>
          </div>
        </div>
      </div>

      <div class="col-lg-6">
        <div class="card p-3">
          <h6>Income Statement</h6>
          <div class="row g-2 mb-3">
            <div class="col-6">
              <input v-model="isFrom" type="date" class="form-control form-control-sm" />
            </div>
            <div class="col-6">
              <input v-model="isTo" type="date" class="form-control form-control-sm" />
            </div>
          </div>
          <button class="btn btn-sm btn-outline-primary mb-3" @click="loadIncomeStatement">Run</button>

          <table v-if="incomeStatement" class="table table-sm mb-0">
            <tbody>
              <tr><td>Revenue</td><td class="text-end figure">{{ formatMoney(incomeStatement.total_revenue) }}</td></tr>
              <tr><td>Cost of Sales</td><td class="text-end figure">({{ formatMoney(incomeStatement.total_cost_of_sales) }})</td></tr>
              <tr class="fw-bold border-top"><td>Gross Profit</td><td class="text-end figure">{{ formatMoney(incomeStatement.gross_profit) }}</td></tr>
              <tr><td>Operating Expenses</td><td class="text-end figure">({{ formatMoney(incomeStatement.total_expenses) }})</td></tr>
              <tr class="fw-bold border-top"><td>Operating Income</td><td class="text-end figure">{{ formatMoney(incomeStatement.operating_income) }}</td></tr>
              <tr><td>Other Income</td><td class="text-end figure">{{ formatMoney(incomeStatement.total_other_income) }}</td></tr>
              <tr><td>Other Expenses</td><td class="text-end figure">({{ formatMoney(incomeStatement.total_other_expenses) }})</td></tr>
              <tr class="fw-bold border-top"><td>Net Income</td><td class="text-end figure">{{ formatMoney(incomeStatement.net_income) }}</td></tr>
            </tbody>
          </table>
        </div>

        <div class="card p-3 mt-4">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <h6 class="mb-0">Budget Variance</h6>
            <button class="btn btn-sm btn-outline-primary" @click="openCreateBudget">
              <i class="bi bi-plus-lg"></i> New Budget
            </button>
          </div>
          <select v-model="selectedBudgetId" class="form-select form-select-sm mb-2" @change="loadVariance">
            <option value="">— select a budget —</option>
            <option v-for="b in budgets" :key="b.id" :value="b.id">{{ b.name }}</option>
          </select>
          <div v-if="!budgets.length" class="text-muted small">
            No budgets yet — click "New Budget" to set one up for a fiscal year.
          </div>

          <table v-if="variance" class="table table-sm mb-0">
            <thead><tr><th>Account</th><th class="text-end">Budgeted</th><th class="text-end">Actual</th><th class="text-end">Variance</th></tr></thead>
            <tbody>
              <tr v-for="row in variance.rows" :key="row.account_id">
                <td>{{ row.account_code }} — {{ row.account_name }}</td>
                <td class="text-end figure">{{ formatMoney(row.budgeted_amount) }}</td>
                <td class="text-end figure">{{ formatMoney(row.actual_amount) }}</td>
                <td class="text-end figure" :class="Number(row.variance) < 0 ? 'text-danger' : 'text-success'">{{ formatMoney(row.variance) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <FormModal v-model:show="showBudgetForm" title="New Budget" :is-dirty="isBudgetFormDirty" size="lg">
      <form @submit.prevent="onCreateBudget">
        <div class="row g-2 mb-3">
          <div class="col-6">
            <label class="form-label">Fiscal Year</label>
            <select v-model="budgetForm.fiscal_year_id" class="form-select" required>
              <option value="">— select —</option>
              <option v-for="fy in fiscalYears" :key="fy.id" :value="fy.id">{{ fy.name }}</option>
            </select>
          </div>
          <div class="col-6">
            <label class="form-label">Budget Name</label>
            <input v-model="budgetForm.name" class="form-control" placeholder="e.g. FY2026 Operating Budget" required />
          </div>
        </div>

        <p class="text-muted small">
          Set a budgeted amount per account. Only accounts with a nonzero amount are saved —
          leave the rest blank.
        </p>
        <div class="budget-lines-scroll mb-3">
          <table class="table table-sm mb-0">
            <thead>
              <tr><th>Account</th><th style="width: 160px">Budgeted Amount</th></tr>
            </thead>
            <tbody>
              <tr v-for="a in budgetableAccounts" :key="a.id">
                <td class="text-muted small">{{ a.code }} — {{ a.name }}</td>
                <td><input v-model="budgetLineAmounts[a.id]" type="number" step="0.01" class="form-control form-control-sm" placeholder="0.00" /></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="budgetFormError" class="alert alert-danger py-2 small">{{ budgetFormError }}</div>
        <div class="d-flex justify-content-end gap-2">
          <button type="button" class="btn btn-outline-secondary" @click="showBudgetForm = false">Cancel</button>
          <button type="submit" class="btn btn-primary" :disabled="budgetSubmitting">
            <span v-if="budgetSubmitting" class="spinner-border spinner-border-sm me-1"></span>
            Create Budget
          </button>
        </div>
      </form>
    </FormModal>
  </div>
</template>

<style scoped>
.budget-lines-scroll {
  max-height: 320px;
  overflow-y: auto;
}
</style>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import api from "../services/api";
import { useBusinessStore } from "../stores/business";
import FormModal from "../components/FormModal.vue";
import { formatMoney } from "../utils/format";

const businessStore = useBusinessStore();
const bsDate = ref(new Date().toISOString().slice(0, 10));
const isFrom = ref(new Date().toISOString().slice(0, 8) + "01");
const isTo = ref(new Date().toISOString().slice(0, 10));
const bs = ref(null);
const incomeStatement = ref(null);
const budgets = ref([]);
const selectedBudgetId = ref("");
const variance = ref(null);

const fiscalYears = ref([]);
const accounts = ref([]);
// Budgets are typically set against expense (and sometimes revenue)
// accounts, not balance-sheet accounts like Cash or AR -- those don't
// have a "budgeted amount" concept the way a spending category does.
const budgetableAccounts = computed(() =>
  accounts.value.filter((a) => a.account_type === "Expense" || a.account_type === "Revenue")
);

const showBudgetForm = ref(false);
const budgetSubmitting = ref(false);
const budgetFormError = ref("");
const budgetForm = reactive({ fiscal_year_id: "", name: "" });
const budgetLineAmounts = reactive({});
const budgetFormPristine = ref("");
const isBudgetFormDirty = computed(
  () => JSON.stringify({ budgetForm, budgetLineAmounts }) !== budgetFormPristine.value
);

function openCreateBudget() {
  budgetForm.fiscal_year_id = "";
  budgetForm.name = "";
  for (const key of Object.keys(budgetLineAmounts)) delete budgetLineAmounts[key];
  budgetFormError.value = "";
  showBudgetForm.value = true;
  budgetFormPristine.value = JSON.stringify({ budgetForm, budgetLineAmounts });
}

async function onCreateBudget() {
  budgetFormError.value = "";
  budgetSubmitting.value = true;
  try {
    const lines = Object.entries(budgetLineAmounts)
      .filter(([, amount]) => amount !== "" && amount !== null && Number(amount) !== 0)
      .map(([account_id, budgeted_amount]) => ({ account_id, budgeted_amount }));
    if (!lines.length) {
      budgetFormError.value = "Enter a budgeted amount for at least one account.";
      return;
    }
    await api.post(`/businesses/${businessStore.activeBusinessId}/budgets`, {
      fiscal_year_id: budgetForm.fiscal_year_id,
      name: budgetForm.name,
      lines,
    });
    showBudgetForm.value = false;
    const { data } = await api.get(`/businesses/${businessStore.activeBusinessId}/budgets`);
    budgets.value = data;
  } catch (err) {
    budgetFormError.value = err.response?.data?.detail || "Could not create budget.";
  } finally {
    budgetSubmitting.value = false;
  }
}

async function loadBalanceSheet() {
  const { data } = await api.get(`/businesses/${businessStore.activeBusinessId}/reports/balance-sheet`, {
    params: { as_of_date: bsDate.value },
  });
  bs.value = data;
}

async function loadIncomeStatement() {
  const { data } = await api.get(`/businesses/${businessStore.activeBusinessId}/reports/income-statement`, {
    params: { period_start: isFrom.value, period_end: isTo.value },
  });
  incomeStatement.value = data;
}

async function loadVariance() {
  if (!selectedBudgetId.value) {
    variance.value = null;
    return;
  }
  const { data } = await api.get(
    `/businesses/${businessStore.activeBusinessId}/budgets/${selectedBudgetId.value}/variance`
  );
  variance.value = data;
}

onMounted(async () => {
  const businessId = businessStore.activeBusinessId;
  const [budgetsRes, fiscalYearsRes, accountsRes] = await Promise.all([
    api.get(`/businesses/${businessId}/budgets`),
    api.get(`/businesses/${businessId}/fiscal-years`),
    api.get(`/businesses/${businessId}/accounts`),
  ]);
  budgets.value = budgetsRes.data;
  fiscalYears.value = fiscalYearsRes.data;
  accounts.value = accountsRes.data;
});
</script>
