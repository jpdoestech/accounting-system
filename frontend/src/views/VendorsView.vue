<template>
  <div>
    <div class="page-header">
      <div>
        <span class="eyebrow">Purchases · Master data</span>
        <h4 class="mb-0">Vendors</h4>
      </div>
      <button class="btn btn-primary btn-sm" @click="openCreate">
        <i class="bi bi-plus-lg"></i> New vendor
      </button>
    </div>

    <div class="card">
      <table class="table table-hover mb-0">
        <thead>
          <tr>
            <th class="ps-3">Name</th>
            <th>TIN</th>
            <th>VAT status</th>
            <th>Email</th>
            <th class="table-actions pe-3">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="v in pagedItems" :key="v.id">
            <td class="ps-3 fw-medium">{{ v.name }}</td>
            <td class="figure text-muted">{{ v.tin || "—" }}</td>
            <td>
              <span class="badge-pill" :class="v.is_vat_registered ? 'badge-pill--green' : 'badge-pill--muted'">
                {{ v.is_vat_registered ? "VAT-registered" : "Non-VAT" }}
              </span>
            </td>
            <td class="text-muted">{{ v.email || "—" }}</td>
            <td class="table-actions pe-3">
              <span class="row-action-links">
                <button class="row-action-link" @click="openEdit(v)">Edit</button>
                <button class="row-action-link row-action-link--danger" @click="askDelete(v)">Delete</button>
              </span>
            </td>
          </tr>
        </tbody>
      </table>

      <PaginationBar
        v-if="items.length"
        v-model:page="page"
        v-model:page-size="pageSize"
        :total-items="totalItems"
      />

      <div v-if="!loading && !items.length" class="empty-state">
        <i class="bi bi-truck"></i>
        No vendors yet. Add one to start recording purchase bills.
      </div>
    </div>

    <EntityFormModal
      v-model:show="showForm"
      :title="editingId ? 'Edit vendor' : 'New vendor'"
      :fields="fields"
      :initial-values="formInitialValues"
      :submitting="submitting"
      :error="formError"
      :submit-label="editingId ? 'Save changes' : 'Add vendor'"
      @submit="onSubmit"
    />

    <ConfirmDialog
      :show="!!pendingDelete"
      title="Delete vendor"
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
import PaginationBar from "../components/PaginationBar.vue";
import { useCrudResource } from "../composables/useCrudResource";
import { usePagination } from "../composables/usePagination";

const { items, loading, create, update, remove } = useCrudResource("/vendors");
const { page, pageSize, pagedItems, totalItems } = usePagination(items);

const fields = [
  { key: "name", label: "Name", required: true, colClass: "col-md-8" },
  { key: "tin", label: "TIN", colClass: "col-md-4" },
  { key: "email", label: "Email", type: "email", colClass: "col-md-6" },
  { key: "phone", label: "Phone", colClass: "col-md-6" },
  { key: "address", label: "Address", colClass: "col-12" },
  {
    key: "is_vat_registered",
    type: "checkbox",
    label: "",
    checkLabel: "VAT-registered vendor",
    colClass: "col-12",
  },
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
  formInitialValues.value = { is_vat_registered: true };
  formError.value = "";
  showForm.value = true;
}

function openEdit(vendor) {
  editingId.value = vendor.id;
  formInitialValues.value = { ...vendor };
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
    formError.value = err.response?.data?.detail || "Could not save vendor.";
  } finally {
    submitting.value = false;
  }
}

function askDelete(vendor) {
  pendingDelete.value = vendor;
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
