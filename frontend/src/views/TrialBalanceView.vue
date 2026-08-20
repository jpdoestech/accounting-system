<template>
  <div class="view-root">
    <div class="page-header">
      <div>
        <h4 class="mb-0">Trial Balance</h4>
        <p class="text-muted small mb-0">All posted journal entries, as of today.</p>
      </div>
      <div class="search-box">
        <i class="bi bi-search"></i>
        <input v-model="search" type="text" class="form-control form-control-sm" placeholder="Search code, account…" />
      </div>
    </div>

    <div class="view-scroll-area">
      <div class="table-scroll">
        <table class="table table-sm bg-white data-grid data-grid--trial-balance">
          <colgroup>
            <col style="width: 14%" />
            <col style="width: 46%" />
            <col style="width: 20%" />
            <col style="width: 20%" />
          </colgroup>
          <thead>
            <tr>
              <th>Code</th>
              <th>Account</th>
              <th class="text-end">Debit</th>
              <th class="text-end">Credit</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in pagedItems" :key="row.account_id">
              <td class="text-muted figure">{{ row.account_code }}</td>
              <td>{{ row.account_name }}</td>
              <td class="text-end figure">{{ row.debit !== "0.00" ? formatMoney(row.debit) : "" }}</td>
              <td class="text-end figure">{{ row.credit !== "0.00" ? formatMoney(row.credit) : "" }}</td>
            </tr>
            <tr v-if="!rows.length">
              <td colspan="4" class="text-muted text-center py-3">No posted entries yet.</td>
            </tr>
            <tr v-else-if="!filtered.length">
              <td colspan="4" class="text-muted text-center py-3">No accounts match "{{ search }}".</td>
            </tr>
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
          <span><span class="fw-semibold">Debit:</span> <span class="figure fw-semibold">{{ formatMoney(totalDebit) }}</span></span>
          <span><span class="fw-semibold">Credit:</span> <span class="figure fw-semibold">{{ formatMoney(totalCredit) }}</span></span>
        </template>
      </PaginationBar>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import api from "../services/api";
import { useBusinessStore } from "../stores/business";
import PaginationBar from "../components/PaginationBar.vue";
import { usePagination } from "../composables/usePagination";
import { useTextFilter } from "../composables/useTextFilter";
import { formatMoney } from "../utils/format";

const businessStore = useBusinessStore();
const rows = ref([]);
const { query: search, filtered } = useTextFilter(rows, (r) => [r.account_code, r.account_name]);
const { page, pageSize, pagedItems, totalItems } = usePagination(filtered);

// Grand totals reflect ALL rows (not filtered/paged) -- a trial
// balance's whole point is that total debits = total credits across
// every account, so narrowing by search shouldn't change what the
// footer proves.
const totalDebit = computed(() => rows.value.reduce((sum, r) => sum + Number(r.debit), 0));
const totalCredit = computed(() => rows.value.reduce((sum, r) => sum + Number(r.credit), 0));

async function loadTrialBalance() {
  if (!businessStore.activeBusinessId) return;
  const { data } = await api.get(`/businesses/${businessStore.activeBusinessId}/reports/trial-balance`);
  rows.value = data;
}

onMounted(loadTrialBalance);
watch(() => businessStore.activeBusinessId, loadTrialBalance);
</script>
