<template>
  <teleport to="body">
    <div v-if="show" class="modal-backdrop show"></div>
    <div v-if="show" class="modal d-block" tabindex="-1" @click.self="requestClose">
      <div class="modal-dialog" :class="sizeClass">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ title }}</h5>
            <button type="button" class="btn-close" @click="requestClose"></button>
          </div>
          <div class="modal-body form-modal-body">
            <slot />
          </div>
        </div>
      </div>
    </div>

    <ConfirmDialog
      :show="showDiscardConfirm"
      title="Discard changes?"
      message="You have unsaved changes. Close without saving?"
      confirm-label="Discard"
      @confirm="forceClose"
      @cancel="showDiscardConfirm = false"
    />
  </teleport>
</template>

<script setup>
import { computed, ref } from "vue";
import ConfirmDialog from "./ConfirmDialog.vue";

const props = defineProps({
  show: { type: Boolean, default: false },
  title: { type: String, required: true },
  // When true, closing (X, backdrop click, or a Cancel button that calls
  // requestClose) asks for confirmation first instead of closing right away.
  isDirty: { type: Boolean, default: false },
  size: { type: String, default: "lg" }, // 'md' | 'lg' | 'xl'
});

const emit = defineEmits(["update:show"]);

const showDiscardConfirm = ref(false);
const sizeClass = computed(() => (props.size === "xl" ? "modal-xl" : props.size === "md" ? "" : "modal-lg"));

function requestClose() {
  if (props.isDirty) {
    showDiscardConfirm.value = true;
  } else {
    emit("update:show", false);
  }
}

function forceClose() {
  showDiscardConfirm.value = false;
  emit("update:show", false);
}

defineExpose({ requestClose });
</script>

<style scoped>
.form-modal-body {
  max-height: 70vh;
  overflow-y: auto;
}
</style>
