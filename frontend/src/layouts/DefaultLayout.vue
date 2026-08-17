<template>
  <div class="app-shell">
    <aside class="app-sidebar" v-if="businessStore.businesses.length">
      <div class="app-sidebar__brand">
        <i class="bi bi-book"></i>
        <span>PH Accounting</span>
      </div>

      <nav class="pb-4">
        <router-link to="/" class="app-sidebar__link">
          <i class="bi bi-speedometer2"></i> Dashboard
        </router-link>

        <div class="app-sidebar__section">Accounting</div>
        <router-link to="/accounts" class="app-sidebar__link">
          <i class="bi bi-diagram-3"></i> Chart of Accounts
        </router-link>
        <router-link to="/fiscal-periods" class="app-sidebar__link">
          <i class="bi bi-calendar3"></i> Fiscal Periods
        </router-link>
        <router-link to="/journal-entries/new" class="app-sidebar__link">
          <i class="bi bi-pencil-square"></i> New Journal Entry
        </router-link>
        <router-link to="/reports/trial-balance" class="app-sidebar__link">
          <i class="bi bi-clipboard-data"></i> Trial Balance
        </router-link>
        <router-link to="/tax-rules" class="app-sidebar__link">
          <i class="bi bi-percent"></i> Tax Rules
        </router-link>

        <div class="app-sidebar__section">Sales</div>
        <router-link to="/customers" class="app-sidebar__link">
          <i class="bi bi-people"></i> Customers
        </router-link>
        <router-link to="/sales-invoices" class="app-sidebar__link">
          <i class="bi bi-receipt"></i> Sales Invoices
        </router-link>

        <div class="app-sidebar__section">Purchases</div>
        <router-link to="/vendors" class="app-sidebar__link">
          <i class="bi bi-truck"></i> Vendors
        </router-link>
        <router-link to="/purchase-bills" class="app-sidebar__link">
          <i class="bi bi-file-earmark-text"></i> Purchase Bills
        </router-link>

        <div class="app-sidebar__section">Banking</div>
        <router-link to="/bank-accounts" class="app-sidebar__link">
          <i class="bi bi-bank"></i> Bank Accounts
        </router-link>
        <router-link to="/cash-receipts" class="app-sidebar__link">
          <i class="bi bi-cash-coin"></i> Cash Receipts
        </router-link>
        <router-link to="/cash-disbursements" class="app-sidebar__link">
          <i class="bi bi-credit-card"></i> Payments
        </router-link>

        <div class="app-sidebar__section">More</div>
        <router-link
          v-if="businessStore.activeBusinessId"
          :to="{ name: 'business-settings', params: { id: businessStore.activeBusinessId } }"
          class="app-sidebar__link"
        >
          <i class="bi bi-gear"></i> Business Settings
        </router-link>
        <router-link to="/bir" class="app-sidebar__link">
          <i class="bi bi-flag"></i> BIR Reports
        </router-link>
        <router-link to="/inventory-items" class="app-sidebar__link">
          <i class="bi bi-box-seam"></i> Inventory
        </router-link>
        <router-link to="/fixed-assets" class="app-sidebar__link">
          <i class="bi bi-building"></i> Fixed Assets
        </router-link>
        <router-link to="/financial-statements" class="app-sidebar__link">
          <i class="bi bi-graph-up"></i> Statements
        </router-link>
      </nav>
    </aside>

    <div class="flex-grow-1 d-flex flex-column">
      <header class="app-topbar" v-if="businessStore.businesses.length">
        <select
          class="form-select form-select-sm w-auto"
          :value="businessStore.activeBusinessId"
          @change="onSwitchBusiness"
        >
          <option v-for="b in businessStore.businesses" :key="b.id" :value="b.id">
            {{ b.business_name || b.registered_name }}
          </option>
        </select>

        <router-link to="/business/new" class="btn btn-sm btn-outline-primary">
          <i class="bi bi-plus-lg"></i> New Business
        </router-link>

        <router-link
          v-if="businessStore.activeBusinessId"
          :to="{ name: 'business-settings', params: { id: businessStore.activeBusinessId } }"
          class="btn btn-sm btn-outline-secondary"
        >
          <i class="bi bi-gear"></i> Business Settings
        </router-link>

        <div class="ms-auto d-flex align-items-center gap-2">
          <button class="btn btn-sm btn-outline-secondary" @click="onLogout">
            <i class="bi bi-box-arrow-right"></i> Log out
          </button>
        </div>
      </header>

      <main class="app-main flex-grow-1">
        <router-view />
      </main>
    </div>
  </div>
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
