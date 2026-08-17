<template>
  <div v-if="businessStore.loading" class="text-muted">Loading businesses…</div>

  <div v-else-if="!businessStore.businesses.length" class="text-center py-5">
    <i class="bi bi-building display-4 text-muted"></i>
    <h5 class="mt-3">No business set up yet</h5>
    <p class="text-muted">Create your first business profile to get started.</p>
    <router-link to="/business/new" class="btn btn-primary">
      <i class="bi bi-plus-lg"></i> Create Business
    </router-link>
  </div>

  <div v-else>
    <h4>{{ businessStore.activeBusiness?.business_name || businessStore.activeBusiness?.registered_name }}</h4>
    <p class="text-muted">
      TIN: {{ businessStore.activeBusiness?.tin || "—" }} ·
      VAT status: {{ businessStore.activeBusiness?.vat_registration_status || "—" }} ·
      Currency: {{ businessStore.activeBusiness?.currency_code }}
    </p>

    <div class="row g-3 mt-2">
      <div class="col-md-3">
        <div class="card text-center p-3">
          <div class="text-muted small">General Ledger</div>
          <div class="fs-5 mt-1">Phase 2</div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card text-center p-3">
          <div class="text-muted small">Sales / A/R</div>
          <div class="fs-5 mt-1">Phase 4</div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card text-center p-3">
          <div class="text-muted small">Purchases / A/P</div>
          <div class="fs-5 mt-1">Phase 5</div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card text-center p-3">
          <div class="text-muted small">BIR Reports</div>
          <div class="fs-5 mt-1">Phase 7</div>
        </div>
      </div>
    </div>

    <router-link :to="`/business/${businessStore.activeBusinessId}/settings`" class="btn btn-outline-secondary btn-sm mt-4">
      <i class="bi bi-gear"></i> Business Settings
    </router-link>
  </div>
</template>

<script setup>
import { useBusinessStore } from "../stores/business";

const businessStore = useBusinessStore();
</script>
