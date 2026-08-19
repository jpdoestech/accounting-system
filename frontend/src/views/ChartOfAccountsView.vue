<template>
  <div class="view-root">
    <div class="page-header">
      <div>
        <span class="eyebrow">Accounting · Master data</span>
        <h4 class="mb-0">Chart of Accounts</h4>
      </div>
      <div class="d-flex align-items-center gap-2">
        <div class="search-box">
          <i class="bi bi-search"></i>
          <input v-model="search" type="text" class="form-control form-control-sm" placeholder="Search code, name, type…" />
        </div>
        <button class="btn btn-primary btn-sm" @click="openCreate">
          <i class="bi bi-plus-lg"></i> New account
        </button>
      </div>
    </div>

    <div class="card view-scroll-area">
      <div class="table-scroll">
        <table class="table table-hover mb-0">
        <thead>
          <tr>
            <th class="ps-3">Code</th>
            <th>Name</th>
            <th>Type</th>
            <th>Status</th>
            <th class="table-actions pe-3">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in pagedItems" :key="a.id">
            <td class="ps-3 figure text-muted">{{ a.code }}</td>
            <td class="fw-medium">{{ a.name }}</td>
            <td><span class="badge-pill badge-pill--muted">{{ a.account_type }}</span></td>
            <td>
              <span class="badge-pill" :class="a.is_active === false ? 'badge-pill--muted' : 'badge-pill--green'">
                {{ a.is_active === false ? "Inactive" : "Active" }}
              </span>
            </td>
            <td class="table-actions pe-3">
              <span class="row-action-links">
                <router-link
                  :to="{ name: 'account-ledger', params: { businessId: businessStore.activeBusinessId, accountId: a.id } }"
                  class="row-action-link"
                >
                  View ledger
                </router-link>
                <button class="row-action-link" @click="openEdit(a)">Edit</button>
              </span>
            </td>
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

      <div v-if="!loading && !items.length" class="empty-state">
        <i class="bi bi-diagram-3"></i>
        No accounts yet. Add your first one to start recording transactions.
      </div>
      <div v-else-if="!loading && items.length && !filtered.length" class="empty-state">
        <i class="bi bi-search"></i>
        No accounts match "{{ search }}".
      </div>
    </div>

    <EntityFormModal
      v-model:show="showForm"
      :title="editingId ? 'Edit account' : 'New account'"
      :fields="fields"
      :initial-values="formInitialValues"
      :submitting="submitting"
      :error="formError"
      :submit-label="editingId ? 'Save changes' : 'Add account'"
      @submit="onSubmit"
    />
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useBusinessStore } from "../stores/business";
import EntityFormModal from "../components/EntityFormModal.vue";
import PaginationBar from "../components/PaginationBar.vue";
import { useCrudResource } from "../composables/useCrudResource";
import { usePagination } from "../composables/usePagination";
import { useTextFilter } from "../composables/useTextFilter";

const businessStore = useBusinessStore();
const { items, loading, create, update } = useCrudResource("/accounts");
const { query: search, filtered } = useTextFilter(items, (a) => [a.code, a.name, a.account_type]);
const { page, pageSize, pagedItems, totalItems } = usePagination(filtered);

const accountTypes = [
  "Asset",
  "Liability",
  "Equity",
  "Revenue",
  "Cost of Sales",
  "Expense",
  "Other Income",
  "Other Expense",
];

const createFields = [
  { key: "code", label: "Code", required: true, colClass: "col-md-3" },
  { key: "name", label: "Name", required: true, colClass: "col-md-9" },
  {
    key: "account_type",
    label: "Type",
    type: "select",
    required: true,
    colClass: "col-12",
    options: accountTypes.map((t) => ({ value: t, label: t })),
  },
  { key: "description", label: "Description", colClass: "col-12" },
];

const editFields = [
  { key: "code", label: "Code", required: true, colClass: "col-md-3" },
  { key: "name", label: "Name", required: true, colClass: "col-md-9" },
  {
    key: "account_type",
    label: "Type",
    type: "select",
    required: true,
    colClass: "col-12",
    options: accountTypes.map((t) => ({ value: t, label: t })),
    hint: "Changing this reclassifies the account on financial statements going forward. Past reports already run are unaffected.",
  },
  { key: "description", label: "Description", colClass: "col-12" },
  {
    key: "is_active",
    type: "checkbox",
    label: "",
    checkLabel: "Active (uncheck to retire this account)",
    colClass: "col-12",
  },
];

const fields = ref(createFields);
const showForm = ref(false);
const editingId = ref(null);
const submitting = ref(false);
const formError = ref("");
const formInitialValues = ref({});

function openCreate() {
  editingId.value = null;
  fields.value = createFields;
  formInitialValues.value = { account_type: "" };
  formError.value = "";
  showForm.value = true;
}

function openEdit(account) {
  editingId.value = account.id;
  fields.value = editFields;
  formInitialValues.value = { ...account, is_active: account.is_active !== false };
  formError.value = "";
  showForm.value = true;
}

async function onSubmit(values) {
  formError.value = "";
  submitting.value = true;
  try {
    if (editingId.value) {
      await update(editingId.value, values);
    } else {
      await create(values);
    }
    showForm.value = false;
  } catch (err) {
    formError.value = err.response?.data?.detail || "Could not save account.";
  } finally {
    submitting.value = false;
  }
}
</script>
