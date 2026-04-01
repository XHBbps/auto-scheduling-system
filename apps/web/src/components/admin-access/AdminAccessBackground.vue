<template>
  <div class="login-page__noise"></div>
  <div class="login-page__grid"></div>
  <div class="login-page__glow login-page__glow--left"></div>
  <div class="login-page__glow login-page__glow--right"></div>

  <div class="login-page__left-visual" aria-hidden="true">
    <div class="datarain-stage">
      <div class="datarain-grid"></div>
      <div class="datarain-haze"></div>

      <div class="datarain-streams">
        <span class="datarain-stream datarain-stream--1"></span>
        <span class="datarain-stream datarain-stream--2"></span>
        <span class="datarain-stream datarain-stream--3"></span>
        <span class="datarain-stream datarain-stream--4"></span>
        <span class="datarain-stream datarain-stream--5"></span>
        <span class="datarain-stream datarain-stream--6"></span>
      </div>

      <div class="datarain-traces">
        <span class="datarain-trace datarain-trace--1"></span>
        <span class="datarain-trace datarain-trace--2"></span>
        <span class="datarain-trace datarain-trace--3"></span>
        <span class="datarain-trace datarain-trace--4"></span>
        <span class="datarain-trace datarain-trace--5"></span>
        <span class="datarain-trace datarain-trace--6"></span>
        <span class="datarain-trace datarain-trace--7"></span>
        <span class="datarain-trace datarain-trace--8"></span>
      </div>

      <div class="datarain-sweep"></div>
      <div class="datarain-fade"></div>
    </div>
  </div>
</template>

<style scoped>
.login-page__noise,
.login-page__grid,
.login-page__glow,
.login-page__left-visual {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.login-page__noise {
  opacity: 0.14;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.018) 1px, transparent 1px);
  background-size: 112px 112px;
  mask-image: radial-gradient(circle at center, black, transparent 90%);
}

.login-page__grid {
  background-image:
    linear-gradient(rgba(128, 223, 146, 0.036) 1px, transparent 1px),
    linear-gradient(90deg, rgba(128, 223, 146, 0.034) 1px, transparent 1px);
  background-size: 64px 64px;
  opacity: 0.22;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.74), transparent 94%);
}

.login-page__glow {
  border-radius: 999px;
  filter: blur(96px);
}

.login-page__glow--left {
  width: 34vw;
  height: 34vw;
  top: -12vw;
  left: -8vw;
  background: rgba(120, 215, 137, 0.16);
}

.login-page__glow--right {
  width: 30vw;
  height: 30vw;
  right: -10vw;
  bottom: -14vw;
  background: rgba(64, 118, 76, 0.16);
}

.datarain-stage {
  position: absolute;
  inset: 0;
  overflow: hidden;
  border-radius: 0 34px 34px 0;
  background: linear-gradient(180deg, rgba(9, 16, 12, 0.52) 0%, rgba(3, 7, 5, 0.12) 100%);
  mask-image: linear-gradient(90deg, rgba(0, 0, 0, 1) 0%, rgba(0, 0, 0, 1) 72%, rgba(0, 0, 0, 0.12) 88%, rgba(0, 0, 0, 0.04) 100%);
}

.datarain-grid,
.datarain-haze,
.datarain-streams,
.datarain-traces,
.datarain-sweep,
.datarain-fade {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.datarain-grid {
  background-image:
    repeating-linear-gradient(90deg, rgba(136, 228, 154, 0.06) 0 1px, transparent 1px 40px),
    linear-gradient(180deg, rgba(136, 228, 154, 0.035), transparent 72%);
  opacity: 0.42;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.9), transparent 100%);
}

.datarain-haze {
  background:
    radial-gradient(circle at 18% 16%, rgba(124, 219, 142, 0.1), transparent 22%),
    radial-gradient(circle at 30% 54%, rgba(107, 190, 124, 0.08), transparent 20%),
    radial-gradient(circle at 46% 34%, rgba(124, 219, 142, 0.06), transparent 24%);
  filter: blur(22px);
  opacity: 0.82;
}

.datarain-stream,
.datarain-trace {
  position: absolute;
  top: -22%;
}

.datarain-stream {
  width: 3px;
  height: 144%;
  border-radius: 999px;
  background: linear-gradient(
    180deg,
    rgba(142, 237, 161, 0) 0%,
    rgba(142, 237, 161, 0.08) 16%,
    rgba(142, 237, 161, 0.32) 42%,
    rgba(142, 237, 161, 0.58) 62%,
    rgba(142, 237, 161, 0.12) 82%,
    rgba(142, 237, 161, 0) 100%
  );
  box-shadow: 0 0 10px rgba(142, 237, 161, 0.18);
  opacity: 0.48;
  animation: datarain-stream-fall 10s linear infinite;
}

.datarain-stream::after {
  content: '';
  position: absolute;
  top: 14%;
  left: 50%;
  width: 14px;
  height: 74px;
  transform: translateX(-50%);
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(160, 245, 177, 0), rgba(160, 245, 177, 0.42), rgba(160, 245, 177, 0));
  filter: blur(8px);
}

.datarain-stream--1 {
  left: 10%;
  animation-duration: 9.5s;
}

.datarain-stream--2 {
  left: 22%;
  width: 5px;
  opacity: 0.6;
  animation-duration: 12s;
  animation-delay: -4s;
}

.datarain-stream--3 {
  left: 36%;
  width: 2px;
  opacity: 0.3;
  animation-duration: 8.5s;
  animation-delay: -2s;
}

.datarain-stream--4 {
  left: 50%;
  width: 4px;
  opacity: 0.26;
  animation-duration: 14s;
  animation-delay: -7s;
}

.datarain-stream--5 {
  left: 64%;
  width: 2px;
  opacity: 0.16;
  animation-duration: 11.5s;
  animation-delay: -3s;
}

.datarain-stream--6 {
  left: 76%;
  width: 1px;
  opacity: 0.1;
  animation-duration: 15s;
  animation-delay: -9s;
}

.datarain-trace {
  width: 1px;
  height: 138%;
  border-radius: 999px;
  background-image: repeating-linear-gradient(
    180deg,
    rgba(150, 240, 167, 0.62) 0 14px,
    rgba(150, 240, 167, 0.08) 14px 22px,
    transparent 22px 40px
  );
  background-size: 100% 180px;
  box-shadow: 0 0 6px rgba(150, 240, 167, 0.16);
  opacity: 0.18;
  animation: datarain-trace-fall 13s linear infinite;
}

.datarain-trace--1 {
  left: 14%;
  animation-duration: 12s;
}

.datarain-trace--2 {
  left: 27%;
  opacity: 0.24;
  animation-duration: 10.5s;
  animation-delay: -1.5s;
}

.datarain-trace--3 {
  left: 33%;
  animation-duration: 15s;
  animation-delay: -4.5s;
}

.datarain-trace--4 {
  left: 42%;
  opacity: 0.14;
  animation-duration: 11.5s;
  animation-delay: -6s;
}

.datarain-trace--5 {
  left: 48%;
  animation-duration: 16.5s;
  animation-delay: -8s;
}

.datarain-trace--6 {
  left: 58%;
  opacity: 0.12;
  animation-duration: 14s;
  animation-delay: -10s;
}

.datarain-trace--7 {
  left: 68%;
  opacity: 0.1;
  animation-duration: 12.8s;
  animation-delay: -5s;
}

.datarain-trace--8 {
  left: 80%;
  opacity: 0.08;
  animation-duration: 17s;
  animation-delay: -12s;
}

.datarain-sweep {
  top: -6%;
  bottom: -6%;
  left: 16%;
  width: 22%;
  border-radius: 999px;
  background: linear-gradient(90deg, transparent, rgba(148, 240, 166, 0.05), rgba(148, 240, 166, 0.12), rgba(148, 240, 166, 0.05), transparent);
  filter: blur(28px);
  opacity: 0.32;
  animation: datarain-sweep-shift 18s ease-in-out infinite;
}

.datarain-fade {
  background:
    linear-gradient(90deg, rgba(2, 5, 4, 0.02), rgba(2, 5, 4, 0.18) 54%, rgba(2, 5, 4, 0.6) 76%, rgba(2, 5, 4, 0.94) 100%),
    linear-gradient(180deg, rgba(2, 5, 4, 0.12), transparent 18%, transparent 82%, rgba(2, 5, 4, 0.22) 100%);
}

@keyframes datarain-stream-fall {
  from {
    transform: translate3d(0, -10%, 0);
    opacity: 0.12;
  }
  18% {
    opacity: 0.44;
  }
  72% {
    opacity: 0.58;
  }
  to {
    transform: translate3d(0, 12%, 0);
    opacity: 0.12;
  }
}

@keyframes datarain-trace-fall {
  from {
    transform: translate3d(0, -12%, 0);
    background-position-y: 0;
    opacity: 0.08;
  }
  16% {
    opacity: 0.22;
  }
  78% {
    opacity: 0.16;
  }
  to {
    transform: translate3d(0, 10%, 0);
    background-position-y: 180px;
    opacity: 0.08;
  }
}

@keyframes datarain-sweep-shift {
  0%,
  100% {
    transform: translateX(-8%);
    opacity: 0.2;
  }
  50% {
    transform: translateX(18%);
    opacity: 0.38;
  }
}

@media (max-width: 1220px) {
  .login-page__left-visual {
    width: 100%;
    height: 360px;
    bottom: auto;
  }

  .datarain-stage {
    position: absolute;
    inset: 0;
    width: auto;
    height: auto;
    margin: 0;
    border-radius: 0 0 30px 30px;
  }

  .datarain-stream--5,
  .datarain-stream--6,
  .datarain-trace--7,
  .datarain-trace--8 {
    display: none;
  }
}

@media (max-width: 720px) {
  .login-page__left-visual {
    height: 260px;
  }

  .datarain-stage {
    border-radius: 0 0 24px 24px;
  }

  .datarain-stream--3,
  .datarain-stream--4,
  .datarain-stream--5,
  .datarain-stream--6,
  .datarain-trace--4,
  .datarain-trace--5,
  .datarain-trace--6,
  .datarain-trace--7,
  .datarain-trace--8,
  .datarain-sweep {
    display: none;
  }
}
</style>
