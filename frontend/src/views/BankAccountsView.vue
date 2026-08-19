<template>
  <div class="view-root">
    <div class="page-header">
      <div>
        <span class="eyebrow">Banking · Master data</span>
        <h4 class="mb-0">Bank Accounts</h4>
      </div>
      <button class="btn btn-primary btn-sm" @click="openCreate">
        <i class="bi bi-plus-lg"></i> New bank account
      </button>
    </div>

    <div class="card view-scroll-area">
      <div class="table-scroll">
        <table class="table table-hover mb-0">
        <thead>
          <tr>
            <th class="ps-3">Name</th>
            <th>Bank</th>
            <th>Account No.</th>
            <th class="text-end">Opening Balance</th>
            <th>Status</th>
            <th class="table-actions pe-3">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="b in pagedItems" :key="b.id">
            <td class="ps-3 fw-medium">{{ b.name }}</td>
            <td class="text-muted">{{ b.bank_name || "—" }}</td>
            <td class="figure text-muted">{{ b.account_number || "—" }}</td>
            <td class="text-end figure">{{ b.opening_balance }}</td>
            <td>
              <span class="badge-pill" :class="b.is_active === false ? 'badge-pill--muted' : 'badge-pill--green'">
                {{ b.is_active === false ? "Inactive" : "Active" }}
              </span>
            </td>
            <td class="table-actions pe-3">
              <span class="row-action-links">
                <button class="row-action-link" @click="openEdit(b)">Edit</button>
              </span>
            </td>
          </tr>
        </tbody>
        </table>
      </div>

      <PaginationBar
        v-if="items.length"
        v-model:page="page"
        v-model:page-size="pageSize"
        :total-items="totalItems"
      />

      <div v-if="!loading && !items.length" class="empty-state">
        <i class="bi bi-bank"></i>
        No bank accounts yet. Add one to record cash receipts and payments.
      </div>
    </div>

    <EntityFormModal
      v-model:show="showForm"
      :title="editingId ? 'Edit bank account' : 'New bank account'"
      :fields="fields"
      :initial-values="formInitialValues"
      :submitting="submitting"
      :error="formError"
      :submit-label="editingId ? 'Save changes' : 'Add bank account'"
      @submit="onSubmit"
    />
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import api from "../services/api";
import { useBusinessStore } from "../stores/business";
import EntityFormModal from "../components/EntityFormModal.vue";
import PaginationBar from "../components/PaginationBar.vue";
import { useCrudResource } from "../composables/useCrudResource";
import { usePagination } from "../composables/usePagination";

const businessStore = useBusinessStore();
const { items, loading, create, update } = useCrudResource("/bank-accounts");
const { page, pageSize, pagedItems, totalItems } = usePagination(items);
const glAccounts = ref([]);

// gl_account_id, opening_balance, and opening_balance_date are only
// settable at creation -- the backend keeps them locked on edit since
// changing the GL mapping or opening balance after transactions exist
// would desync the bank account from its ledger account.
const createFields = [
  { key: "name", label: "Name", required: true, placeholder: "BDO Checking", colClass: "col-md-6" },
  { key: "bank_name", label: "Bank name", colClass: "col-md-6" },
  {
    key: "gl_account_id",
    label: "GL account",
    type: "select",
    required: true,
    colClass: "col-12",
    options: [],
  },
  { key: "account_number", label: "Account number", colClass: "col-md-6" },
  { key: "currency_code", label: "Currency", colClass: "col-md-6", placeholder: "PHP" },
  { key: "opening_balance", label: "Opening balance", type: "number", colClass: "col-md-6" },
  { key: "opening_balance_date", label: "As of", type: "date", colClass: "col-md-6" },
];

const editFields = [
  { key: "name", label: "Name", required: true, colClass: "col-md-6" },
  { key: "bank_name", label: "Bank name", colClass: "col-md-6" },
  { key: "account_number", label: "Account number", colClass: "col-md-6" },
  { key: "currency_code", label: "Currency", colClass: "col-md-6" },
  {
    key: "is_active",
    type: "checkbox",
    label: "",
    checkLabel: "Active (uncheck to retire this bank account)",
    colClass: "col-12",
  },
];

const fields = ref(createFields);
const showForm = ref(false);
const editingId = ref(null);
const submitting = ref(false);
const formError = ref("");
const formInitialValues = ref({});

async function loadGlAccounts() {
  if (!businessStore.activeBusinessId) return;
  const { data } = await api.get(`/businesses/${businessStore.activeBusinessId}/accounts`);
  glAccounts.value = data;
  createFields.find((f) => f.key === "gl_account_id").options = data.map((a) => ({
    value: a.id,
    label: `${a.code} — ${a.name}`,
  }));
}

function openCreate() {
  editingId.value = null;
  fields.value = createFields;
  formInitialValues.value = {
    gl_account_id: "",
    currency_code: "PHP",
    opening_balance: "0.00",
    opening_balance_date: new Date().toISOString().slice(0, 10),
  };
  formError.value = "";
  showForm.value = true;
}

function openEdit(bankAccount) {
  editingId.value = bankAccount.id;
  fields.value = editFields;
  formInitialValues.value = { ...bankAccount, is_active: bankAccount.is_active !== false };
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
    formError.value = err.response?.data?.detail || "Could not save bank account.";
  } finally {
    submitting.value = false;
  }
}

onMounted(loadGlAccounts);
</script>
