<template>
  <div class="view-root">
    <div class="page-header">
      <div>
        <span class="eyebrow">Business Settings</span>
        <h4 class="mb-0">Team</h4>
      </div>
      <div class="d-flex align-items-center gap-2">
        <router-link
          :to="{ name: 'business-settings', params: { id: businessId } }"
          class="btn btn-outline-secondary btn-sm"
        >
          <i class="bi bi-arrow-left"></i> Back to Settings
        </router-link>
        <button v-if="isAdmin" class="btn btn-primary btn-sm" @click="openInvite">
          <i class="bi bi-plus-lg"></i> Add teammate
        </button>
      </div>
    </div>

    <p class="text-muted small">
      Anyone added here can access this business fully once logged in. Role only restricts who can
      manage the team itself (Admin) — it doesn't yet limit which screens or actions an Accountant
      or Viewer can use.
    </p>

    <div v-if="error" class="alert alert-danger py-2 small">{{ error }}</div>

    <div class="card view-scroll-area">
      <div class="table-scroll">
        <table class="table table-hover mb-0">
          <thead>
            <tr>
              <th class="ps-3">Email</th>
              <th>Name</th>
              <th>Role</th>
              <th class="table-actions pe-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in members" :key="m.id">
              <td class="ps-3 fw-medium">
                {{ m.email }}
                <span v-if="m.is_self" class="badge-pill badge-pill--muted ms-1">You</span>
              </td>
              <td class="text-muted">{{ m.full_name || "—" }}</td>
              <td>
                <select
                  v-if="isAdmin"
                  class="form-select form-select-sm"
                  style="width: auto"
                  :value="m.role_name"
                  :disabled="changingId === m.id"
                  @change="onChangeRole(m, $event.target.value)"
                >
                  <option v-for="r in roles" :key="r.id" :value="r.name">{{ r.name }}</option>
                </select>
                <span v-else class="badge-pill badge-pill--muted">{{ m.role_name }}</span>
              </td>
              <td class="table-actions pe-3">
                <span v-if="isAdmin && !m.is_self" class="row-action-links">
                  <button class="row-action-link row-action-link--danger" @click="askRemove(m)">
                    Remove
                  </button>
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="!loading && !members.length" class="empty-state">
        <i class="bi bi-people"></i>
        No team members yet.
      </div>
    </div>

    <FormModal v-model:show="showInvite" title="Add teammate" :is-dirty="isDirty">
      <form @submit.prevent="onInvite">
        <p class="text-muted small">
          They need an existing account on this app already — there's no email-invite system yet,
          so if they haven't registered, ask them to sign up first, then add them here.
        </p>
        <div class="mb-2">
          <label class="form-label">Email</label>
          <input v-model="inviteForm.email" type="email" class="form-control" required />
        </div>
        <div class="mb-3">
          <label class="form-label">Role</label>
          <select v-model="inviteForm.role_name" class="form-select">
            <option v-for="r in roles" :key="r.id" :value="r.name">{{ r.name }}</option>
          </select>
        </div>

        <div v-if="inviteError" class="alert alert-danger py-2 small">{{ inviteError }}</div>
        <div class="d-flex justify-content-end gap-2">
          <button type="button" class="btn btn-outline-secondary" @click="showInvite = false">Cancel</button>
          <button type="submit" class="btn btn-primary" :disabled="inviting">
            <span v-if="inviting" class="spinner-border spinner-border-sm me-1"></span>
            Add
          </button>
        </div>
      </form>
    </FormModal>

    <ConfirmDialog
      :show="!!pendingRemove"
      title="Remove teammate"
      :message="pendingRemove ? `Remove ${pendingRemove.email}'s access to this business?` : ''"
      confirm-label="Remove"
      :busy="removing"
      @confirm="confirmRemove"
      @cancel="pendingRemove = null"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import api from "../services/api";
import FormModal from "../components/FormModal.vue";
import ConfirmDialog from "../components/ConfirmDialog.vue";

const props = defineProps({ id: { type: String, required: true } });
const businessId = props.id;

const members = ref([]);
const roles = ref([]);
const loading = ref(true);
const error = ref("");

const isAdmin = computed(() => {
  const me = members.value.find((m) => m.is_self);
  return me?.role_name === "Admin";
});

async function loadAll() {
  error.value = "";
  loading.value = true;
  try {
    const [membersRes, rolesRes] = await Promise.all([
      api.get(`/businesses/${businessId}/users`),
      api.get(`/businesses/${businessId}/roles`),
    ]);
    members.value = membersRes.data;
    roles.value = rolesRes.data;
  } catch (err) {
    error.value = err.response?.data?.detail || "Could not load team.";
  } finally {
    loading.value = false;
  }
}

const showInvite = ref(false);
const inviting = ref(false);
const inviteError = ref("");
const inviteForm = reactive({ email: "", role_name: "Accountant" });
const invitePristine = ref("");
const isDirty = computed(() => JSON.stringify(inviteForm) !== invitePristine.value);

function openInvite() {
  inviteForm.email = "";
  inviteForm.role_name = "Accountant";
  inviteError.value = "";
  showInvite.value = true;
  invitePristine.value = JSON.stringify(inviteForm);
}

async function onInvite() {
  inviteError.value = "";
  inviting.value = true;
  try {
    await api.post(`/businesses/${businessId}/users`, inviteForm);
    showInvite.value = false;
    await loadAll();
  } catch (err) {
    inviteError.value = err.response?.data?.detail || "Could not add teammate.";
  } finally {
    inviting.value = false;
  }
}

const changingId = ref(null);
async function onChangeRole(member, newRole) {
  error.value = "";
  changingId.value = member.id;
  try {
    await api.patch(`/businesses/${businessId}/users/${member.id}`, { role_name: newRole });
    await loadAll();
  } catch (err) {
    error.value = err.response?.data?.detail || "Could not change role.";
  } finally {
    changingId.value = null;
  }
}

const pendingRemove = ref(null);
const removing = ref(false);
function askRemove(member) {
  error.value = "";
  pendingRemove.value = member;
}
async function confirmRemove() {
  if (!pendingRemove.value) return;
  removing.value = true;
  try {
    await api.delete(`/businesses/${businessId}/users/${pendingRemove.value.id}`);
    pendingRemove.value = null;
    await loadAll();
  } catch (err) {
    error.value = err.response?.data?.detail || "Could not remove teammate.";
    pendingRemove.value = null;
  } finally {
    removing.value = false;
  }
}

onMounted(loadAll);
</script>
