<template>
  <div class="col-lg-7">
    <h4>New Business</h4>
    <p class="text-muted">Philippine business profile (Section 11 of the spec).</p>

    <form @submit.prevent="onSubmit" class="card p-4">
      <div class="row g-3">
        <div class="col-md-6">
          <label class="form-label">Registered Name *</label>
          <input v-model="form.registered_name" class="form-control" required />
        </div>
        <div class="col-md-6">
          <label class="form-label">Business Name</label>
          <input v-model="form.business_name" class="form-control" />
        </div>

        <div class="col-md-4">
          <label class="form-label">TIN</label>
          <input v-model="form.tin" class="form-control" placeholder="000-000-000-000" />
        </div>
        <div class="col-md-4">
          <label class="form-label">Branch Code</label>
          <input v-model="form.branch_code" class="form-control" />
        </div>
        <div class="col-md-4">
          <label class="form-label">RDO Code</label>
          <input v-model="form.rdo_code" class="form-control" />
        </div>

        <div class="col-12">
          <label class="form-label">Registered Address</label>
          <input v-model="form.registered_address" class="form-control" />
        </div>
        <div class="col-md-4">
          <label class="form-label">ZIP Code</label>
          <input v-model="form.zip_code" class="form-control" />
        </div>
        <div class="col-md-4">
          <label class="form-label">Telephone</label>
          <input v-model="form.telephone" class="form-control" />
        </div>
        <div class="col-md-4">
          <label class="form-label">Email</label>
          <input v-model="form.email" type="email" class="form-control" />
        </div>

        <div class="col-md-6">
          <label class="form-label">VAT Registration Status</label>
          <select v-model="form.vat_registration_status" class="form-select">
            <option value="">— Select —</option>
            <option>VAT Registered</option>
            <option>Non-VAT</option>
            <option>Exempt</option>
          </select>
        </div>
        <div class="col-md-6">
          <label class="form-label">Taxpayer Type</label>
          <input v-model="form.taxpayer_type" class="form-control" placeholder="e.g. Individual / Corporation" />
        </div>

        <div class="col-md-6">
          <label class="form-label">Currency</label>
          <input v-model="form.currency_code" class="form-control" maxlength="3" />
        </div>
        <div class="col-md-6">
          <label class="form-label">Fiscal Year Start Month</label>
          <input v-model.number="form.fiscal_year_start_month" type="number" min="1" max="12" class="form-control" />
        </div>
      </div>

      <div v-if="error" class="alert alert-danger py-2 small mt-3">{{ error }}</div>

      <button type="submit" class="btn btn-primary mt-4" :disabled="submitting">
        <span v-if="submitting" class="spinner-border spinner-border-sm me-1"></span>
        Create Business
      </button>
    </form>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { useBusinessStore } from "../stores/business";

const router = useRouter();
const businessStore = useBusinessStore();

const form = reactive({
  registered_name: "",
  business_name: "",
  tin: "",
  branch_code: "",
  rdo_code: "",
  registered_address: "",
  zip_code: "",
  telephone: "",
  email: "",
  vat_registration_status: "",
  taxpayer_type: "",
  currency_code: "PHP",
  fiscal_year_start_month: 1,
});

const error = ref("");
const submitting = ref(false);

async function onSubmit() {
  error.value = "";
  submitting.value = true;
  try {
    await businessStore.createBusiness(form);
    router.push({ name: "dashboard" });
  } catch (err) {
    error.value = err.response?.data?.detail || "Could not create business.";
  } finally {
    submitting.value = false;
  }
}
</script>
