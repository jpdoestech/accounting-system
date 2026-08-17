<template>
  <div v-if="ledger">
    <h4>{{ ledger.account_code }} — {{ ledger.account_name }}</h4>
    <p class="text-muted">
      Opening balance: {{ ledger.opening_balance }} · Closing balance: {{ ledger.closing_balance }}
    </p>

    <table class="table table-sm bg-white">
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
        <tr v-for="(line, i) in ledger.lines" :key="i">
          <td>{{ line.entry_date }}</td>
          <td class="text-muted small">{{ line.description || line.memo || line.reference || "—" }}</td>
          <td class="text-end">{{ line.debit !== "0.00" ? line.debit : "" }}</td>
          <td class="text-end">{{ line.credit !== "0.00" ? line.credit : "" }}</td>
          <td class="text-end">{{ line.running_balance }}</td>
        </tr>
        <tr v-if="!ledger.lines.length">
          <td colspan="5" class="text-muted text-center py-3">No activity yet.</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from "vue";
import api from "../services/api";
import { useBusinessStore } from "../stores/business";

const props = defineProps({ businessId: String, accountId: String });
const businessStore = useBusinessStore();
const ledger = ref(null);

async function loadLedger() {
  const bId = props.businessId || businessStore.activeBusinessId;
  const { data } = await api.get(`/businesses/${bId}/accounts/${props.accountId}/ledger`);
  ledger.value = data;
}

onMounted(loadLedger);
watch(() => props.accountId, loadLedger);
</script>
