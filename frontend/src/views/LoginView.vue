<template>
  <div class="d-flex align-items-center justify-content-center vh-100 bg-light">
    <div class="card shadow-sm" style="width: 380px">
      <div class="card-body p-4">
        <h4 class="card-title mb-1">
          <i class="bi bi-calculator text-primary me-2"></i>Sign in
        </h4>
        <p class="text-muted small mb-4">Philippine Accounting System</p>

        <form @submit.prevent="onSubmit">
          <div class="mb-3">
            <label class="form-label">Email</label>
            <input v-model="email" type="email" class="form-control" required />
          </div>
          <div class="mb-3">
            <label class="form-label">Password</label>
            <input v-model="password" type="password" class="form-control" required />
          </div>

          <div v-if="error" class="alert alert-danger py-2 small">{{ error }}</div>

          <button type="submit" class="btn btn-primary w-100" :disabled="submitting">
            <span v-if="submitting" class="spinner-border spinner-border-sm me-1"></span>
            Sign in
          </button>
        </form>

        <p class="text-center small mt-3 mb-0">
          No account? <router-link to="/register">Register</router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const email = ref("");
const password = ref("");
const error = ref("");
const submitting = ref(false);

const router = useRouter();
const authStore = useAuthStore();

async function onSubmit() {
  error.value = "";
  submitting.value = true;
  try {
    await authStore.login(email.value, password.value);
    router.push({ name: "dashboard" });
  } catch (err) {
    error.value = err.response?.data?.detail || "Login failed. Check your credentials.";
  } finally {
    submitting.value = false;
  }
}
</script>
