<template>
  <teleport to="body">
    <div v-if="show" class="modal-backdrop show"></div>
    <div v-if="show" class="modal d-block" tabindex="-1" @click.self="$emit('cancel')">
      <div class="modal-dialog modal-sm">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">{{ title }}</h5>
            <button type="button" class="btn-close" @click="$emit('cancel')"></button>
          </div>
          <div class="modal-body">
            <p class="mb-0">{{ message }}</p>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-outline-secondary" @click="$emit('cancel')">
              Cancel
            </button>
            <button type="button" class="btn btn-danger" :disabled="busy" @click="$emit('confirm')">
              <span v-if="busy" class="spinner-border spinner-border-sm me-1"></span>
              {{ confirmLabel }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
defineProps({
  show: { type: Boolean, default: false },
  title: { type: String, default: "Are you sure?" },
  message: { type: String, default: "This action can't be undone." },
  confirmLabel: { type: String, default: "Delete" },
  busy: { type: Boolean, default: false },
});
defineEmits(["confirm", "cancel"]);
</script>
