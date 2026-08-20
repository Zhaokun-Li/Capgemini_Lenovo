<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import Sidebar from './components/sidebar.vue'
import Header from './components/header.vue'

const route = useRoute()
const showLayout = computed(() => !route.meta.hideLayout)
const sidebarOpen = ref(false)

watch(
  () => route.fullPath,
  () => {
    sidebarOpen.value = false
  }
)
</script>

<template>
  <div class="app">
    <template v-if="showLayout">
      <Sidebar
        :open="sidebarOpen"
        @close="sidebarOpen = false"
      />

      <button
        v-if="sidebarOpen"
        type="button"
        class="sidebar-backdrop"
        aria-label="关闭导航菜单"
        @click="sidebarOpen = false"
      ></button>

      <div class="main-layout">
        <Header @toggle-sidebar="sidebarOpen = !sidebarOpen" />

        <main class="page-content">
          <RouterView v-slot="{ Component, route: currentRoute }">
            <KeepAlive>
              <component
                :is="Component"
                v-if="currentRoute.meta.keepAlive"
                :key="currentRoute.name"
              />
            </KeepAlive>
            <component
              :is="Component"
              v-if="!currentRoute.meta.keepAlive"
              :key="currentRoute.fullPath"
            />
          </RouterView>
        </main>
      </div>
    </template>

    <RouterView v-else />
  </div>
</template>
