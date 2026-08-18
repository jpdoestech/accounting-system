<template>
  <div class="pagination-bar">
    <div class="text-muted small">
      <template v-if="totalItems">Showing {{ from }}–{{ to }} of {{ totalItems }}</template>
      <template v-else>No rows</template>
    </div>

    <div class="d-flex align-items-center gap-2">
      <label class="text-muted small mb-0">Rows per page</label>
      <select class="form-select form-select-sm w-auto" :value="selectValue" @change="onSelectChange">
        <option v-for="opt in pageSizeOptions" :key="opt" :value="opt">{{ opt }}</option>
        <option value="custom">Custom…</option>
      </select>
      <input
        v-if="isCustom"
        type="number"
        min="1"
        class="form-control form-control-sm"
        style="width: 90px"
        v-model.number="customDraft"
        placeholder="e.g. 250"
        @keyup.enter="applyCustom"
        @blur="applyCustom"
      />

      <div class="btn-group btn-group-sm ms-1">
        <button
          type="button"
          class="btn btn-outline-secondary"
          :disabled="page <= 1"
          @click="$emit('update:page', page - 1)"
        >
          <i class="bi bi-chevron-left"></i>
        </button>
        <span class="btn btn-outline-secondary disabled px-2">Page {{ page }} of {{ totalPages }}</span>
        <button
          type="button"
          class="btn btn-outline-secondary"
          :disabled="page >= totalPages"
          @click="$emit('update:page', page + 1)"
        >
          <i class="bi bi-chevron-right"></i>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { PAGE_SIZE_OPTIONS } from "../composables/usePagination";

const props = defineProps({
  page: { type: Number, required: true },
  pageSize: { type: Number, required: true },
  totalItems: { type: Number, required: true },
  pageSizeOptions: { type: Array, default: () => PAGE_SIZE_OPTIONS },
});

const emit = defineEmits(["update:page", "update:pageSize"]);

const totalPages = computed(() => Math.max(1, Math.ceil(props.totalItems / props.pageSize)));
const from = computed(() => (props.totalItems === 0 ? 0 : (props.page - 1) * props.pageSize + 1));
const to = computed(() => Math.min(props.page * props.pageSize, props.totalItems));

const isCustom = computed(() => !props.pageSizeOptions.includes(props.pageSize));
const selectValue = computed(() => (isCustom.value ? "custom" : props.pageSize));
const customDraft = ref(isCustom.value ? props.pageSize : "");

function onSelectChange(event) {
  const raw = event.target.value;
  if (raw === "custom") {
    customDraft.value = props.pageSize;
    return;
  }
  emit("update:pageSize", Number(raw));
}

function applyCustom() {
  const n = Number(customDraft.value);
  if (n > 0) emit("update:pageSize", n);
}
</script>

<style scoped>
.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.6rem;
  padding: 0.55rem 0.9rem;
  border-top: 1px solid var(--border);
  background: #fafbfc;
}
</style>
