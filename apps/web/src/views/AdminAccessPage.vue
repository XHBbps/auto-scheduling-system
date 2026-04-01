<template>
  <div class="login-page">
    <AdminAccessBackground />
    <AdminAccessBrand />

    <div class="login-stage">
      <section class="login-hero" aria-label="AutoSchedule 数据流视觉区">
        <div class="login-hero__center"></div>
      </section>

      <AdminAccessLoginPanel
        :username="username"
        :password="password"
        :loading="loading"
        :active-session-summary="activeSessionSummary"
        @update:username="username = $event"
        @update:password="password = $event"
        @submit="handleSubmit"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import AdminAccessBackground from '../components/admin-access/AdminAccessBackground.vue'
import AdminAccessBrand from '../components/admin-access/AdminAccessBrand.vue'
import AdminAccessLoginPanel from '../components/admin-access/AdminAccessLoginPanel.vue'
import { useAdminAccess } from '../composables/useAdminAccess'

const { activeSessionSummary, handleSubmit, loading, password, username } = useAdminAccess()
</script>

<style scoped>
.login-page {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  background:
    radial-gradient(circle at 16% 18%, rgba(124, 215, 141, 0.12), transparent 18%),
    radial-gradient(circle at 78% 16%, rgba(124, 215, 141, 0.06), transparent 20%),
    radial-gradient(circle at 50% 110%, rgba(63, 120, 75, 0.18), transparent 30%),
    linear-gradient(135deg, #020504 0%, #07110d 50%, #030505 100%);
}

.login-stage {
  position: relative;
  z-index: 1;
  width: min(1320px, 100%);
  min-height: 100vh;
  margin: 0 auto;
  display: grid;
  grid-template-columns: minmax(0, 0.94fr) minmax(360px, 420px);
  align-items: center;
  gap: 24px;
  padding: 18px 32px 24px 16px;
  transform: translateX(-42px);
}

.login-hero {
  position: relative;
  min-width: 0;
  min-height: calc(100vh - 42px);
}

.login-hero__center {
  min-height: calc(100vh - 42px);
}

@media (max-width: 1220px) {
  .login-stage {
    grid-template-columns: 1fr;
    gap: 14px;
    padding: 20px 20px 28px 16px;
    transform: none;
  }

  .login-hero {
    min-height: 360px;
  }

  .login-hero__center {
    min-height: 360px;
  }
}

@media (max-width: 720px) {
  .login-stage {
    padding: 16px 14px 20px 12px;
  }

  .login-hero {
    min-height: 260px;
  }

  .login-hero__center {
    min-height: 260px;
  }
}
</style>
