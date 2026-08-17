<template>
  <div class="d-flex align-items-center justify-content-center vh-100 bg-light">
    <div class="card shadow-sm" style="width: 380px">
      <div class="card-body p-4">
        <h4 class="card-title mb-1">Create account</h4>
        <p class="text-muted small mb-4">Philippine Accounting System</p>

        <form @submit.prevent="onSubmit">
          <div class="mb-3">
            <label class="form-label">Full name</label>
            <input v-model="fullName" type="text" class="form-control" required />
          </div>
          <div class="mb-3">
            <label class="form-label">Email</label>
            <input v-model="email" type="email" class="form-control" required />
          </div>
          <div class="mb-3">
            <label class="form-label">Password</label>
            <input v-model="password" type="password" class="form-control" minlength="8" required />
          </div>

          <div v-if="error" class="alert alert-danger py-2 small">{{ error }}</div>
          <div v-if="success" class="alert alert-success py-2 small">
            Account created. You can sign in now.
          </div>

          <button type="submit" class="btn btn-primary w-100" :disabled="submitting">
            <span v-if="submitting" class="spinner-border spinner-border-sm me-1"></span>
            Register
          </button>
        </form>

        <p class="text-center small mt-3 mb-0">
          Already have an account? <router-link to="/login">Sign in</router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const fullName = ref("");
const email = ref("");
const password = ref("");
const error = ref("");
const success = ref(false);
const submitting = ref(false);

const router = useRouter();
const authStore = useAuthStore();

async function onSubmit() {
  error.value = "";
  submitting.value = true;
  try {
    await authStore.register(email.value, password.value, fullName.value);
    success.value = true;
    setTimeout(() => router.push({ name: "login" }), 800);
  } catch (err) {
    error.value = err.response?.data?.detail || "Registration failed.";
  } finally {
    submitting.value = false;
  }
}
</script>
