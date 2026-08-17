<template>
  <div class="col-lg-8">
    <h4>New Journal Entry</h4>
    <p class="text-muted small">Total debits must equal total credits.</p>

    <form @submit.prevent="onSubmit" class="card p-4">
      <div class="row g-2 mb-3">
        <div class="col-md-4">
          <label class="form-label">Date</label>
          <input v-model="entryDate" type="date" class="form-control" required />
        </div>
        <div class="col-md-8">
          <label class="form-label">Memo</label>
          <input v-model="memo" class="form-control" />
        </div>
      </div>

      <table class="table table-sm">
        <thead>
          <tr>
            <th>Account</th>
            <th style="width: 140px">Debit</th>
            <th style="width: 140px">Credit</th>
            <th style="width: 40px"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(line, i) in lines" :key="i">
            <td>
              <select v-model="line.account_id" class="form-select form-select-sm" required>
                <option value="">— account —</option>
                <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.code }} — {{ a.name }}</option>
              </select>
            </td>
            <td><input v-model="line.debit" type="number" step="0.01" class="form-control form-control-sm" /></td>
            <td><input v-model="line.credit" type="number" step="0.01" class="form-control form-control-sm" /></td>
            <td>
              <button type="button" class="btn btn-sm btn-outline-danger" @click="lines.splice(i, 1)">
                <i class="bi bi-x"></i>
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <button type="button" class="btn btn-sm btn-outline-secondary mb-3" @click="addLine">
        <i class="bi bi-plus"></i> Add line
      </button>

      <div class="d-flex gap-4 small text-muted mb-3">
        <span>Total debit: {{ totalDebit.toFixed(2) }}</span>
        <span>Total credit: {{ totalCredit.toFixed(2) }}</span>
        <span :class="isBalanced ? 'text-success' : 'text-danger'">
          {{ isBalanced ? "Balanced" : "Not balanced" }}
        </span>
      </div>

      <div v-if="error" class="alert alert-danger py-2 small">{{ error }}</div>
      <div v-if="success" class="alert alert-success py-2 small">Journal entry posted.</div>

      <button type="submit" class="btn btn-primary" :disabled="submitting || !isBalanced">
        <span v-if="submitting" class="spinner-border spinner-border-sm me-1"></span>
        Post Entry
      </button>
    </form>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import api from "../services/api";
import { useBusinessStore } from "../stores/business";

const businessStore = useBusinessStore();
const accounts = ref([]);
const entryDate = ref(new Date().toISOString().slice(0, 10));
const memo = ref("");
const lines = ref([
  { account_id: "", debit: "", credit: "" },
  { account_id: "", debit: "", credit: "" },
]);
const error = ref("");
const success = ref(false);
const submitting = ref(false);

const totalDebit = computed(() => lines.value.reduce((sum, l) => sum + (Number(l.debit) || 0), 0));
const totalCredit = computed(() => lines.value.reduce((sum, l) => sum + (Number(l.credit) || 0), 0));
const isBalanced = computed(
  () => totalDebit.value > 0 && Math.abs(totalDebit.value - totalCredit.value) < 0.005
);

function addLine() {
  lines.value.push({ account_id: "", debit: "", credit: "" });
}

async function onSubmit() {
  error.value = "";
  success.value = false;
  submitting.value = true;
  try {
    await api.post(`/businesses/${businessStore.activeBusinessId}/journal-entries`, {
      entry_date: entryDate.value,
      memo: memo.value || null,
      lines: lines.value
        .filter((l) => l.account_id)
        .map((l) => ({
          account_id: l.account_id,
          debit: l.debit || "0.00",
          credit: l.credit || "0.00",
        })),
    });
    success.value = true;
    lines.value = [
      { account_id: "", debit: "", credit: "" },
      { account_id: "", debit: "", credit: "" },
    ];
    memo.value = "";
  } catch (err) {
    error.value = err.response?.data?.detail || "Could not post entry.";
  } finally {
    submitting.value = false;
  }
}

onMounted(async () => {
  const { data } = await api.get(`/businesses/${businessStore.activeBusinessId}/accounts`);
  accounts.value = data;
});
</script>
