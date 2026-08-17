<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h4 class="mb-0">Customers</h4>
      <button class="btn btn-primary btn-sm" @click="showForm = !showForm">
        <i class="bi bi-plus-lg"></i> New Customer
      </button>
    </div>

    <form v-if="showForm" @submit.prevent="onCreate" class="card p-3 mb-4">
      <div class="row g-2">
        <div class="col-md-4">
          <label class="form-label">Name</label>
          <input v-model="form.name" class="form-control" required />
        </div>
        <div class="col-md-3">
          <label class="form-label">TIN</label>
          <input v-model="form.tin" class="form-control" />
        </div>
        <div class="col-md-3">
          <label class="form-label">Email</label>
          <input v-model="form.email" type="email" class="form-control" />
        </div>
        <div class="col-md-2 d-flex align-items-end">
          <button type="submit" class="btn btn-success w-100" :disabled="submitting">Add</button>
        </div>
        <div class="col-12">
          <label class="form-label">Address</label>
          <input v-model="form.address" class="form-control" />
        </div>
      </div>
      <div v-if="error" class="alert alert-danger py-2 small mt-2 mb-0">{{ error }}</div>
    </form>

    <table class="table table-sm table-hover bg-white">
      <thead>
        <tr>
          <th>Name</th>
          <th>TIN</th>
          <th>Email</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="c in customers" :key="c.id">
          <td>{{ c.name }}</td>
          <td class="text-muted">{{ c.tin || "—" }}</td>
          <td class="text-muted">{{ c.email || "—" }}</td>
        </tr>
        <tr v-if="!customers.length">
          <td colspan="3" class="text-muted text-center py-3">No customers yet.</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from "vue";
import api from "../services/api";
import { useBusinessStore } from "../stores/business";

const businessStore = useBusinessStore();
const customers = ref([]);
const showForm = ref(false);
const submitting = ref(false);
const error = ref("");

const form = reactive({ name: "", tin: "", email: "", address: "" });

async function loadCustomers() {
  if (!businessStore.activeBusinessId) return;
  const { data } = await api.get(`/businesses/${businessStore.activeBusinessId}/customers`);
  customers.value = data;
}

async function onCreate() {
  error.value = "";
  submitting.value = true;
  try {
    await api.post(`/businesses/${businessStore.activeBusinessId}/customers`, form);
    form.name = "";
    form.tin = "";
    form.email = "";
    form.address = "";
    showForm.value = false;
    await loadCustomers();
  } catch (err) {
    error.value = err.response?.data?.detail || "Could not create customer.";
  } finally {
    submitting.value = false;
  }
}

onMounted(loadCustomers);
watch(() => businessStore.activeBusinessId, loadCustomers);
</script>
