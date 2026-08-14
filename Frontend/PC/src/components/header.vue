<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getStoredUser, logout } from '../api/auth'

const router = useRouter()
const menuOpen = ref(false)
const user = ref(getStoredUser())
const userMenu = ref(null)

const userName = computed(() => {
  return user.value?.display_name ||
    user.value?.username ||
    '用户'
})

const userRole = computed(() => {
  return user.value?.role === 'admin' ? '管理员' : '普通用户'
})

const toggleMenu = () => {
  menuOpen.value = !menuOpen.value
}

const handleLogout = async () => {
  logout()
  menuOpen.value = false
  await router.replace('/login')
}

const closeMenu = (event) => {
  if (
    userMenu.value &&
    !userMenu.value.contains(event.target)
  ) {
    menuOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', closeMenu)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', closeMenu)
})
</script>

<template>
  <header class="top-header">
    <div class="header-title">舆情监控平台</div>

    <div ref="userMenu" class="user-menu">
      <button
        type="button"
        class="user-button"
        @click.stop="toggleMenu"
      >
        <span class="user-avatar">
          {{ userName.slice(0, 1).toUpperCase() }}
        </span>

        <span class="user-details">
          <strong>{{ userName }}</strong>
          <small>{{ userRole }}</small>
        </span>

        <span class="arrow" :class="{ open: menuOpen }">⌄</span>
      </button>

      <div v-if="menuOpen" class="dropdown-menu">
        <div class="dropdown-user">
          <strong>{{ userName }}</strong>
          <span>{{ user?.email || '' }}</span>
        </div>

        <button
          type="button"
          class="logout-button"
          @click="handleLogout"
        >
          退出登录
        </button>
      </div>
    </div>
  </header>
</template>

<style scoped>
.top-header {
  position: fixed;
  top: 0;
  right: 0;
  left: var(--sidebar-width);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: var(--header-height);
  margin: 0;
  padding: 0 28px;
  background: #ffffff;
  border-bottom: 1px solid #e8edf4;
}

@media (max-width: 900px) {
  .top-header {
    left: 0;
  }

  .user-details {
    display: none;
  }
}

.header-title {
  color: #17233b;
  font-size: 18px;
  font-weight: 700;
}

.user-menu {
  position: relative;
}

.user-button {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
}

.user-button:hover {
  background: #f3f6fa;
}

.user-avatar {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  color: #ffffff;
  background: #2563eb;
  font-weight: 700;
}

.user-details {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  line-height: 1.3;
}

.user-details strong {
  color: #1f2937;
  font-size: 14px;
}

.user-details small {
  color: #8490a3;
  font-size: 12px;
}

.arrow {
  color: #667085;
  transition: transform 0.2s;
}

.arrow.open {
  transform: rotate(180deg);
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  width: 210px;
  padding: 8px;
  border: 1px solid #e5eaf1;
  border-radius: 10px;
  background: #ffffff;
  box-shadow: 0 12px 30px rgba(15, 35, 65, 0.15);
}

.dropdown-user {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border-bottom: 1px solid #edf0f5;
}

.dropdown-user strong {
  color: #1f2937;
  font-size: 14px;
}

.dropdown-user span {
  overflow: hidden;
  color: #8490a3;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.logout-button {
  width: 100%;
  margin-top: 6px;
  padding: 10px 12px;
  border: 0;
  border-radius: 7px;
  color: #d92d20;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.logout-button:hover {
  background: #fef3f2;
}

@media (max-width: 900px) {
  .top-header {
    left: 0;
  }

  .user-details {
    display: none;
  }
}

.user-menu {
  position: relative;
  top: auto;
  right: auto;
  margin: 0;
  align-self: center;
}

.user-button {
  position: static;
  display: flex;
  align-items: center;
  gap: 10px;
  width: auto;
  height: 54px;
  margin: 0;
  padding: 6px 12px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  box-shadow: none;
  cursor: pointer;
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  z-index: 1100;
  width: 210px;
  margin: 0;
}
</style>