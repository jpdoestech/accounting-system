<template>
  <teleport to="body">
    <div v-if="show" class="modal-backdrop show"></div>
    <div v-if="show" class="modal d-block" tabindex="-1" @click.self="onCancel">
      <div class="modal-dialog">
        <form class="modal-content" @submit.prevent="onSubmit">
          <div class="modal-header">
            <h5 class="modal-title">{{ title }}</h5>
            <button type="button" class="btn-close" @click="onCancel"></button>
          </div>

          <div class="modal-body">
            <div class="row g-3">
              <div v-for="field in fields" :key="field.key" :class="field.colClass || 'col-12'">
                <label class="form-label">{{ field.label }}</label>

                <select
                  v-if="field.type === 'select'"
                  v-model="form[field.key]"
                  class="form-select"
                  :required="field.required"
                >
                  <option v-for="opt in field.options" :key="opt.value" :value="opt.value">
                    {{ opt.label }}
                  </option>
                </select>

                <div v-else-if="field.type === 'checkbox'" class="form-check mt-2">
                  <input
                    :id="field.key"
                    v-model="form[field.key]"
                    type="checkbox"
                    class="form-check-input"
                  />
                  <label :for="field.key" class="form-check-label">{{ field.checkLabel }}</label>
                </div>

                <input
                  v-else
                  v-model="form[field.key]"
                  :type="field.type || 'text'"
                  class="form-control"
                  :placeholder="field.placeholder"
                  :required="field.required"
                />

                <div v-if="field.hint" class="form-text">{{ field.hint }}</div>
              </div>
            </div>

            <div v-if="error" class="alert alert-danger py-2 small mt-3 mb-0">{{ error }}</div>
          </div>

          <div class="modal-footer">
            <button type="button" class="btn btn-outline-secondary" @click="onCancel">
              Cancel
            </button>
            <button type="submit" class="btn btn-primary" :disabled="submitting">
              <span v-if="submitting" class="spinner-border spinner-border-sm me-1"></span>
              {{ submitLabel }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { reactive, watch } from "vue";

const props = defineProps({
  show: { type: Boolean, default: false },
  title: { type: String, required: true },
  fields: { type: Array, required: true },
  initialValues: { type: Object, default: () => ({}) },
  submitting: { type: Boolean, default: false },
  error: { type: String, default: "" },
  submitLabel: { type: String, default: "Save" },
});

const emit = defineEmits(["update:show", "submit"]);

const form = reactive({});

function resetForm() {
  for (const field of props.fields) {
    form[field.key] = props.initialValues[field.key] ?? (field.type === "checkbox" ? false : "");
  }
}

// Re-seed the form every time the modal is opened, so editing a second
// row never shows stale values from whatever was open before.
watch(
  () => props.show,
  (isOpen) => {
    if (isOpen) resetForm();
  },
  { immediate: true }
);

function onCancel() {
  emit("update:show", false);
}

function onSubmit() {
  emit("submit", { ...form });
}
</script>
