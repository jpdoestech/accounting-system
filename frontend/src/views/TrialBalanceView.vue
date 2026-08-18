<template>
  <div>
    <h4>Trial Balance</h4>
    <p class="text-muted small">All posted journal entries, as of today.</p>

    <table class="table table-sm bg-white">
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
          <td class="text-muted">{{ row.account_code }}</td>
          <td>{{ row.account_name }}</td>
          <td class="text-end">{{ row.debit !== "0.00" ? row.debit : "" }}</td>
          <td class="text-end">{{ row.credit !== "0.00" ? row.credit : "" }}</td>
        </tr>
        <tr v-if="!rows.length">
          <td colspan="4" class="text-muted text-center py-3">No posted entries yet.</td>
        </tr>
      </tbody>
      <tfoot v-if="rows.length">
        <tr class="fw-bold border-top">
          <td colspan="2">Total</td>
          <td class="text-end">{{ totalDebit.toFixed(2) }}</td>
          <td class="text-end">{{ totalCredit.toFixed(2) }}</td>
        </tr>
      </tfoot>
    </table>
    <PaginationBar
      v-if="rows.length"
      v-model:page="page"
      v-model:page-size="pageSize"
      :total-items="totalItems"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import api from "../services/api";
import { useBusinessStore } from "../stores/business";
import PaginationBar from "../components/PaginationBar.vue";
import { usePagination } from "../composables/usePagination";

const businessStore = useBusinessStore();
const rows = ref([]);
const { page, pageSize, pagedItems, totalItems } = usePagination(rows);

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
