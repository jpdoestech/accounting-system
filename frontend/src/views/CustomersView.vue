<template>
  <div>
    <div class="page-header">
      <div>
        <span class="eyebrow">Sales · Master data</span>
        <h4 class="mb-0">Customers</h4>
      </div>
      <button class="btn btn-primary btn-sm" @click="openCreate">
        <i class="bi bi-plus-lg"></i> New customer
      </button>
    </div>

    <div class="card">
      <table class="table table-hover mb-0">
        <thead>
          <tr>
            <th class="ps-3">Name</th>
            <th>TIN</th>
            <th>Email</th>
            <th>Phone</th>
            <th class="table-actions pe-3">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in items" :key="c.id">
            <td class="ps-3 fw-medium">{{ c.name }}</td>
            <td class="figure text-muted">{{ c.tin || "—" }}</td>
            <td class="text-muted">{{ c.email || "—" }}</td>
            <td class="figure text-muted">{{ c.phone || "—" }}</td>
            <td class="table-actions pe-3">
              <button class="icon-btn" title="Edit" @click="openEdit(c)">
                <i class="bi bi-pencil"></i>
              </button>
              <button class="icon-btn icon-btn--danger" title="Delete" @click="askDelete(c)">
                <i class="bi bi-trash"></i>
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="!loading && !items.length" class="empty-state">
        <i class="bi bi-people"></i>
        No customers yet. Add your first one to start invoicing.
      </div>
    </div>

    <EntityFormModal
      v-model:show="showForm"
      :title="editingId ? 'Edit customer' : 'New customer'"
      :fields="fields"
      :initial-values="formInitialValues"
      :submitting="submitting"
      :error="formError"
      :submit-label="editingId ? 'Save changes' : 'Add customer'"
      @submit="onSubmit"
    />

    <ConfirmDialog
      :show="!!pendingDelete"
      title="Delete customer"
      :message="pendingDelete ? `Delete ${pendingDelete.name}? This can't be undone.` : ''"
      :busy="deleting"
      @confirm="confirmDelete"
      @cancel="pendingDelete = null"
    />
  </div>
</template>

<script setup>
import { ref } from "vue";
import EntityFormModal from "../components/EntityFormModal.vue";
import ConfirmDialog from "../components/ConfirmDialog.vue";
import { useCrudResource } from "../composables/useCrudResource";

const { items, loading, create, update, remove } = useCrudResource("/customers");

const fields = [
  { key: "name", label: "Name", required: true, colClass: "col-md-8" },
  { key: "tin", label: "TIN", colClass: "col-md-4" },
  { key: "email", label: "Email", type: "email", colClass: "col-md-6" },
  { key: "phone", label: "Phone", colClass: "col-md-6" },
  { key: "address", label: "Address", colClass: "col-12" },
];

const showForm = ref(false);
const editingId = ref(null);
const submitting = ref(false);
const formError = ref("");
const formInitialValues = ref({});

const pendingDelete = ref(null);
const deleting = ref(false);

function openCreate() {
  editingId.value = null;
  formInitialValues.value = {};
  formError.value = "";
  showForm.value = true;
}

function openEdit(customer) {
  editingId.value = customer.id;
  formInitialValues.value = { ...customer };
  formError.value = "";
  showForm.value = true;
}

async function onSubmit(values) {
  formError.value = "";
  submitting.value = true;
  try {
    if (editingId.value) {
      await update(editingId.value, values);
    } else {
      await create(values);
    }
    showForm.value = false;
  } catch (err) {
    formError.value = err.response?.data?.detail || "Could not save customer.";
  } finally {
    submitting.value = false;
  }
}

function askDelete(customer) {
  pendingDelete.value = customer;
}

async function confirmDelete() {
  if (!pendingDelete.value) return;
  deleting.value = true;
  try {
    await remove(pendingDelete.value.id);
    pendingDelete.value = null;
  } finally {
    deleting.value = false;
  }
}
</script>
