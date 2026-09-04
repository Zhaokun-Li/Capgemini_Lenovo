<script setup>
import { computed, ref } from 'vue'

defineProps({
  open: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close'])
const helpLoading = ref(false)

const getUser = () => {
  try {
    return JSON.parse(localStorage.getItem('user') || 'null')
  } catch {
    return null
  }
}

const user = getUser()

const isAdmin = computed(() => {
  return user?.role?.toLowerCase() === 'admin'
})

const commonMenuItems = [
  {
    name: '数据总览',
    path: '/overview',
    icon: 'grid'
  },
  {
    name: '舆情监控',
    path: '/monitor',
    icon: 'monitor'
  },
  {
    name: '舆情分析',
    path: '/sentiment',
    icon: 'sentiment'
  },
  {
    name: '趋势洞察',
    path: '/trend',
    icon: 'trend'
  }
]

const adminMenuItems = [
  {
    name: '数据导入',
    path: '/admin/import',
    icon: 'import'
  },
  {
    name: '用户管理',
    path: '/admin/users',
    icon: 'users'
  }
]

const waitForChatbotButton = () => new Promise((resolve, reject) => {
  const startedAt = Date.now()
  const timer = window.setInterval(() => {
    const button = document.getElementById('dify-chatbot-bubble-button')

    if (button) {
      window.clearInterval(timer)
      resolve(button)
      return
    }

    if (Date.now() - startedAt > 8000) {
      window.clearInterval(timer)
      reject(new Error('Dify chatbot load timeout'))
    }
  }, 200)
})

const toggleHelpChat = async () => {
  if (helpLoading.value) return

  helpLoading.value = true

  try {
    const chatbotButton = await waitForChatbotButton()
    chatbotButton.click()
    emit('close')
  } catch {
    window.alert('Dify 助手加载失败，请刷新页面后重试')
  } finally {
    helpLoading.value = false
  }
}
</script>

<template>
  <aside class="sidebar" :class="{ 'sidebar-open': open }">
    <div class="sidebar-logo">
      <div class="sidebar-logo-mark">L</div>

      <div class="sidebar-logo-text">
        <strong>LENOVO INSIGHT</strong>
        <span>舆情分析平台</span>
      </div>
    </div>

    <div class="sidebar-title">工作台</div>

    <nav class="sidebar-navigation">
      <RouterLink
        v-for="item in commonMenuItems"
        :key="item.path"
        :to="item.path"
        class="sidebar-item"
        active-class="sidebar-item-active"
        @click="emit('close')"
      >
        <span class="sidebar-icon">
          <svg
            v-if="item.icon === 'grid'"
            viewBox="0 0 24 24"
          >
            <rect
              x="3"
              y="3"
              width="18"
              height="18"
              rx="2"
            />
            <path d="M9 3v18M15 3v18M3 9h18M3 15h18" />
          </svg>

          <svg
            v-else-if="item.icon === 'monitor'"
            viewBox="0 0 24 24"
          >
            <circle cx="12" cy="12" r="8" />
            <circle cx="12" cy="12" r="3" />
            <path d="M12 2v2M12 20v2M2 12h2M20 12h2" />
          </svg>

          <svg
            v-else-if="item.icon === 'sentiment'"
            viewBox="0 0 24 24"
          >
            <circle cx="12" cy="12" r="9" />
            <path d="M8 9h.01M16 9h.01" />
            <path d="M8 15c1 1.5 2.3 2 4 2s3-.5 4-2" />
          </svg>

          <svg
            v-else-if="item.icon === 'trend'"
            viewBox="0 0 24 24"
          >
            <path d="M3 17l6-6 4 4 7-8" />
            <path d="M15 7h5v5" />
          </svg>

          <svg
            v-else-if="item.icon === 'product'"
            viewBox="0 0 24 24"
          >
            <path d="M12 3l8 5-8 5-8-5 8-5z" />
            <path d="M4 8v8l8 5 8-5V8" />
            <path d="M12 13v8" />
          </svg>

          <svg
            v-else-if="item.icon === 'report'"
            viewBox="0 0 24 24"
          >
            <rect
              x="4"
              y="3"
              width="16"
              height="18"
              rx="2"
            />
            <path d="M8 8h8M8 12h8M8 16h5" />
          </svg>
        </span>

        <span class="sidebar-name">
          {{ item.name }}
        </span>
      </RouterLink>

      <template v-if="isAdmin">
        <div class="sidebar-section-title">
          管理员功能
        </div>

        <RouterLink
          v-for="item in adminMenuItems"
          :key="item.path"
          :to="item.path"
          class="sidebar-item"
          active-class="sidebar-item-active"
          @click="emit('close')"
        >
          <span class="sidebar-icon">
            <svg
              v-if="item.icon === 'import'"
              viewBox="0 0 24 24"
            >
              <path d="M12 3v12" />
              <path d="M7 10l5 5 5-5" />
              <path d="M4 20h16" />
            </svg>

            <svg
              v-else-if="item.icon === 'users'"
              viewBox="0 0 24 24"
            >
              <circle cx="9" cy="8" r="3" />
              <circle cx="17" cy="9" r="2" />
              <path d="M3 20c0-4 2-7 6-7s6 3 6 7" />
              <path d="M15 14c3 0 5 2 5 5" />
            </svg>
          </span>

          <span class="sidebar-name">
            {{ item.name }}
          </span>
        </RouterLink>
      </template>
    </nav>

    <div class="sidebar-bottom">
      <div class="service-status">
        <div class="service-title">
          <span class="service-dot"></span>
          <strong>数据服务正常</strong>
        </div>

        <span class="service-update">
          最后更新：刚刚
        </span>

        <div class="service-progress">
          <span></span>
        </div>
      </div>

      <button
        type="button"
        class="sidebar-help"
        aria-label="打开智能帮助助手"
        @click="toggleHelpChat"
      >
        <div class="help-icon">?</div>

        <div class="help-content">
          <strong>需要帮助？</strong>
          <span>{{ helpLoading ? '正在加载助手…' : '打开智能助手' }}</span>
        </div>
      </button>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  position: fixed;
  top: 0;
  bottom: 0;
  left: 0;
  z-index: 1100;
  display: flex;
  width: var(--sidebar-width);
  height: 100vh;
  margin: 0;
  padding: 0;
  flex-direction: column;
  overflow: hidden;
  color: #ffffff;
  background:
    radial-gradient(
      circle at 20% 0%,
      rgba(52, 91, 180, 0.28),
      transparent 36%
    ),
    linear-gradient(180deg, #172c5a 0%, #0d1c3d 100%);
  box-shadow: 4px 0 20px rgba(8, 22, 52, 0.12);
}

.sidebar-logo {
  display: flex;
  align-items: center;
  height: var(--header-height);
  padding: 0 22px;
  flex-shrink: 0;
  gap: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.09);
}

.sidebar-logo-mark {
  display: grid;
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  place-items: center;
  border: 2px solid rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  color: #ffffff;
  font-size: 21px;
  font-weight: 800;
  line-height: 1;
}

.sidebar-logo-text {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 3px;
}

.sidebar-logo-text strong {
  overflow: hidden;
  color: #ffffff;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.7px;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-logo-text span {
  color: rgba(221, 230, 250, 0.65);
  font-size: 11px;
  line-height: 1.3;
}

.sidebar-title {
  padding: 24px 24px 10px;
  color: rgba(204, 217, 245, 0.5);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 1.5px;
}

.sidebar-navigation {
  display: flex;
  min-height: 0;
  padding: 0 14px;
  flex: 1;
  flex-direction: column;
  gap: 5px;
  overflow-x: hidden;
  overflow-y: auto;
}

.sidebar-navigation::-webkit-scrollbar {
  width: 4px;
}

.sidebar-navigation::-webkit-scrollbar-thumb {
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.16);
}

.sidebar-section-title {
  margin: 18px 10px 7px;
  color: rgba(204, 217, 245, 0.5);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 1.5px;
}

.sidebar-item {
  position: relative;
  display: flex;
  min-height: 46px;
  padding: 0 15px;
  align-items: center;
  gap: 13px;
  border-radius: 8px;
  color: rgba(221, 230, 250, 0.72);
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
  transition:
    color 0.2s ease,
    background-color 0.2s ease,
    transform 0.2s ease;
}

.sidebar-item:hover {
  color: #ffffff;
  background: rgba(255, 255, 255, 0.08);
  transform: translateX(2px);
}

.sidebar-item-active {
  color: #ffffff;
  background: linear-gradient(
    90deg,
    rgba(55, 113, 242, 0.88),
    rgba(42, 92, 206, 0.7)
  );
  box-shadow: 0 7px 18px rgba(7, 30, 88, 0.24);
}

.sidebar-item-active::before {
  position: absolute;
  top: 9px;
  bottom: 9px;
  left: 0;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: #8fbcff;
  content: "";
}

.sidebar-icon {
  display: grid;
  width: 21px;
  height: 21px;
  flex-shrink: 0;
  place-items: center;
}

.sidebar-icon svg {
  width: 20px;
  height: 20px;
  overflow: visible;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.sidebar-name {
  overflow: hidden;
  flex: 1;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-bottom {
  display: flex;
  padding: 14px;
  flex-shrink: 0;
  flex-direction: column;
  gap: 12px;
}

.service-status {
  padding: 14px;
  border: 1px solid rgba(153, 185, 255, 0.15);
  border-radius: 10px;
  background: rgba(9, 27, 64, 0.42);
}

.service-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.service-title strong {
  color: rgba(239, 244, 255, 0.9);
  font-size: 12px;
  font-weight: 600;
}

.service-dot {
  width: 7px;
  height: 7px;
  flex-shrink: 0;
  border-radius: 50%;
  background: #35d07f;
  box-shadow: 0 0 0 4px rgba(53, 208, 127, 0.12);
}

.service-update {
  display: block;
  margin-top: 7px;
  color: rgba(198, 212, 240, 0.48);
  font-size: 10px;
}

.service-progress {
  height: 3px;
  margin-top: 11px;
  overflow: hidden;
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.09);
}

.service-progress span {
  display: block;
  width: 82%;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #20c778, #5ce29f);
}

.sidebar-help {
  display: flex;
  width: 100%;
  padding: 11px 12px;
  align-items: center;
  gap: 11px;
  border: 0;
  border-radius: 9px;
  color: rgba(223, 232, 250, 0.74);
  background: transparent;
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition:
    color 0.2s ease,
    background-color 0.2s ease;
}

.sidebar-help:hover {
  color: #ffffff;
  background: rgba(255, 255, 255, 0.07);
}

.help-icon {
  display: grid;
  width: 29px;
  height: 29px;
  flex-shrink: 0;
  place-items: center;
  border: 1px solid rgba(210, 224, 252, 0.32);
  border-radius: 50%;
  font-size: 14px;
  font-weight: 700;
}

.help-content {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 3px;
}

.help-content strong {
  color: inherit;
  font-size: 12px;
  font-weight: 600;
}

.help-content span {
  color: rgba(198, 212, 240, 0.48);
  font-size: 10px;
}

@media (max-width: 900px) {
  .sidebar {
    display: flex;
    width: min(82vw, 286px);
    transform: translateX(-105%);
    transition: transform 0.25s ease;
    will-change: transform;
  }

  .sidebar-open {
    transform: translateX(0);
  }
}

:global(#dify-chatbot-bubble-button) {
  display: none !important;
  background-color: #1c64f2 !important;
}

:global(#dify-chatbot-bubble-window) {
  position: fixed !important;
  top: auto !important;
  right: auto !important;
  bottom: 18px !important;
  left: calc(var(--sidebar-width) + 18px) !important;
  z-index: 9999 !important;
  width: min(24rem, calc(100vw - var(--sidebar-width) - 36px)) !important;
  height: min(40rem, calc(100dvh - 36px)) !important;
  max-width: calc(100vw - var(--sidebar-width) - 36px) !important;
  max-height: calc(100dvh - 36px) !important;
  margin: 0 !important;
  transform: none !important;
}

@media (max-width: 900px) {
  :global(#dify-chatbot-bubble-window) {
    right: 12px !important;
    bottom: 12px !important;
    left: 12px !important;
    width: auto !important;
    height: min(40rem, calc(100dvh - 24px)) !important;
    max-width: none !important;
    max-height: calc(100dvh - 24px) !important;
  }
}

.sidebar-help:focus-visible {
  outline: 2px solid #8fbcff;
  outline-offset: 2px;
}
</style>
