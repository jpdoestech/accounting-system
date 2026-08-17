<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h4 class="mb-0">Tax Rules</h4>
      <button class="btn btn-primary btn-sm" @click="showForm = !showForm">
        <i class="bi bi-plus-lg"></i> New Rule
      </button>
    </div>
    <p class="text-muted small">
      Rules are effective-dated — a transaction always uses the rate in force on its own
      date, even if the rate has changed since.
    </p>

    <form v-if="showForm" @submit.prevent="onCreate" class="card p-3 mb-4">
      <div class="row g-2">
        <div class="col-md-3">
          <label class="form-label">Rule Code</label>
          <input v-model="form.rule_code" class="form-control" placeholder="VAT_STANDARD" required />
        </div>
        <div class="col-md-3">
          <label class="form-label">Name</label>
          <input v-model="form.name" class="form-control" required />
        </div>
        <div class="col-md-2">
          <label class="form-label">Type</label>
          <select v-model="form.tax_type" class="form-select" required>
            <option value="">— Select —</option>
            <option>VAT</option>
            <option>Withholding</option>
          </select>
        </div>
        <div class="col-md-2">
          <label class="form-label">Rate %</label>
          <input v-model="form.rate_percent" type="number" step="0.0001" class="form-control" required />
        </div>
        <div class="col-md-2" v-if="form.tax_type === 'Withholding'">
          <label class="form-label">ATC Code</label>
          <input v-model="form.atc_code" class="form-control" placeholder="WC010" />
        </div>
        <div class="col-md-3">
          <label class="form-label">Effective From</label>
          <input v-model="form.effective_from" type="date" class="form-control" required />
        </div>
        <div class="col-md-3">
          <label class="form-label">Effective To (optional)</label>
          <input v-model="form.effective_to" type="date" class="form-control" />
        </div>
        <div class="col-md-4">
          <label class="form-label">Legal Basis (optional)</label>
          <input v-model="form.legal_basis" class="form-control" placeholder="e.g. NIRC Sec. 106" />
        </div>
        <div class="col-md-2 d-flex align-items-end">
          <button type="submit" class="btn btn-success w-100" :disabled="submitting">Add Rule</button>
        </div>
      </div>
      <div v-if="error" class="alert alert-danger py-2 small mt-2 mb-0">{{ error }}</div>
    </form>

    <table class="table table-sm table-hover bg-white">
      <thead>
        <tr>
          <th>Code</th>
          <th>Name</th>
          <th>Type</th>
          <th class="text-end">Rate</th>
          <th>Effective</th>
          <th>Status</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in rules" :key="r.id">
          <td class="text-muted">{{ r.rule_code }}</td>
          <td>{{ r.name }}<span v-if="r.atc_code" class="text-muted small"> ({{ r.atc_code }})</span></td>
          <td><span class="badge text-bg-light">{{ r.tax_type }}</span></td>
          <td class="text-end">{{ r.rate_percent }}%</td>
          <td class="small text-muted">{{ r.effective_from }} – {{ r.effective_to || "present" }}</td>
          <td>
            <span :class="r.status === 'Active' ? 'badge text-bg-success' : 'badge text-bg-secondary'">
              {{ r.status }}
            </span>
          </td>
          <td class="text-end">
            <button
              v-if="r.status === 'Active'"
              class="btn btn-sm btn-outline-secondary"
              @click="onRetire(r.id)"
            >
              Retire
            </button>
          </td>
        </tr>
        <tr v-if="!rules.length">
          <td colspan="7" class="text-muted text-center py-3">No tax rules yet.</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from "vue";
import api from "../services/api";
import { useBusinessStore } from "../stores/business";

const businessStore = useBusinessStore();
const rules = ref([]);
const showForm = ref(false);
const submitting = ref(false);
const error = ref("");

const form = reactive({
  rule_code: "",
  name: "",
  tax_type: "",
  atc_code: "",
  rate_percent: "",
  effective_from: "",
  effective_to: "",
  legal_basis: "",
});

async function loadRules() {
  if (!businessStore.activeBusinessId) return;
  const { data } = await api.get(`/businesses/${businessStore.activeBusinessId}/tax-rules`);
  rules.value = data;
}

async function onCreate() {
  error.value = "";
  submitting.value = true;
  try {
    const payload = { ...form };
    if (!payload.effective_to) delete payload.effective_to;
    if (!payload.atc_code) delete payload.atc_code;
    if (!payload.legal_basis) delete payload.legal_basis;

    await api.post(`/businesses/${businessStore.activeBusinessId}/tax-rules`, payload);
    Object.keys(form).forEach((k) => (form[k] = ""));
    showForm.value = false;
    await loadRules();
  } catch (err) {
    error.value = err.response?.data?.detail || "Could not create tax rule.";
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
