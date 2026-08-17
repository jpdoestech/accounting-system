<template>
  <div class="row g-4">
    <div class="col-lg-7">
      <h4>Purchase Bills</h4>
      <div v-if="postError" class="alert alert-danger py-2 small">{{ postError }}</div>
      <table class="table table-sm table-hover bg-white">
        <thead>
          <tr>
            <th>No.</th>
            <th>Date</th>
            <th>Due to Vendor</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="bill in bills" :key="bill.id">
            <td>{{ bill.bill_number }}</td>
            <td class="text-muted small">{{ bill.bill_date }}</td>
            <td class="text-end">{{ bill.amount_due_to_vendor }}</td>
            <td>
              <span :class="bill.status === 'Posted' ? 'badge text-bg-success' : 'badge text-bg-secondary'">
                {{ bill.status }}
              </span>
            </td>
            <td class="text-end">
              <button
                v-if="bill.status === 'Draft'"
                class="btn btn-sm btn-outline-primary"
                :disabled="postingId === bill.id"
                @click="onPost(bill.id)"
              >
                <span v-if="postingId === bill.id" class="spinner-border spinner-border-sm me-1"></span>
                Post
              </button>
            </td>
          </tr>
          <tr v-if="!bills.length">
            <td colspan="5" class="text-muted text-center py-3">No bills yet.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="col-lg-5">
      <h4>New Bill</h4>
      <form @submit.prevent="onCreate" class="card p-3">
        <div class="mb-2">
          <label class="form-label">Vendor</label>
          <select v-model="form.vendor_id" class="form-select" required>
            <option value="">— Select —</option>
            <option v-for="v in vendors" :key="v.id" :value="v.id">{{ v.name }}</option>
          </select>
        </div>
        <div class="row g-2 mb-2">
          <div class="col-6">
            <label class="form-label">Bill No.</label>
            <input v-model="form.bill_number" class="form-control" required />
          </div>
          <div class="col-6">
            <label class="form-label">Date</label>
            <input v-model="form.bill_date" type="date" class="form-control" required />
          </div>
        </div>

        <hr />
        <div v-for="(line, i) in lines" :key="i" class="mb-2 border rounded p-2">
          <input v-model="line.description" class="form-control form-control-sm mb-1" placeholder="Description" required />
          <select v-model="line.expense_account_id" class="form-select form-select-sm mb-1" required>
            <option value="">— expense account —</option>
            <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.code }} — {{ a.name }}</option>
          </select>
          <select v-model="line.item_id" class="form-select form-select-sm mb-1">
            <option value="">— not an inventory item —</option>
            <option v-for="it in items" :key="it.id" :value="it.id">{{ it.sku }} — {{ it.name }}</option>
          </select>
          <div class="row g-1">
            <div class="col-3">
              <input v-model="line.quantity" type="number" step="0.01" class="form-control form-control-sm" placeholder="Qty" />
            </div>
            <div class="col-3">
              <input v-model="line.unit_price" type="number" step="0.01" class="form-control form-control-sm" placeholder="Unit price" required />
            </div>
            <div class="col-3">
              <select v-model="line.tax_rule_code" class="form-select form-select-sm">
                <option value="">No VAT</option>
                <option v-for="r in vatRules" :key="r.rule_code" :value="r.rule_code">{{ r.rule_code }}</option>
              </select>
            </div>
            <div class="col-3">
              <select v-model="line.withholding_tax_rule_code" class="form-select form-select-sm">
                <option value="">No W/T</option>
                <option v-for="r in withholdingRules" :key="r.rule_code" :value="r.rule_code">{{ r.rule_code }}</option>
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
import { computed, onMounted, reactive, ref } from "vue";
import api from "../services/api";
import { useBusinessStore } from "../stores/business";

const businessStore = useBusinessStore();
const bills = ref([]);
const vendors = ref([]);
const accounts = ref([]);
const taxRules = ref([]);
const items = ref([]);
const error = ref("");
const submitting = ref(false);
const postError = ref("");
const postingId = ref(null);

const vatRules = computed(() => taxRules.value.filter((r) => r.tax_type === "VAT"));
const withholdingRules = computed(() => taxRules.value.filter((r) => r.tax_type === "Withholding"));

const form = reactive({
  vendor_id: "",
  bill_number: "",
  bill_date: new Date().toISOString().slice(0, 10),
});

const lines = ref([
  {
    description: "",
    expense_account_id: "",
    quantity: "1",
    unit_price: "",
    tax_rule_code: "",
    withholding_tax_rule_code: "",
    item_id: "",
  },
]);

function addLine() {
  lines.value.push({
    description: "",
    expense_account_id: "",
    quantity: "1",
    unit_price: "",
    tax_rule_code: "",
    withholding_tax_rule_code: "",
    item_id: "",
  });
}

async function loadAll() {
  const businessId = businessStore.activeBusinessId;
  if (!businessId) return;
  const [billsRes, vendorsRes, acctRes, taxRes, itemsRes] = await Promise.all([
    api.get(`/businesses/${businessId}/purchase-bills`),
    api.get(`/businesses/${businessId}/vendors`),
    api.get(`/businesses/${businessId}/accounts`),
    api.get(`/businesses/${businessId}/tax-rules`),
    api.get(`/businesses/${businessId}/inventory-items`),
  ]);
  bills.value = billsRes.data;
  vendors.value = vendorsRes.data;
  accounts.value = acctRes.data;
  taxRules.value = taxRes.data.filter((r) => r.status === "Active");
  items.value = itemsRes.data;
}

async function onCreate() {
  error.value = "";
  submitting.value = true;
  try {
    await api.post(`/businesses/${businessStore.activeBusinessId}/purchase-bills`, {
      ...form,
      lines: lines.value
        .filter((l) => l.expense_account_id && l.unit_price)
        .map((l) => ({
          ...l,
          tax_rule_code: l.tax_rule_code || null,
          withholding_tax_rule_code: l.withholding_tax_rule_code || null,
          item_id: l.item_id || null,
        })),
    });
    lines.value = [
      {
        description: "",
        expense_account_id: "",
        quantity: "1",
        unit_price: "",
        tax_rule_code: "",
        withholding_tax_rule_code: "",
        item_id: "",
      },
    ];
    form.bill_number = "";
    await loadAll();
  } catch (err) {
    error.value = err.response?.data?.detail || "Could not create bill.";
  } finally {
    submitting.value = false;
  }
}

async function onPost(billId) {
  postError.value = "";
  postingId.value = billId;
  try {
    await api.post(`/businesses/${businessStore.activeBusinessId}/purchase-bills/${billId}/post`);
    await loadAll();
  } catch (err) {
    postError.value = err.response?.data?.detail || "Could not post bill.";
  } finally {
    postingId.value = null;
  }
}

onMounted(loadAll);
</script>
