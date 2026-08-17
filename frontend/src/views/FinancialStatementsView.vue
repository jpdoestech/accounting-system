<template>
  <div>
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
                  <td class="text-end">{{ l.amount }}</td>
                </tr>
                <tr class="fw-bold border-top">
                  <td>Total Assets</td>
                  <td class="text-end">{{ bs.total_assets }}</td>
                </tr>
              </tbody>
            </table>

            <div class="small text-muted mb-1">Liabilities</div>
            <table class="table table-sm">
              <tbody>
                <tr v-for="l in bs.liabilities" :key="l.account_id">
                  <td>{{ l.account_code }} — {{ l.account_name }}</td>
                  <td class="text-end">{{ l.amount }}</td>
                </tr>
                <tr class="fw-bold border-top">
                  <td>Total Liabilities</td>
                  <td class="text-end">{{ bs.total_liabilities }}</td>
                </tr>
              </tbody>
            </table>

            <div class="small text-muted mb-1">Equity</div>
            <table class="table table-sm">
              <tbody>
                <tr v-for="l in bs.equity" :key="l.account_id">
                  <td>{{ l.account_code }} — {{ l.account_name }}</td>
                  <td class="text-end">{{ l.amount }}</td>
                </tr>
                <tr>
                  <td>Net Income (current)</td>
                  <td class="text-end">{{ bs.net_income_to_date }}</td>
                </tr>
                <tr class="fw-bold border-top">
                  <td>Total Equity</td>
                  <td class="text-end">{{ bs.total_equity }}</td>
                </tr>
                <tr class="fw-bold border-top">
                  <td>Total Liabilities + Equity</td>
                  <td class="text-end">{{ bs.total_liabilities_and_equity }}</td>
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
              <tr><td>Revenue</td><td class="text-end">{{ incomeStatement.total_revenue }}</td></tr>
              <tr><td>Cost of Sales</td><td class="text-end">({{ incomeStatement.total_cost_of_sales }})</td></tr>
              <tr class="fw-bold border-top"><td>Gross Profit</td><td class="text-end">{{ incomeStatement.gross_profit }}</td></tr>
              <tr><td>Operating Expenses</td><td class="text-end">({{ incomeStatement.total_expenses }})</td></tr>
              <tr class="fw-bold border-top"><td>Operating Income</td><td class="text-end">{{ incomeStatement.operating_income }}</td></tr>
              <tr><td>Other Income</td><td class="text-end">{{ incomeStatement.total_other_income }}</td></tr>
              <tr><td>Other Expenses</td><td class="text-end">({{ incomeStatement.total_other_expenses }})</td></tr>
              <tr class="fw-bold border-top"><td>Net Income</td><td class="text-end">{{ incomeStatement.net_income }}</td></tr>
            </tbody>
          </table>
        </div>

        <div class="card p-3 mt-4">
          <h6>Budget Variance</h6>
          <select v-model="selectedBudgetId" class="form-select form-select-sm mb-2" @change="loadVariance">
            <option value="">— select a budget —</option>
            <option v-for="b in budgets" :key="b.id" :value="b.id">{{ b.name }}</option>
          </select>

          <table v-if="variance" class="table table-sm mb-0">
            <thead><tr><th>Account</th><th class="text-end">Budgeted</th><th class="text-end">Actual</th><th class="text-end">Variance</th></tr></thead>
            <tbody>
              <tr v-for="row in variance.rows" :key="row.account_id">
                <td>{{ row.account_code }} — {{ row.account_name }}</td>
                <td class="text-end">{{ row.budgeted_amount }}</td>
                <td class="text-end">{{ row.actual_amount }}</td>
                <td class="text-end" :class="Number(row.variance) < 0 ? 'text-danger' : 'text-success'">{{ row.variance }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import api from "../services/api";
import { useBusinessStore } from "../stores/business";

const businessStore = useBusinessStore();
const bsDate = ref(new Date().toISOString().slice(0, 10));
const isFrom = ref(new Date().toISOString().slice(0, 8) + "01");
const isTo = ref(new Date().toISOString().slice(0, 10));
const bs = ref(null);
const incomeStatement = ref(null);
const budgets = ref([]);
const selectedBudgetId = ref("");
const variance = ref(null);

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
  const { data } = await api.get(`/businesses/${businessStore.activeBusinessId}/budgets`);
  budgets.value = data;
});
</script>
