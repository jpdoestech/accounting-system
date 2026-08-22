<template>
  <div class="view-root">
    <div class="page-header">
      <div>
        <span class="eyebrow">Accounting</span>
        <h4 class="mb-0">Journal Entries</h4>
      </div>
      <div class="d-flex align-items-center gap-2">
        <div class="search-box">
          <i class="bi bi-search"></i>
          <input v-model="search" type="text" class="form-control form-control-sm" placeholder="Search reference, memo, source…" />
        </div>
        <button class="btn btn-primary btn-sm" @click="openCreate">
          <i class="bi bi-plus-lg"></i> New Journal Entry
        </button>
      </div>
    </div>

    <div v-if="reverseError" class="alert alert-danger py-2 small">{{ reverseError }}</div>

    <div class="card view-scroll-area">
      <div class="table-scroll">
        <table class="table table-hover mb-0 data-grid data-grid--journal-entries">
          <thead>
            <tr>
              <th></th>
              <th class="ps-3">Date</th>
              <th>Reference</th>
              <th>Memo</th>
              <th class="text-end">Amount</th>
              <th>Status</th>
              <th class="table-actions pe-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="entry in pagedItems" :key="entry.id">
              <tr class="row-expandable" @click="toggleExpand(entry.id)">
                <td class="text-center text-muted">
                  <i class="bi" :class="expandedId === entry.id ? 'bi-chevron-down' : 'bi-chevron-right'"></i>
                </td>
                <td class="ps-3 fw-medium">{{ entry.entry_date }}</td>
                <td class="text-muted">{{ entry.reference || "—" }}</td>
                <td class="text-muted text-truncate">
                  {{ entry.memo || "—" }}
                  <span class="badge-pill badge-pill--muted ms-1">{{ entry.source }}</span>
                </td>
                <td class="text-end figure">{{ formatMoney(entryAmount(entry)) }}</td>
                <td>
                  <span class="badge-pill" :class="entry.status === 'Reversed' ? 'badge-pill--muted' : 'badge-pill--green'">
                    {{ entry.status }}
                  </span>
                </td>
                <td class="table-actions pe-3" @click.stop>
                  <span v-if="entry.status === 'Posted'" class="row-action-links">
                    <button class="row-action-link row-action-link--danger" @click="askReverse(entry)">
                      Reverse
                    </button>
                  </span>
                </td>
              </tr>
              <tr v-if="expandedId === entry.id" class="row-detail">
                <td colspan="7" class="p-0">
                  <div class="row-detail__inner">
                    <table class="table table-sm mb-0 row-detail__table data-grid data-grid--journal-entry-detail">
                      <thead>
                        <tr>
                          <th>Account</th>
                          <th>Description</th>
                          <th class="text-end">Debit</th>
                          <th class="text-end">Credit</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(line, i) in entry.lines" :key="i">
                          <td class="text-muted">{{ accountLabel(line.account_id) }}</td>
                          <td class="text-muted">{{ line.description || "—" }}</td>
                          <td class="text-end figure">{{ line.debit !== "0.00" ? formatMoney(line.debit) : "" }}</td>
                          <td class="text-end figure">{{ line.credit !== "0.00" ? formatMoney(line.credit) : "" }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </td>
              </tr>
            </template>
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
          <span><span class="fw-semibold">Total Debit:</span> <span class="figure fw-semibold">{{ formatMoney(listTotalDebit) }}</span></span>
          <span><span class="fw-semibold">Total Credit:</span> <span class="figure fw-semibold">{{ formatMoney(listTotalCredit) }}</span></span>
        </template>
      </PaginationBar>

      <div v-if="!entries.length" class="empty-state">
        <i class="bi bi-journal-text"></i>
        No journal entries yet. Click "New Journal Entry" to record one.
      </div>
      <div v-else-if="!filtered.length" class="empty-state">
        <i class="bi bi-search"></i>
        No entries match "{{ search }}".
      </div>
    </div>

    <FormModal v-model:show="showForm" title="New Journal Entry" :is-dirty="isDirty" size="lg">
      <form @submit.prevent="onSubmit">
        <p class="text-muted small">Total debits must equal total credits.</p>
        <div class="row g-2 mb-3">
          <div class="col-md-4">
            <label class="form-label">Date</label>
            <input v-model="entryDate" type="date" class="form-control" required />
          </div>
          <div class="col-md-8">
            <label class="form-label">Reference (optional)</label>
            <input v-model="reference" class="form-control" placeholder="e.g. Check #1234" />
          </div>
          <div class="col-12">
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
              <td>
                <input
                  v-model="line.debit"
                  type="number"
                  step="0.01"
                  min="0"
                  class="form-control form-control-sm"
                  placeholder="0.00"
                  @input="line.credit = ''"
                />
              </td>
              <td>
                <input
                  v-model="line.credit"
                  type="number"
                  step="0.01"
                  min="0"
                  class="form-control form-control-sm"
                  placeholder="0.00"
                  @input="line.debit = ''"
                />
              </td>
              <td>
                <button
                  v-if="lines.length > 2"
                  type="button"
                  class="btn btn-sm btn-outline-danger"
                  @click="lines.splice(i, 1)"
                >
                  <i class="bi bi-x"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <p class="text-muted small mb-3">
          <i class="bi bi-info-circle me-1"></i>
          Each line is <strong>one side only</strong> — enter an amount in either Debit or Credit, never
          both, on the same row. Put the amount under Debit on the account that increases, and the same
          amount under Credit on the account it comes from.
        </p>

        <button type="button" class="btn btn-sm btn-outline-secondary mb-3" @click="addLine">
          <i class="bi bi-plus"></i> Add line
        </button>

        <div class="d-flex gap-4 small text-muted mb-3">
          <span>Total debit: {{ formatMoney(totalDebit) }}</span>
          <span>Total credit: {{ formatMoney(totalCredit) }}</span>
          <span :class="isBalanced ? 'text-success' : 'text-danger'">
            {{ isBalanced ? "Balanced" : "Not balanced" }}
          </span>
        </div>

        <div v-if="error" class="alert alert-danger py-2 small">{{ error }}</div>
        <div class="d-flex justify-content-end gap-2">
          <button type="button" class="btn btn-outline-secondary" @click="showForm = false">Cancel</button>
          <button type="submit" class="btn btn-primary" :disabled="submitting || !isBalanced">
            <span v-if="submitting" class="spinner-border spinner-border-sm me-1"></span>
            Post Entry
          </button>
        </div>
      </form>
    </FormModal>

    <ConfirmDialog
      :show="!!pendingReverse"
      title="Reverse journal entry"
      :message="pendingReverse ? `Post a reversing entry that flips every line's debit/credit? The original entry (${pendingReverse.entry_date}) will be marked Reversed and can't be reversed again.` : ''"
      confirm-label="Reverse entry"
      :busy="reversing"
      @confirm="confirmReverse"
      @cancel="pendingReverse = null"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import api from "../services/api";
import { useBusinessStore } from "../stores/business";
import PaginationBar from "../components/PaginationBar.vue";
import ConfirmDialog from "../components/ConfirmDialog.vue";
import FormModal from "../components/FormModal.vue";
import { usePagination } from "../composables/usePagination";
import { useTextFilter } from "../composables/useTextFilter";
import { formatMoney } from "../utils/format";

const businessStore = useBusinessStore();
const entries = ref([]);
const accounts = ref([]);
const showForm = ref(false);

function accountLabel(id) {
  const a = accounts.value.find((x) => x.id === id);
  return a ? `${a.code} — ${a.name}` : "—";
}
function entryAmount(entry) {
  return entry.lines.reduce((sum, l) => sum + Number(l.debit || 0), 0);
}

// Each entry is individually guaranteed to balance (the backend
// rejects an unbalanced post), so summing every filtered entry's own
// lines this way will always show Total Debit == Total Credit -- same
// "proof of balance" idea as Trial Balance, just at the entry level
// instead of the account level.
const listTotalDebit = computed(() =>
  filtered.value.reduce((sum, e) => sum + e.lines.reduce((s, l) => s + Number(l.debit || 0), 0), 0)
);
const listTotalCredit = computed(() =>
  filtered.value.reduce((sum, e) => sum + e.lines.reduce((s, l) => s + Number(l.credit || 0), 0), 0)
);

const { query: search, filtered } = useTextFilter(entries, (e) => [e.reference, e.memo, e.source, e.status]);
const { page, pageSize, pagedItems, totalItems } = usePagination(filtered);

const expandedId = ref(null);
function toggleExpand(entryId) {
  expandedId.value = expandedId.value === entryId ? null : entryId;
}

const entryDate = ref(new Date().toISOString().slice(0, 10));
const reference = ref("");
const memo = ref("");
const lines = ref([
  { account_id: "", debit: "", credit: "" },
  { account_id: "", debit: "", credit: "" },
]);
const error = ref("");
const submitting = ref(false);
const pristineSnapshot = ref("");

const totalDebit = computed(() => lines.value.reduce((sum, l) => sum + (Number(l.debit) || 0), 0));
const totalCredit = computed(() => lines.value.reduce((sum, l) => sum + (Number(l.credit) || 0), 0));
const isBalanced = computed(
  () => totalDebit.value > 0 && Math.abs(totalDebit.value - totalCredit.value) < 0.005
);
const isDirty = computed(
  () => JSON.stringify({ entryDate: entryDate.value, reference: reference.value, memo: memo.value, lines: lines.value }) !== pristineSnapshot.value
);

function snapshot() {
  pristineSnapshot.value = JSON.stringify({
    entryDate: entryDate.value,
    reference: reference.value,
    memo: memo.value,
    lines: lines.value,
  });
}

function addLine() {
  lines.value.push({ account_id: "", debit: "", credit: "" });
}

function resetForm() {
  entryDate.value = new Date().toISOString().slice(0, 10);
  reference.value = "";
  memo.value = "";
  lines.value = [
    { account_id: "", debit: "", credit: "" },
    { account_id: "", debit: "", credit: "" },
  ];
  error.value = "";
}

function openCreate() {
  resetForm();
  showForm.value = true;
  snapshot();
}

async function loadAll() {
  const businessId = businessStore.activeBusinessId;
  if (!businessId) return;
  const [entriesRes, acctRes] = await Promise.all([
    api.get(`/businesses/${businessId}/journal-entries`),
    api.get(`/businesses/${businessId}/accounts`),
  ]);
  entries.value = entriesRes.data;
  accounts.value = acctRes.data;
}

async function onSubmit() {
  error.value = "";
  submitting.value = true;
  try {
    await api.post(`/businesses/${businessStore.activeBusinessId}/journal-entries`, {
      entry_date: entryDate.value,
      reference: reference.value || null,
      memo: memo.value || null,
      lines: lines.value
        .filter((l) => l.account_id)
        .map((l) => ({
          account_id: l.account_id,
          debit: l.debit || "0.00",
          credit: l.credit || "0.00",
        })),
    });
    showForm.value = false;
    await loadAll();
  } catch (err) {
    error.value = err.response?.data?.detail || "Could not post entry.";
  } finally {
    submitting.value = false;
  }
}

const pendingReverse = ref(null);
const reversing = ref(false);
const reverseError = ref("");

function askReverse(entry) {
  reverseError.value = "";
  pendingReverse.value = entry;
}

async function confirmReverse() {
  if (!pendingReverse.value) return;
  reversing.value = true;
  try {
    await api.post(`/businesses/${businessStore.activeBusinessId}/journal-entries/${pendingReverse.value.id}/reverse`);
    pendingReverse.value = null;
    await loadAll();
  } catch (err) {
    reverseError.value = err.response?.data?.detail || "Could not reverse entry.";
    pendingReverse.value = null;
  } finally {
    reversing.value = false;
  }
}

onMounted(loadAll);
</script>

<style scoped>
.row-expandable {
  cursor: pointer;
}

.row-detail td {
  background: #fafbfc;
}

.row-detail__inner {
  padding: 0.5rem 1rem 0.75rem 2.5rem;
}

.row-detail__table {
  background: transparent;
}

.row-detail__table thead th {
  font-size: 0.68rem;
  color: var(--text-muted);
  background: transparent;
  border-bottom: 1px solid var(--border);
}
</style>
