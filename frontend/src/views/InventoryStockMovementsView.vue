<template>
  <div v-if="item" class="view-scroll-page">
    <div class="page-header">
      <div>
        <span class="eyebrow">Inventory</span>
        <h4 class="mb-0">{{ item.sku }} — {{ item.name }}</h4>
        <p class="text-muted small mb-0">
          On hand: {{ formatNumber(item.quantity_on_hand) }} · Avg. cost: {{ formatMoney(item.average_cost) }} ·
          Stock value: {{ formatMoney(Number(item.quantity_on_hand) * Number(item.average_cost)) }}
        </p>
      </div>
      <div class="d-flex align-items-center gap-2">
        <router-link to="/inventory-items" class="btn btn-outline-secondary btn-sm">
          <i class="bi bi-arrow-left"></i> Back to Inventory
        </router-link>
        <button class="btn btn-primary btn-sm" @click="openAdjust">
          <i class="bi bi-plus-lg"></i> Adjust Stock
        </button>
      </div>
    </div>

    <div v-if="error" class="alert alert-danger py-2 small">{{ error }}</div>

    <div class="card view-scroll-area">
      <div class="table-scroll">
        <table class="table table-hover mb-0">
          <colgroup>
            <col style="width: 12%" />
            <col style="width: 14%" />
            <col style="width: 14%" />
            <col style="width: 13%" />
            <col style="width: 13%" />
            <col style="width: 13%" />
            <col style="width: 14%" />
            <col style="width: 7%" />
          </colgroup>
          <thead>
            <tr>
              <th class="ps-3">Date</th>
              <th>Type</th>
              <th>Reference</th>
              <th class="text-end">Qty</th>
              <th class="text-end">Unit Cost</th>
              <th class="text-end">Total Cost</th>
              <th class="text-end">Balance</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in pagedItems" :key="m.id">
              <td class="ps-3 text-muted small">{{ m.movement_date }}</td>
              <td><span class="badge-pill badge-pill--muted">{{ m.movement_type }}</span></td>
              <td class="text-muted small">{{ m.reference_type || "—" }}</td>
              <td class="text-end figure" :class="Number(m.quantity) < 0 ? 'text-danger' : ''">
                {{ Number(m.quantity) > 0 ? "+" : "" }}{{ formatNumber(m.quantity) }}
              </td>
              <td class="text-end figure">{{ formatMoney(m.unit_cost) }}</td>
              <td class="text-end figure">{{ formatMoney(m.total_cost) }}</td>
              <td class="text-end figure">
                {{ formatNumber(m.balance_qty_after) }} / {{ formatMoney(m.balance_value_after) }}
              </td>
              <td></td>
            </tr>
            <tr v-if="!movements.length">
              <td colspan="8" class="text-muted text-center py-3">No stock movements yet.</td>
            </tr>
          </tbody>
        </table>
      </div>
      <PaginationBar
        v-if="movements.length"
        v-model:page="page"
        v-model:page-size="pageSize"
        :total-items="totalItems"
      />
    </div>

    <FormModal v-model:show="showForm" title="Adjust Stock" :is-dirty="isDirty">
      <form @submit.prevent="onSubmit">
        <p class="text-muted small">
          Positive quantity records a stock-in (requires a unit cost); negative quantity records a
          stock-out at the item's current average cost.
        </p>
        <div class="mb-2">
          <label class="form-label">Date</label>
          <input v-model="form.movement_date" type="date" class="form-control" required />
        </div>
        <div class="mb-2">
          <label class="form-label">Quantity (+ to increase, − to decrease)</label>
          <input v-model="form.quantity" type="number" step="0.0001" class="form-control" required />
        </div>
        <div class="mb-2" v-if="Number(form.quantity) > 0">
          <label class="form-label">Unit Cost</label>
          <input v-model="form.unit_cost" type="number" step="0.01" class="form-control" required />
        </div>
        <div class="mb-3">
          <label class="form-label">Memo</label>
          <input v-model="form.memo" class="form-control" placeholder="e.g. Physical count correction" />
        </div>

        <div v-if="formError" class="alert alert-danger py-2 small">{{ formError }}</div>
        <div class="d-flex justify-content-end gap-2">
          <button type="button" class="btn btn-outline-secondary" @click="showForm = false">Cancel</button>
          <button type="submit" class="btn btn-primary" :disabled="submitting">
            <span v-if="submitting" class="spinner-border spinner-border-sm me-1"></span>
            Post Adjustment
          </button>
        </div>
      </form>
    </FormModal>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import api from "../services/api";
import { useBusinessStore } from "../stores/business";
import PaginationBar from "../components/PaginationBar.vue";
import FormModal from "../components/FormModal.vue";
import { usePagination } from "../composables/usePagination";
import { formatMoney, formatNumber } from "../utils/format";

const props = defineProps({ itemId: String });
const businessStore = useBusinessStore();

const item = ref(null);
const movements = ref([]);
const { page, pageSize, pagedItems, totalItems } = usePagination(movements);
const error = ref("");

const showForm = ref(false);
const submitting = ref(false);
const formError = ref("");
const pristineSnapshot = ref("");

function blankForm() {
  return { movement_date: new Date().toISOString().slice(0, 10), quantity: "", unit_cost: "", memo: "" };
}
const form = reactive(blankForm());
const isDirty = computed(() => JSON.stringify(form) !== pristineSnapshot.value);

function openAdjust() {
  Object.assign(form, blankForm());
  formError.value = "";
  showForm.value = true;
  pristineSnapshot.value = JSON.stringify(form);
}

async function loadAll() {
  error.value = "";
  try {
    const businessId = businessStore.activeBusinessId;
    const [itemsRes, movementsRes] = await Promise.all([
      api.get(`/businesses/${businessId}/inventory-items`),
      api.get(`/businesses/${businessId}/inventory-items/${props.itemId}/movements`),
    ]);
    item.value = itemsRes.data.find((i) => i.id === props.itemId) || null;
    // Newest first for a normal "history" reading order.
    movements.value = [...movementsRes.data].reverse();
  } catch (err) {
    error.value = err.response?.data?.detail || "Could not load stock history.";
  }
}

async function onSubmit() {
  formError.value = "";
  submitting.value = true;
  try {
    await api.post(`/businesses/${businessStore.activeBusinessId}/stock-adjustments`, {
      item_id: props.itemId,
      quantity: form.quantity,
      unit_cost: Number(form.quantity) > 0 ? form.unit_cost : null,
      movement_date: form.movement_date,
      memo: form.memo || null,
    });
    showForm.value = false;
    await loadAll();
  } catch (err) {
    formError.value = err.response?.data?.detail || "Could not post adjustment.";
  } finally {
    submitting.value = false;
  }
}

onMounted(loadAll);
</script>
