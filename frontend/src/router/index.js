import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "../stores/auth";

const routes = [
  {
    path: "/login",
    name: "login",
    component: () => import("../views/LoginView.vue"),
    meta: { public: true },
  },
  {
    path: "/register",
    name: "register",
    component: () => import("../views/RegisterView.vue"),
    meta: { public: true },
  },
  {
    path: "/",
    component: () => import("../layouts/DefaultLayout.vue"),
    children: [
      {
        path: "",
        name: "dashboard",
        component: () => import("../views/DashboardView.vue"),
      },
      {
        path: "business/new",
        name: "business-new",
        component: () => import("../views/BusinessSetupView.vue"),
      },
      {
        path: "business/:id/settings",
        name: "business-settings",
        component: () => import("../views/BusinessSettingsView.vue"),
        props: true,
      },
      {
        path: "accounts",
        name: "accounts",
        component: () => import("../views/ChartOfAccountsView.vue"),
      },
      {
        path: "fiscal-periods",
        name: "fiscal-periods",
        component: () => import("../views/FiscalPeriodsView.vue"),
      },
      {
        path: "accounts/:businessId/:accountId/ledger",
        name: "account-ledger",
        component: () => import("../views/AccountLedgerView.vue"),
        props: true,
      },
      {
        path: "journal-entries/new",
        name: "journal-entry-new",
        component: () => import("../views/JournalEntryFormView.vue"),
      },
      {
        path: "reports/trial-balance",
        name: "trial-balance",
        component: () => import("../views/TrialBalanceView.vue"),
      },
      {
        path: "tax-rules",
        name: "tax-rules",
        component: () => import("../views/TaxRulesView.vue"),
      },
      {
        path: "customers",
        name: "customers",
        component: () => import("../views/CustomersView.vue"),
      },
      {
        path: "sales-invoices",
        name: "sales-invoices",
        component: () => import("../views/SalesInvoicesView.vue"),
      },
      {
        path: "vendors",
        name: "vendors",
        component: () => import("../views/VendorsView.vue"),
      },
      {
        path: "purchase-bills",
        name: "purchase-bills",
        component: () => import("../views/PurchaseBillsView.vue"),
      },
      {
        path: "bank-accounts",
        name: "bank-accounts",
        component: () => import("../views/BankAccountsView.vue"),
      },
      {
        path: "cash-receipts",
        name: "cash-receipts",
        component: () => import("../views/CashReceiptsView.vue"),
      },
      {
        path: "cash-disbursements",
        name: "cash-disbursements",
        component: () => import("../views/CashDisbursementsView.vue"),
      },
      {
        path: "bir",
        name: "bir-reports",
        component: () => import("../views/BirReportsView.vue"),
      },
      {
        path: "inventory-items",
        name: "inventory-items",
        component: () => import("../views/InventoryItemsView.vue"),
      },
      {
        path: "fixed-assets",
        name: "fixed-assets",
        component: () => import("../views/FixedAssetsView.vue"),
      },
      {
        path: "financial-statements",
        name: "financial-statements",
        component: () => import("../views/FinancialStatementsView.vue"),
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to) => {
  const auth = useAuthStore();
  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: "login" };
  }
  if (to.meta.public && auth.isAuthenticated) {
    return { name: "dashboard" };
  }
  return true;
});

export default router;
