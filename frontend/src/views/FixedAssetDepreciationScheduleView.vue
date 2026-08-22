<template>
  <div v-if="asset" class="view-scroll-page">
    <div class="page-header">
      <div>
        <span class="eyebrow">Fixed Assets</span>
        <h4 class="mb-0">{{ asset.asset_code }} — {{ asset.name }}</h4>
        <p class="text-muted small mb-0">
          Cost: {{ formatMoney(asset.acquisition_cost) }} · Salvage value: {{ formatMoney(asset.salvage_value) }} ·
          Useful life: {{ asset.useful_life_months }} months · Acquired {{ asset.acquisition_date }}
        </p>
      </div>
      <router-link to="/fixed-assets" class="btn btn-outline-secondary btn-sm">
        <i class="bi bi-arrow-left"></i> Back to Fixed Assets
      </router-link>
    </div>

    <p class="text-muted small">
      The full projected schedule from acquisition to fully depreciated. Rows already posted show
      the actual entry that was recorded; everything else is a projection based on straight-line
      depreciation and will only become real once posted from the Fixed Assets list.
    </p>

    <div class="card view-scroll-area">
      <div class="table-scroll">
        <table class="table table-hover mb-0">
          <colgroup>
            <col style="width: 16%" />
            <col style="width: 20%" />
            <col style="width: 22%" />
            <col style="width: 22%" />
            <col style="width: 20%" />
          </colgroup>
          <thead>
            <tr>
              <th class="ps-3">Period</th>
              <th class="text-end">Depreciation</th>
              <th class="text-end">Accum. Depreciation</th>
              <th class="text-end">Book Value</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in pagedItems" :key="`${row.period_year}-${row.period_month}`">
              <td class="ps-3">{{ monthLabel(row.period_year, row.period_month) }}</td>
              <td class="text-end figure">{{ formatMoney(row.depreciation_amount) }}</td>
              <td class="text-end figure">{{ formatMoney(row.accumulated_depreciation_after) }}</td>
              <td class="text-end figure">{{ formatMoney(row.book_value_after) }}</td>
              <td>
                <span class="badge-pill" :class="row.posted ? 'badge-pill--green' : 'badge-pill--muted'">
                  {{ row.posted ? "Posted" : "Projected" }}
                </span>
              </td>
            </tr>
            <tr v-if="!schedule.length">
              <td colspan="5" class="text-muted text-center py-3">No schedule available.</td>
            </tr>
          </tbody>
        </table>
      </div>
      <PaginationBar
        v-if="schedule.length"
        v-model:page="page"
        v-model:page-size="pageSize"
        :total-items="totalItems"
      />
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import api from "../services/api";
import { useBusinessStore } from "../stores/business";
import PaginationBar from "../components/PaginationBar.vue";
import { usePagination } from "../composables/usePagination";
import { formatMoney } from "../utils/format";

const props = defineProps({ assetId: String });
const businessStore = useBusinessStore();

const asset = ref(null);
const schedule = ref([]);
const { page, pageSize, pagedItems, totalItems } = usePagination(schedule);

const monthNames = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];
function monthLabel(year, month) {
  return `${monthNames[month - 1]} ${year}`;
}

async function loadAll() {
  const businessId = businessStore.activeBusinessId;
  const [assetsRes, scheduleRes, entriesRes] = await Promise.all([
    api.get(`/businesses/${businessId}/fixed-assets`),
    api.get(`/businesses/${businessId}/fixed-assets/${props.assetId}/schedule`),
    api.get(`/businesses/${businessId}/fixed-assets/${props.assetId}/depreciation-entries`),
  ]);
  asset.value = assetsRes.data.find((a) => a.id === props.assetId) || null;

  // Mark each projected row as Posted if an actual depreciation entry
  // already exists for that period, so it's obvious what's real vs
  // what's still just a projection.
  const postedPeriods = new Set(entriesRes.data.map((e) => `${e.period_year}-${e.period_month}`));
  schedule.value = scheduleRes.data.map((row) => ({
    ...row,
    posted: postedPeriods.has(`${row.period_year}-${row.period_month}`),
  }));
}

onMounted(loadAll);
</script>
