<template>
  <header class="login-brand">
    <div class="login-brand__badge" aria-hidden="true">
      <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="loginBrandFill" x1="8" y1="5" x2="31" y2="35" gradientUnits="userSpaceOnUse">
            <stop stop-color="#9AF1A8" />
            <stop offset="1" stop-color="#78D789" />
          </linearGradient>
        </defs>
        <rect x="4.5" y="4.5" width="31" height="31" rx="8.6" fill="url(#loginBrandFill)" />
        <rect x="10.2" y="10.1" width="8.2" height="8.2" rx="2.6" fill="#152219" />
        <rect x="21.6" y="10.1" width="8.2" height="8.2" rx="2.6" fill="#72BC80" />
        <rect x="10.2" y="21.5" width="8.2" height="8.2" rx="2.6" fill="#72BC80" />
        <rect x="21.6" y="21.5" width="8.2" height="8.2" rx="2.6" fill="#152219" />
      </svg>
    </div>
    <div class="login-brand__text">
      <div class="login-brand__name">AutoSchedule</div>
      <div class="login-brand__meta">排产管理系统</div>
    </div>
  </header>
</template>

<style scoped>
.login-brand {
  position: absolute;
  top: 12px;
  left: 16px;
  z-index: 6;
  display: inline-flex;
  align-items: center;
  gap: 16px;
}

.login-brand__badge {
  width: 56px;
  height: 56px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  filter: drop-shadow(0 14px 28px rgba(120, 215, 137, 0.2));
}

.login-brand__badge svg {
  width: 100%;
  height: 100%;
  display: block;
}

.login-brand__text {
  display: grid;
  gap: 6px;
}

.login-brand__name {
  color: #ffffff;
  font-size: clamp(28px, 2.5vw, 38px);
  font-weight: 900;
  line-height: 1;
  letter-spacing: -0.05em;
}

.login-brand__meta {
  color: rgba(194, 202, 197, 0.54);
  font-size: 12px;
  line-height: 1;
  letter-spacing: 0.08em;
}

@media (max-width: 1220px) {
  .login-brand {
    top: 12px;
    left: 14px;
  }
}

@media (max-width: 720px) {
  .login-brand {
    top: 10px;
    left: 12px;
  }

  .login-brand__badge {
    width: 48px;
    height: 48px;
  }

  .login-brand__name {
    font-size: 26px;
  }

  .login-brand__meta {
    font-size: 11px;
  }
}
</style>
