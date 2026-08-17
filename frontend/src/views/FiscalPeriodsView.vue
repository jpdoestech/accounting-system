<template>
  <div>
    <div class="page-header">
      <div>
        <span class="eyebrow">Accounting · Setup</span>
        <h4 class="mb-0">Fiscal Years &amp; Periods</h4>
      </div>
      <button class="btn btn-primary btn-sm" @click="showYearForm = true">
        <i class="bi bi-plus-lg"></i> New Fiscal Year
      </button>
    </div>

    <div class="alert alert-warning py-2 small mb-3" v-if="!loading && !fiscalYears.length">
      <i class="bi bi-exclamation-triangle me-1"></i>
      No fiscal year exists yet for this business. You need at least one, with an <strong>Open</strong>
      period covering today's date, before you can post any journal entry, sales invoice, purchase
      bill, cash receipt, or disbursement.
    </div>

    <div v-for="fy in fiscalYears" :key="fy.id" class="card mb-3">
      <div class="d-flex align-items-center justify-content-between p-3 border-bottom">
        <div>
          <div class="fw-medium">{{ fy.name }}</div>
          <div class="text-muted small">{{ fy.start_date }} – {{ fy.end_date }}</div>
        </div>
        <div class="d-flex align-items-center gap-2">
          <span class="badge-pill" :class="fy.status === 'Open' ? 'badge-pill--green' : 'badge-pill--muted'">
            {{ fy.status }}
          </span>
          <button
            v-if="!periodsFor(fy.id).length"
            class="btn btn-sm btn-outline-primary"
            :disabled="generatingFor === fy.id"
            @click="generateMonthlyPeriods(fy)"
          >
            <span v-if="generatingFor === fy.id" class="spinner-border spinner-border-sm me-1"></span>
            Generate 12 monthly periods
          </button>
          <button class="btn btn-sm btn-outline-secondary" @click="openPeriodForm(fy)">
            <i class="bi bi-plus-lg"></i> Add period
          </button>
        </div>
      </div>

      <table class="table table-hover mb-0" v-if="periodsFor(fy.id).length">
        <thead>
          <tr>
            <th class="ps-3">Period</th>
            <th>Start</th>
            <th>End</th>
            <th>Status</th>
            <th class="table-actions pe-3">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in periodsFor(fy.id)" :key="p.id" :class="{ 'table-active': coversToday(p) }">
            <td class="ps-3">
              {{ p.name }}
              <span v-if="coversToday(p)" class="badge-pill badge-pill--green ms-1">Current</span>
            </td>
            <td class="text-muted">{{ p.start_date }}</td>
            <td class="text-muted">{{ p.end_date }}</td>
            <td>
              <span class="badge-pill" :class="p.status === 'Open' ? 'badge-pill--green' : 'badge-pill--muted'">
                {{ p.status }}
              </span>
            </td>
            <td class="table-actions pe-3">
              <span class="row-action-links" v-if="p.status === 'Open'">
                <button class="row-action-link row-action-link--danger" @click="onClose(p)">Close</button>
              </span>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-else class="empty-state">
        <i class="bi bi-calendar3"></i>
        No periods yet for this fiscal year.
      </div>
    </div>

    <div v-if="!loading && !fiscalYears.length" class="empty-state">
      <i class="bi bi-calendar3"></i>
      Nothing to show yet — create your first fiscal year above.
    </div>

    <EntityFormModal
      v-model:show="showYearForm"
      title="New fiscal year"
      :fields="yearFields"
      :initial-values="yearInitialValues"
      :submitting="submittingYear"
      :error="yearError"
      submit-label="Create fiscal year"
      @submit="onCreateYear"
    />

    <EntityFormModal
      v-model:show="showPeriodForm"
      title="Add accounting period"
      :fields="periodFields"
      :initial-values="periodInitialValues"
      :submitting="submittingPeriod"
      :error="periodError"
      submit-label="Add period"
      @submit="onCreatePeriod"
    />
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import api from "../services/api";
import { useBusinessStore } from "../stores/business";
import EntityFormModal from "../components/EntityFormModal.vue";

const businessStore = useBusinessStore();

const fiscalYears = ref([]);
const periods = ref([]);
const loading = ref(true);
const generatingFor = ref(null);

const today = new Date().toISOString().slice(0, 10);
const currentYear = new Date().getFullYear();

function periodsFor(fiscalYearId) {
  return periods.value
    .filter((p) => p.fiscal_year_id === fiscalYearId)
    .sort((a, b) => a.start_date.localeCompare(b.start_date));
}

function coversToday(period) {
  return period.start_date <= today && period.end_date >= today;
}

async function loadAll() {
  const businessId = businessStore.activeBusinessId;
  if (!businessId) return;
  loading.value = true;
  try {
    const [yearsRes, periodsRes] = await Promise.all([
      api.get(`/businesses/${businessId}/fiscal-years`),
      api.get(`/businesses/${businessId}/periods`),
    ]);
    fiscalYears.value = yearsRes.data;
    periods.value = periodsRes.data;
  } finally {
    loading.value = false;
  }
}

// --- fiscal year creation ---

const showYearForm = ref(false);
const submittingYear = ref(false);
const yearError = ref("");
const yearInitialValues = ref({
  name: `FY${currentYear}`,
  start_date: `${currentYear}-01-01`,
  end_date: `${currentYear}-12-31`,
});

const yearFields = [
  { key: "name", label: "Name", required: true, colClass: "col-12" },
  { key: "start_date", label: "Start date", type: "date", required: true, colClass: "col-6" },
  { key: "end_date", label: "End date", type: "date", required: true, colClass: "col-6" },
];

async function onCreateYear(values) {
  yearError.value = "";
  submittingYear.value = true;
  try {
    await api.post(`/businesses/${businessStore.activeBusinessId}/fiscal-years`, values);
    showYearForm.value = false;
    await loadAll();
  } catch (err) {
    yearError.value = err.response?.data?.detail || "Could not create fiscal year.";
  } finally {
    submittingYear.value = false;
  }
}

// Convenience: create Jan-through-Dec monthly periods in one click instead
// of making the user add all 12 by hand through "Add period".
async function generateMonthlyPeriods(fy) {
  generatingFor.value = fy.id;
  try {
    const start = new Date(fy.start_date + "T00:00:00");
    for (let i = 0; i < 12; i++) {
      const periodStart = new Date(start.getFullYear(), start.getMonth() + i, 1);
      const periodEnd = new Date(start.getFullYear(), start.getMonth() + i + 1, 0);
      const monthName = periodStart.toLocaleString("default", { month: "long", year: "numeric" });
      await api.post(`/businesses/${businessStore.activeBusinessId}/periods`, {
        fiscal_year_id: fy.id,
        name: monthName,
        start_date: periodStart.toISOString().slice(0, 10),
        end_date: periodEnd.toISOString().slice(0, 10),
      });
    }
    await loadAll();
  } finally {
    generatingFor.value = null;
  }
}

// --- manual period creation ---

const showPeriodForm = ref(false);
const submittingPeriod = ref(false);
const periodError = ref("");
const periodInitialValues = ref({});

const periodFields = [
  { key: "name", label: "Period name", required: true, placeholder: "e.g. January 2026", colClass: "col-12" },
  { key: "start_date", label: "Start date", type: "date", required: true, colClass: "col-6" },
  { key: "end_date", label: "End date", type: "date", required: true, colClass: "col-6" },
];

function openPeriodForm(fy) {
  periodInitialValues.value = { fiscal_year_id: fy.id };
  periodError.value = "";
  showPeriodForm.value = true;
}

async function onCreatePeriod(values) {
  periodError.value = "";
  submittingPeriod.value = true;
  try {
    await api.post(`/businesses/${businessStore.activeBusinessId}/periods`, {
      ...values,
      fiscal_year_id: periodInitialValues.value.fiscal_year_id,
    });
    showPeriodForm.value = false;
    await loadAll();
  } catch (err) {
    periodError.value = err.response?.data?.detail || "Could not add period.";
  } finally {
    submittingPeriod.value = false;
  }
}

async function onClose(period) {
  if (!confirm(`Close period "${period.name}"? No more entries can post into it afterward.`)) return;
  await api.patch(`/businesses/${businessStore.activeBusinessId}/periods/${period.id}/close`);
  await loadAll();
}

onMounted(loadAll);
</script>
