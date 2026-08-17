<template>
  <div class="row g-4">
    <div class="col-lg-7">
      <h4>Sales Invoices</h4>
      <div v-if="postError" class="alert alert-danger py-2 small">{{ postError }}</div>
      <table class="table table-sm table-hover bg-white">
        <thead>
          <tr>
            <th>No.</th>
            <th>Date</th>
            <th>Total</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="inv in invoices" :key="inv.id">
            <td>{{ inv.invoice_number }}</td>
            <td class="text-muted small">{{ inv.invoice_date }}</td>
            <td class="text-end">{{ inv.grand_total }}</td>
            <td>
              <span :class="inv.status === 'Posted' ? 'badge text-bg-success' : 'badge text-bg-secondary'">
                {{ inv.status }}
              </span>
            </td>
            <td class="text-end">
              <button
                v-if="inv.status === 'Draft'"
                class="btn btn-sm btn-outline-primary"
                :disabled="postingId === inv.id"
                @click="onPost(inv.id)"
              >
                <span v-if="postingId === inv.id" class="spinner-border spinner-border-sm me-1"></span>
                Post
              </button>
            </td>
          </tr>
          <tr v-if="!invoices.length">
            <td colspan="5" class="text-muted text-center py-3">No invoices yet.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="col-lg-5">
      <h4>New Invoice</h4>
      <form @submit.prevent="onCreate" class="card p-3">
        <div class="mb-2">
          <label class="form-label">Customer</label>
          <select v-model="form.customer_id" class="form-select" required>
            <option value="">— Select —</option>
            <option v-for="c in customers" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </div>
        <div class="row g-2 mb-2">
          <div class="col-6">
            <label class="form-label">Invoice No.</label>
            <input v-model="form.invoice_number" class="form-control" required />
          </div>
          <div class="col-6">
            <label class="form-label">Date</label>
            <input v-model="form.invoice_date" type="date" class="form-control" required />
          </div>
        </div>

        <hr />
        <div v-for="(line, i) in lines" :key="i" class="mb-2 border rounded p-2">
          <input v-model="line.description" class="form-control form-control-sm mb-1" placeholder="Description" required />
          <select v-model="line.revenue_account_id" class="form-select form-select-sm mb-1" required>
            <option value="">— revenue account —</option>
            <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.code }} — {{ a.name }}</option>
          </select>
          <select v-model="line.item_id" class="form-select form-select-sm mb-1">
            <option value="">— not an inventory item —</option>
            <option v-for="it in items" :key="it.id" :value="it.id">{{ it.sku }} — {{ it.name }} ({{ it.quantity_on_hand }} on hand)</option>
          </select>
          <div class="row g-1">
            <div class="col-4">
              <input v-model="line.quantity" type="number" step="0.01" class="form-control form-control-sm" placeholder="Qty" />
            </div>
            <div class="col-4">
              <input v-model="line.unit_price" type="number" step="0.01" class="form-control form-control-sm" placeholder="Unit price" required />
            </div>
            <div class="col-4">
              <select v-model="line.tax_rule_code" class="form-select form-select-sm">
                <option value="">No tax</option>
                <option v-for="r in taxRules" :key="r.rule_code" :value="r.rule_code">{{ r.rule_code }}</option>
              </select>
            </div>
          </div>
        </div>
        <button type="button" class="btn btn-sm btn-outline-secondary mb-3" @click="addLine">
          <i class="bi bi-plus"></i> Add line
        </button>

        <div v-if="error" class="alert alert-danger py-2 small">{{ error }}</div>
        <button type="submit" class="btn btn-primary" :disabled="submitting">
          <span v-if="submitting" class="spinner-border spinner-border-sm me-1"></span>
          Create Draft
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import api from "../services/api";
import { useBusinessStore } from "../stores/business";

const businessStore = useBusinessStore();
const invoices = ref([]);
const customers = ref([]);
const accounts = ref([]);
const taxRules = ref([]);
const items = ref([]);
const error = ref("");
const submitting = ref(false);
const postError = ref("");
const postingId = ref(null);

const form = reactive({
  customer_id: "",
  invoice_number: "",
  invoice_date: new Date().toISOString().slice(0, 10),
});

const lines = ref([{ description: "", revenue_account_id: "", quantity: "1", unit_price: "", tax_rule_code: "", item_id: "" }]);

function addLine() {
  lines.value.push({ description: "", revenue_account_id: "", quantity: "1", unit_price: "", tax_rule_code: "", item_id: "" });
}

async function loadAll() {
  const businessId = businessStore.activeBusinessId;
  if (!businessId) return;
  const [invRes, custRes, acctRes, taxRes, itemsRes] = await Promise.all([
    api.get(`/businesses/${businessId}/sales-invoices`),
    api.get(`/businesses/${businessId}/customers`),
    api.get(`/businesses/${businessId}/accounts`),
    api.get(`/businesses/${businessId}/tax-rules`),
    api.get(`/businesses/${businessId}/inventory-items`),
  ]);
  invoices.value = invRes.data;
  customers.value = custRes.data;
  accounts.value = acctRes.data;
  taxRules.value = taxRes.data.filter((r) => r.status === "Active");
  items.value = itemsRes.data;
}

async function onCreate() {
  error.value = "";
  submitting.value = true;
  try {
    await api.post(`/businesses/${businessStore.activeBusinessId}/sales-invoices`, {
      ...form,
      lines: lines.value
        .filter((l) => l.revenue_account_id && l.unit_price)
        .map((l) => ({ ...l, tax_rule_code: l.tax_rule_code || null, item_id: l.item_id || null })),
    });
    lines.value = [{ description: "", revenue_account_id: "", quantity: "1", unit_price: "", tax_rule_code: "", item_id: "" }];
    form.invoice_number = "";
    await loadAll();
  } catch (err) {
    error.value = err.response?.data?.detail || "Could not create invoice.";
  } finally {
    submitting.value = false;
  }
}

async function onPost(invoiceId) {
  postError.value = "";
  postingId.value = invoiceId;
  try {
    await api.post(`/businesses/${businessStore.activeBusinessId}/sales-invoices/${invoiceId}/post`);
    await loadAll();
  } catch (err) {
    postError.value = err.response?.data?.detail || "Could not post invoice.";
  } finally {
    postingId.value = null;
  }
}

onMounted(loadAll);
</script>
