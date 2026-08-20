<template>
  <div class="view-root">
    <div class="page-header">
      <div>
        <span class="eyebrow">Accounting · Master data</span>
        <h4 class="mb-0">Tax Rules</h4>
      </div>
      <div class="d-flex align-items-center gap-2">
        <div class="search-box">
          <i class="bi bi-search"></i>
          <input v-model="search" type="text" class="form-control form-control-sm" placeholder="Search code, name…" />
        </div>
        <button class="btn btn-primary btn-sm" @click="openCreate">
          <i class="bi bi-plus-lg"></i> New rule
        </button>
      </div>
    </div>
    <p class="text-muted small">
      Rules are effective-dated — a transaction always uses the rate in force on its own date, even
      if the rate has changed since. Rule code, type, and start date are locked once created since
      invoice/bill lines reference a rule by its code and date range.
    </p>

    <div class="card view-scroll-area">
      <div class="table-scroll">
        <table class="table table-hover mb-0 data-grid data-grid--tax-rules">
        <colgroup>
          <col style="width: 13%" />
          <col style="width: 25%" />
          <col style="width: 12%" />
          <col style="width: 10%" />
          <col style="width: 18%" />
          <col style="width: 10%" />
          <col style="width: 12%" />
        </colgroup>
        <thead>
          <tr>
            <th class="ps-3">Code</th>
            <th>Name</th>
            <th>Type</th>
            <th class="text-end">Rate</th>
            <th>Effective</th>
            <th>Status</th>
            <th class="table-actions pe-3">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in pagedItems" :key="r.id">
            <td class="ps-3 figure text-muted">{{ r.rule_code }}</td>
            <td class="fw-medium">
              {{ r.name }}
              <span v-if="r.atc_code" class="text-muted small">({{ r.atc_code }})</span>
            </td>
            <td><span class="badge-pill badge-pill--muted">{{ r.tax_type }}</span></td>
            <td class="text-end figure">{{ r.rate_percent }}%</td>
            <td class="small text-muted">{{ r.effective_from }} – {{ r.effective_to || "present" }}</td>
            <td>
              <span class="badge-pill" :class="r.status === 'Active' ? 'badge-pill--green' : 'badge-pill--muted'">
                {{ r.status }}
              </span>
            </td>
            <td class="table-actions pe-3">
              <span class="row-action-links">
                <button class="row-action-link" @click="openEdit(r)">Edit</button>
                <button
                  v-if="r.status === 'Active'"
                  class="row-action-link row-action-link--danger"
                  @click="onRetire(r.id)"
                >
                  Retire
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
      />

      <div v-if="!loading && !rules.length" class="empty-state">
        <i class="bi bi-percent"></i>
        No tax rules yet. Add one to apply VAT or withholding tax to invoices and bills.
      </div>
      <div v-else-if="!loading && rules.length && !filtered.length" class="empty-state">
        <i class="bi bi-search"></i>
        No rules match "{{ search }}".
      </div>
    </div>

    <EntityFormModal
      v-model:show="showForm"
      :title="editingId ? 'Edit tax rule' : 'New tax rule'"
      :fields="fields"
      :initial-values="formInitialValues"
      :submitting="submitting"
      :error="formError"
      :submit-label="editingId ? 'Save changes' : 'Add rule'"
      @submit="onSubmit"
    />
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from "vue";
import api from "../services/api";
import { useBusinessStore } from "../stores/business";
import EntityFormModal from "../components/EntityFormModal.vue";
import PaginationBar from "../components/PaginationBar.vue";
import { usePagination } from "../composables/usePagination";
import { useTextFilter } from "../composables/useTextFilter";

const businessStore = useBusinessStore();
const rules = ref([]);
const loading = ref(true);
const { query: search, filtered } = useTextFilter(rules, (r) => [r.rule_code, r.name, r.atc_code, r.tax_type]);
const { page, pageSize, pagedItems, totalItems } = usePagination(filtered);

const showForm = ref(false);
const editingId = ref(null);
const submitting = ref(false);
const formError = ref("");
const formInitialValues = ref({});

const taxTypeOptions = [
  { value: "VAT", label: "VAT" },
  { value: "Withholding", label: "Withholding" },
];

// rule_code, tax_type, and effective_from are only settable at
// creation -- the backend locks them on edit since invoice/bill lines
// reference a rule by its code, and the effective date range is what
// makes a rule the correct one for a transaction's date.
const createFields = [
  { key: "rule_code", label: "Rule code", required: true, placeholder: "VAT_STANDARD", colClass: "col-md-4" },
  { key: "name", label: "Name", required: true, colClass: "col-md-8" },
  { key: "tax_type", label: "Type", type: "select", required: true, colClass: "col-md-4", options: taxTypeOptions },
  { key: "rate_percent", label: "Rate %", type: "number", required: true, colClass: "col-md-4" },
  { key: "atc_code", label: "ATC code (withholding)", placeholder: "WC010", colClass: "col-md-4" },
  { key: "effective_from", label: "Effective from", type: "date", required: true, colClass: "col-md-6" },
  { key: "effective_to", label: "Effective to (optional)", type: "date", colClass: "col-md-6" },
  { key: "legal_basis", label: "Legal basis (optional)", placeholder: "e.g. NIRC Sec. 106", colClass: "col-12" },
];

const editFields = [
  { key: "name", label: "Name", required: true, colClass: "col-md-8" },
  { key: "atc_code", label: "ATC code (withholding)", colClass: "col-md-4" },
  { key: "rate_percent", label: "Rate %", type: "number", required: true, colClass: "col-md-4" },
  { key: "effective_to", label: "Effective to (optional)", type: "date", colClass: "col-md-8" },
  { key: "legal_basis", label: "Legal basis (optional)", colClass: "col-12" },
  { key: "source_reference", label: "Source reference (optional)", colClass: "col-12" },
];

const fields = ref(createFields);

async function loadRules() {
  if (!businessStore.activeBusinessId) {
    rules.value = [];
    return;
  }
  loading.value = true;
  try {
    const { data } = await api.get(`/businesses/${businessStore.activeBusinessId}/tax-rules`);
    rules.value = data;
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editingId.value = null;
  fields.value = createFields;
  formInitialValues.value = { tax_type: "", effective_from: new Date().toISOString().slice(0, 10) };
  formError.value = "";
  showForm.value = true;
}

function openEdit(rule) {
  editingId.value = rule.id;
  fields.value = editFields;
  formInitialValues.value = { ...rule };
  formError.value = "";
  showForm.value = true;
}

async function onSubmit(values) {
  formError.value = "";
  submitting.value = true;
  try {
    const businessId = businessStore.activeBusinessId;
    if (editingId.value) {
      await api.put(`/businesses/${businessId}/tax-rules/${editingId.value}`, values);
    } else {
      const payload = { ...values };
      if (!payload.effective_to) delete payload.effective_to;
      if (!payload.atc_code) delete payload.atc_code;
      if (!payload.legal_basis) delete payload.legal_basis;
      await api.post(`/businesses/${businessId}/tax-rules`, payload);
    }
    showForm.value = false;
    await loadRules();
  } catch (err) {
    formError.value = err.response?.data?.detail || "Could not save tax rule.";
  } finally {
    submitting.value = false;
  }
}

async function onRetire(ruleId) {
  await api.patch(`/businesses/${businessStore.activeBusinessId}/tax-rules/${ruleId}/retire`);
  await loadRules();
}

onMounted(loadRules);
watch(() => businessStore.activeBusinessId, loadRules);
</script>
