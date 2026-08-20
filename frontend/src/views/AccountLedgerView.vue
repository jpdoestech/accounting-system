<template>
  <div v-if="ledger" class="view-root">
    <div class="page-header">
      <div>
        <h4 class="mb-0">{{ ledger.account_code }} — {{ ledger.account_name }}</h4>
        <p class="text-muted mb-0">
          Opening balance: {{ formatMoney(ledger.opening_balance) }} · Closing balance: {{ formatMoney(ledger.closing_balance) }}
        </p>
      </div>
      <div class="search-box">
        <i class="bi bi-search"></i>
        <input v-model="search" type="text" class="form-control form-control-sm" placeholder="Search description, memo, reference…" />
      </div>
    </div>

    <div class="view-scroll-area">
      <div class="table-scroll">
        <table class="table table-sm bg-white">
          <colgroup>
            <col style="width: 14%" />
            <col style="width: 40%" />
            <col style="width: 15%" />
            <col style="width: 15%" />
            <col style="width: 16%" />
          </colgroup>
          <thead>
            <tr>
              <th>Date</th>
              <th>Reference / Memo</th>
              <th class="text-end">Debit</th>
              <th class="text-end">Credit</th>
              <th class="text-end">Balance</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(line, i) in pagedItems" :key="i">
              <td>{{ line.entry_date }}</td>
              <td class="text-muted small">{{ line.description || line.memo || line.reference || "—" }}</td>
              <td class="text-end figure">{{ line.debit !== "0.00" ? formatMoney(line.debit) : "" }}</td>
              <td class="text-end figure">{{ line.credit !== "0.00" ? formatMoney(line.credit) : "" }}</td>
              <td class="text-end figure">{{ formatMoney(line.running_balance) }}</td>
            </tr>
            <tr v-if="!ledger.lines.length">
              <td colspan="5" class="text-muted text-center py-3">No activity yet.</td>
            </tr>
            <tr v-else-if="!filtered.length">
              <td colspan="5" class="text-muted text-center py-3">No lines match "{{ search }}".</td>
            </tr>
          </tbody>
        </table>
      </div>
      <PaginationBar
        v-if="filtered.length"
        v-model:page="page"
        v-model:page-size="pageSize"
        :total-items="totalItems"
      />
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

const props = defineProps({ businessId: String, accountId: String });
const businessStore = useBusinessStore();
const ledger = ref(null);
const ledgerLines = computed(() => ledger.value?.lines || []);
const { query: search, filtered } = useTextFilter(ledgerLines, (l) => [l.description, l.memo, l.reference]);
const { page, pageSize, pagedItems, totalItems } = usePagination(filtered);

async function loadLedger() {
  const bId = props.businessId || businessStore.activeBusinessId;
  const { data } = await api.get(`/businesses/${bId}/accounts/${props.accountId}/ledger`);
  ledger.value = data;
}

onMounted(loadLedger);
watch(() => props.accountId, loadLedger);
</script>
