<template>
  <div class="view-root">
    <div class="page-header">
      <div>
        <span class="eyebrow">Fixed Assets · Master data</span>
        <h4 class="mb-0">Fixed Assets</h4>
      </div>
      <div class="d-flex align-items-center gap-2">
        <div class="search-box">
          <i class="bi bi-search"></i>
          <input v-model="search" type="text" class="form-control form-control-sm" placeholder="Search code, name…" />
        </div>
        <button class="btn btn-primary btn-sm" @click="openCreate">
          <i class="bi bi-plus-lg"></i> New asset
        </button>
      </div>
    </div>

    <div v-if="depreciateError" class="alert alert-danger py-2 small">{{ depreciateError }}</div>

    <div class="card view-scroll-area">
      <div class="table-scroll">
        <table class="table table-hover mb-0 data-grid data-grid--fixed-assets">
        <colgroup>
          <col style="width: 12%" />
          <col style="width: 30%" />
          <col style="width: 12%" />
          <col style="width: 12%" />
          <col style="width: 12%" />
          <col style="width: 8%" />
          <col style="width: 14%" />
        </colgroup>
        <thead>
          <tr>
            <th class="ps-3">Code</th>
            <th>Name</th>
            <th class="text-end">Cost</th>
            <th class="text-end">Accum. Dep.</th>
            <th class="text-end">Book Value</th>
            <th>Status</th>
            <th class="table-actions pe-3">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in pagedItems" :key="a.id">
            <td class="ps-3 figure text-muted">{{ a.asset_code }}</td>
            <td class="fw-medium text-truncate">{{ a.name }}</td>
            <td class="text-end figure">{{ formatMoney(a.acquisition_cost) }}</td>
            <td class="text-end figure">{{ formatMoney(a.accumulated_depreciation) }}</td>
            <td class="text-end figure">{{ formatMoney(bookValue(a)) }}</td>
            <td>
              <span class="badge-pill" :class="a.status === 'Active' ? 'badge-pill--green' : 'badge-pill--muted'">
                {{ a.status }}
              </span>
            </td>
            <td class="table-actions pe-3">
              <span class="row-action-links">
                <button class="row-action-link" @click="openEdit(a)">Edit</button>
                <button
                  class="row-action-link"
                  :disabled="a.status !== 'Active' || depreciatingId === a.id"
                  @click="onDepreciate(a)"
                >
                  {{ depreciatingId === a.id ? "Posting…" : "Post depreciation" }}
                </button>
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
      >
        <template #summary>
          <span><span class="fw-semibold">Cost:</span> <span class="figure fw-semibold">{{ formatMoney(totals.cost) }}</span></span>
          <span><span class="fw-semibold">Accum. Dep.:</span> <span class="figure fw-semibold">{{ formatMoney(totals.dep) }}</span></span>
          <span><span class="fw-semibold">Book Value:</span> <span class="figure fw-semibold">{{ formatMoney(totals.book) }}</span></span>
        </template>
      </PaginationBar>

      <div v-if="!loading && !items.length" class="empty-state">
        <i class="bi bi-building"></i>
        No fixed assets yet. Add one to start tracking depreciation.
      </div>
      <div v-else-if="!loading && items.length && !filtered.length" class="empty-state">
        <i class="bi bi-search"></i>
        No assets match "{{ search }}".
      </div>
    </div>

    <EntityFormModal
      v-model:show="showForm"
      :title="editingId ? 'Edit asset' : 'New asset'"
      :fields="fields"
      :initial-values="formInitialValues"
      :submitting="submitting"
      :error="formError"
      :submit-label="editingId ? 'Save changes' : 'Add asset'"
      @submit="onSubmit"
    />
  </div>
</template>

<script setup>
import { onMounted, ref, computed } from "vue";
import api from "../services/api";
import { useBusinessStore } from "../stores/business";
import EntityFormModal from "../components/EntityFormModal.vue";
import PaginationBar from "../components/PaginationBar.vue";
import { useCrudResource } from "../composables/useCrudResource";
import { usePagination } from "../composables/usePagination";
import { useTextFilter } from "../composables/useTextFilter";
import { formatMoney } from "../utils/format";

const businessStore = useBusinessStore();
const { items, loading, create, update, load } = useCrudResource("/fixed-assets");
const { query: search, filtered } = useTextFilter(items, (a) => [a.asset_code, a.name]);
const { page, pageSize, pagedItems, totalItems } = usePagination(filtered);

function bookValue(asset) {
  return Number(asset.acquisition_cost || 0) - Number(asset.accumulated_depreciation || 0);
}
const totals = computed(() => {
  const cost = filtered.value.reduce((sum, a) => sum + Number(a.acquisition_cost || 0), 0);
  const dep = filtered.value.reduce((sum, a) => sum + Number(a.accumulated_depreciation || 0), 0);
  return { cost, dep, book: cost - dep };
});

// acquisition_cost, salvage_value, useful_life_months, and
// acquisition_date all feed the depreciation schedule -- the backend
// locks them on edit once the asset has (or could have) posted
// depreciation entries, so only asset_code/name are editable after
// creation.
const createFields = [
  { key: "asset_code", label: "Asset code", required: true, colClass: "col-md-4" },
  { key: "name", label: "Name", required: true, colClass: "col-md-8" },
  { key: "acquisition_date", label: "Acquisition date", type: "date", required: true, colClass: "col-md-6" },
  { key: "acquisition_cost", label: "Cost", type: "number", required: true, colClass: "col-md-6" },
  { key: "salvage_value", label: "Salvage value", type: "number", colClass: "col-md-6" },
  { key: "useful_life_months", label: "Useful life (months)", type: "number", required: true, colClass: "col-md-6" },
  { key: "asset_account_id", label: "Asset account", type: "select", required: true, colClass: "col-12", options: [] },
  {
    key: "accumulated_depreciation_account_id",
    label: "Accum. depreciation account",
    type: "select",
    required: true,
    colClass: "col-12",
    options: [],
  },
  {
    key: "depreciation_expense_account_id",
    label: "Depreciation expense account",
    type: "select",
    required: true,
    colClass: "col-12",
    options: [],
  },
];

const editFields = [
  { key: "asset_code", label: "Asset code", required: true, colClass: "col-md-4" },
  { key: "name", label: "Name", required: true, colClass: "col-md-8" },
];

const fields = ref(createFields);
const showForm = ref(false);
const editingId = ref(null);
const submitting = ref(false);
const formError = ref("");
const formInitialValues = ref({});
const depreciatingId = ref(null);
const depreciateError = ref("");

async function loadGlAccounts() {
  if (!businessStore.activeBusinessId) return;
  const { data } = await api.get(`/businesses/${businessStore.activeBusinessId}/accounts`);
  const options = data.map((a) => ({ value: a.id, label: `${a.code} — ${a.name}` }));
  createFields.find((f) => f.key === "asset_account_id").options = options;
  createFields.find((f) => f.key === "accumulated_depreciation_account_id").options = options;
  createFields.find((f) => f.key === "depreciation_expense_account_id").options = options;
}

function openCreate() {
  editingId.value = null;
  fields.value = createFields;
  formInitialValues.value = {
    acquisition_date: new Date().toISOString().slice(0, 10),
    salvage_value: "0.00",
    useful_life_months: 36,
    asset_account_id: "",
    accumulated_depreciation_account_id: "",
    depreciation_expense_account_id: "",
  };
  formError.value = "";
  showForm.value = true;
}

function openEdit(asset) {
  editingId.value = asset.id;
  fields.value = editFields;
  formInitialValues.value = { ...asset };
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
    formError.value = err.response?.data?.detail || "Could not save asset.";
  } finally {
    submitting.value = false;
  }
}

async function onDepreciate(asset) {
  depreciateError.value = "";
  depreciatingId.value = asset.id;
  const today = new Date();
  try {
    await api.post(`/businesses/${businessStore.activeBusinessId}/fixed-assets/${asset.id}/depreciate`, {
      period_year: today.getFullYear(),
      period_month: today.getMonth() + 1,
      entry_date: today.toISOString().slice(0, 10),
    });
    await load();
  } catch (err) {
    depreciateError.value = err.response?.data?.detail || "Could not post depreciation.";
  } finally {
    depreciatingId.value = null;
  }
}

onMounted(loadGlAccounts);
</script>
