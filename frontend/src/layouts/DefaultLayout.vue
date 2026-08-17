<template>
  <nav class="navbar navbar-expand-lg navbar-dark bg-dark px-3">
    <span class="navbar-brand">
      <i class="bi bi-calculator me-2"></i>Philippine Accounting System
    </span>

    <div class="navbar-nav flex-row gap-1 ms-4" v-if="businessStore.businesses.length">
      <router-link to="/" class="nav-link px-2">Dashboard</router-link>

      <div class="nav-item dropdown">
        <a class="nav-link dropdown-toggle px-2" href="#" role="button" data-bs-toggle="dropdown">Accounting</a>
        <ul class="dropdown-menu dropdown-menu-dark">
          <li><router-link to="/accounts" class="dropdown-item">Chart of Accounts</router-link></li>
          <li><router-link to="/journal-entries/new" class="dropdown-item">New Journal Entry</router-link></li>
          <li><router-link to="/reports/trial-balance" class="dropdown-item">Trial Balance</router-link></li>
          <li><router-link to="/tax-rules" class="dropdown-item">Tax Rules</router-link></li>
        </ul>
      </div>

      <div class="nav-item dropdown">
        <a class="nav-link dropdown-toggle px-2" href="#" role="button" data-bs-toggle="dropdown">Sales</a>
        <ul class="dropdown-menu dropdown-menu-dark">
          <li><router-link to="/customers" class="dropdown-item">Customers</router-link></li>
          <li><router-link to="/sales-invoices" class="dropdown-item">Sales Invoices</router-link></li>
        </ul>
      </div>

      <div class="nav-item dropdown">
        <a class="nav-link dropdown-toggle px-2" href="#" role="button" data-bs-toggle="dropdown">Purchases</a>
        <ul class="dropdown-menu dropdown-menu-dark">
          <li><router-link to="/vendors" class="dropdown-item">Vendors</router-link></li>
          <li><router-link to="/purchase-bills" class="dropdown-item">Purchase Bills</router-link></li>
        </ul>
      </div>

      <div class="nav-item dropdown">
        <a class="nav-link dropdown-toggle px-2" href="#" role="button" data-bs-toggle="dropdown">Banking</a>
        <ul class="dropdown-menu dropdown-menu-dark">
          <li><router-link to="/bank-accounts" class="dropdown-item">Bank Accounts</router-link></li>
          <li><router-link to="/cash-receipts" class="dropdown-item">Cash Receipts</router-link></li>
          <li><router-link to="/cash-disbursements" class="dropdown-item">Payments</router-link></li>
        </ul>
      </div>

      <router-link to="/bir" class="nav-link px-2">BIR</router-link>
      <router-link to="/inventory-items" class="nav-link px-2">Inventory</router-link>
      <router-link to="/fixed-assets" class="nav-link px-2">Fixed Assets</router-link>
      <router-link to="/financial-statements" class="nav-link px-2">Statements</router-link>
    </div>

    <div class="ms-auto d-flex align-items-center gap-3">
      <select
        v-if="businessStore.businesses.length"
        class="form-select form-select-sm w-auto"
        :value="businessStore.activeBusinessId"
        @change="onSwitchBusiness"
      >
        <option v-for="b in businessStore.businesses" :key="b.id" :value="b.id">
          {{ b.business_name || b.registered_name }}
        </option>
      </select>

      <router-link to="/business/new" class="btn btn-sm btn-outline-light">
        <i class="bi bi-plus-lg"></i> New Business
      </router-link>

      <button class="btn btn-sm btn-outline-light" @click="onLogout">
        <i class="bi bi-box-arrow-right"></i> Log out
      </button>
    </div>
  </nav>

  <main class="container-fluid p-4">
    <router-view />
  </main>
</template>

<script setup>
import { onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { useBusinessStore } from "../stores/business";

const router = useRouter();
const authStore = useAuthStore();
const businessStore = useBusinessStore();

onMounted(() => {
  businessStore.fetchBusinesses();
});

function onSwitchBusiness(event) {
  businessStore.setActiveBusiness(event.target.value);
}

function onLogout() {
  authStore.logout();
  router.push({ name: "login" });
}
</script>
