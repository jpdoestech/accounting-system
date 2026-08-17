<template>
  <div class="col-lg-6">
    <h4>Business Settings</h4>
    <p class="text-muted">
      Configurable values — no code changes needed to adjust these
      (spec Section 2).
    </p>

    <div v-if="loading" class="text-muted">Loading…</div>

    <form v-else @submit.prevent="onSave" class="card p-4">
      <div class="mb-3">
        <label class="form-label">Invoice Number Prefix</label>
        <input v-model="settings.invoice_number_prefix" class="form-control" placeholder="INV-" />
      </div>
      <div class="mb-3">
        <label class="form-label">Default Payment Terms (days)</label>
        <input v-model.number="settings.default_payment_terms_days" type="number" min="0" class="form-control" />
      </div>
      <div class="mb-3">
        <label class="form-label">Decimal Precision</label>
        <input v-model.number="settings.decimal_precision" type="number" min="0" max="6" class="form-control" />
      </div>
      <div class="mb-3">
        <label class="form-label">Default Currency</label>
        <input v-model="settings.default_currency_code" class="form-control" maxlength="3" />
      </div>

      <hr />
      <p class="text-muted small mb-2">Control accounts used when posting sales invoices.</p>
      <div class="mb-3">
        <label class="form-label">Accounts Receivable Account</label>
        <select v-model="settings.ar_account_id" class="form-select">
          <option :value="null">— none —</option>
          <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.code }} — {{ a.name }}</option>
        </select>
      </div>
      <div class="mb-3">
        <label class="form-label">Output VAT Payable Account</label>
        <select v-model="settings.output_vat_account_id" class="form-select">
          <option :value="null">— none —</option>
          <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.code }} — {{ a.name }}</option>
        </select>
      </div>
      <div class="mb-3">
        <label class="form-label">Accounts Payable Account</label>
        <select v-model="settings.ap_account_id" class="form-select">
          <option :value="null">— none —</option>
          <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.code }} — {{ a.name }}</option>
        </select>
      </div>
      <div class="mb-3">
        <label class="form-label">Input VAT Account</label>
        <select v-model="settings.input_vat_account_id" class="form-select">
          <option :value="null">— none —</option>
          <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.code }} — {{ a.name }}</option>
        </select>
      </div>
      <div class="mb-3">
        <label class="form-label">Withholding Tax Payable Account</label>
        <select v-model="settings.withholding_tax_payable_account_id" class="form-select">
          <option :value="null">— none —</option>
          <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.code }} — {{ a.name }}</option>
        </select>
      </div>

      <div v-if="error" class="alert alert-danger py-2 small">{{ error }}</div>
      <div v-if="saved" class="alert alert-success py-2 small">Settings saved.</div>

      <button type="submit" class="btn btn-primary" :disabled="submitting">
        <span v-if="submitting" class="spinner-border spinner-border-sm me-1"></span>
        Save Settings
      </button>
    </form>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import api from "../services/api";

const props = defineProps({ id: { type: String, required: true } });

const settings = reactive({
  invoice_number_prefix: "",
  default_payment_terms_days: 30,
  decimal_precision: 2,
  default_currency_code: "PHP",
  ar_account_id: null,
  output_vat_account_id: null,
  ap_account_id: null,
  input_vat_account_id: null,
  withholding_tax_payable_account_id: null,
});

const accounts = ref([]);
const loading = ref(true);
const submitting = ref(false);
const error = ref("");
const saved = ref(false);

onMounted(async () => {
  try {
    const [settingsRes, accountsRes] = await Promise.all([
      api.get(`/businesses/${props.id}/settings`),
      api.get(`/businesses/${props.id}/accounts`),
    ]);
    Object.assign(settings, settingsRes.data);
    accounts.value = accountsRes.data;
  } catch (err) {
    error.value = "Could not load settings.";
  } finally {
    loading.value = false;
  }
});

async function onSave() {
  error.value = "";
  saved.value = false;
  submitting.value = true;
  try {
    const { data } = await api.patch(`/businesses/${props.id}/settings`, settings);
    Object.assign(settings, data);
    saved.value = true;
  } catch (err) {
    error.value = err.response?.data?.detail || "Could not save settings.";
  } finally {
    submitting.value = false;
  }
}
</script>
