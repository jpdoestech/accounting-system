<template>
  <div class="view-root">
    <div class="page-header">
      <div>
        <span class="eyebrow">Inventory · Master data</span>
        <h4 class="mb-0">Inventory Items</h4>
      </div>
      <div class="d-flex align-items-center gap-2">
        <div class="search-box">
          <i class="bi bi-search"></i>
          <input v-model="search" type="text" class="form-control form-control-sm" placeholder="Search SKU, name…" />
        </div>
        <button class="btn btn-primary btn-sm" @click="openCreate">
          <i class="bi bi-plus-lg"></i> New item
        </button>
      </div>
    </div>

    <div class="card view-scroll-area">
      <div class="table-scroll">
        <table class="table table-hover mb-0 data-grid data-grid--inventory-items">
        <colgroup>
          <col style="width: 12%" />
          <col style="width: 32%" />
          <col style="width: 12%" />
          <col style="width: 12%" />
          <col style="width: 14%" />
          <col style="width: 8%" />
          <col style="width: 10%" />
        </colgroup>
        <thead>
          <tr>
            <th class="ps-3">SKU</th>
            <th>Name</th>
            <th class="text-end">Qty on Hand</th>
            <th class="text-end">Avg. Cost</th>
            <th class="text-end">Stock Value</th>
            <th>Status</th>
            <th class="table-actions pe-3">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in pagedItems" :key="item.id">
            <td class="ps-3 figure text-muted">{{ item.sku }}</td>
            <td class="fw-medium text-truncate">{{ item.name }}</td>
            <td class="text-end figure">{{ formatNumber(item.quantity_on_hand) }}</td>
            <td class="text-end figure">{{ formatMoney(item.average_cost) }}</td>
            <td class="text-end figure">{{ formatMoney(stockValue(item)) }}</td>
            <td>
              <span class="badge-pill" :class="item.is_active === false ? 'badge-pill--muted' : 'badge-pill--green'">
                {{ item.is_active === false ? "Inactive" : "Active" }}
              </span>
            </td>
            <td class="table-actions pe-3">
              <span class="row-action-links">
                <button class="row-action-link" @click="openEdit(item)">Edit</button>
                <router-link
                  class="row-action-link"
                  :to="{ name: 'inventory-movements', params: { itemId: item.id } }"
                >
                  History
                </router-link>
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
          <span class="fw-semibold">Total Stock Value:</span>
          <span class="figure fw-semibold">{{ formatMoney(grandTotal) }}</span>
        </template>
      </PaginationBar>

      <div v-if="!loading && !items.length" class="empty-state">
        <i class="bi bi-box-seam"></i>
        No inventory items yet. Add one to track stock on sales and purchases.
      </div>
      <div v-else-if="!loading && items.length && !filtered.length" class="empty-state">
        <i class="bi bi-search"></i>
        No items match "{{ search }}".
      </div>
    </div>

    <EntityFormModal
      v-model:show="showForm"
      :title="editingId ? 'Edit item' : 'New item'"
      :fields="fields"
      :initial-values="formInitialValues"
      :submitting="submitting"
      :error="formError"
      :submit-label="editingId ? 'Save changes' : 'Add item'"
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
import { formatMoney, formatNumber } from "../utils/format";

const businessStore = useBusinessStore();
const { items, loading, create, update } = useCrudResource("/inventory-items");
const { query: search, filtered } = useTextFilter(items, (i) => [i.sku, i.name]);
const { page, pageSize, pagedItems, totalItems } = usePagination(filtered);

function stockValue(item) {
  return Number(item.quantity_on_hand || 0) * Number(item.average_cost || 0);
}
const grandTotal = computed(() => filtered.value.reduce((sum, item) => sum + stockValue(item), 0));

const createFields = [
  { key: "sku", label: "SKU", required: true, colClass: "col-md-4" },
  { key: "name", label: "Name", required: true, colClass: "col-md-8" },
  { key: "unit_of_measure", label: "Unit", placeholder: "pcs", colClass: "col-md-4" },
  {
    key: "inventory_account_id",
    label: "Inventory account",
    type: "select",
    required: true,
    colClass: "col-md-4",
    options: [],
  },
  {
    key: "cogs_account_id",
    label: "COGS account",
    type: "select",
    required: true,
    colClass: "col-md-4",
    options: [],
  },
];

const editFields = [
  ...createFields,
  {
    key: "is_active",
    type: "checkbox",
    label: "",
    checkLabel: "Active (uncheck to retire this item)",
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
  const options = data.map((a) => ({ value: a.id, label: `${a.code} — ${a.name}` }));
  createFields.find((f) => f.key === "inventory_account_id").options = options;
  createFields.find((f) => f.key === "cogs_account_id").options = options;
}

function openCreate() {
  editingId.value = null;
  fields.value = createFields;
  formInitialValues.value = { inventory_account_id: "", cogs_account_id: "" };
  formError.value = "";
  showForm.value = true;
}

function openEdit(item) {
  editingId.value = item.id;
  fields.value = editFields;
  formInitialValues.value = { ...item, is_active: item.is_active !== false };
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
    formError.value = err.response?.data?.detail || "Could not save item.";
  } finally {
    submitting.value = false;
  }
}

onMounted(loadGlAccounts);
</script>
