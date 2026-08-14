<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import Sidebar from './components/Sidebar.vue'
import Header from './components/Header.vue'

const route = useRoute()
const showLayout = computed(() => !route.meta.hideLayout)
</script>

<template>
  <div class="app">
    <template v-if="showLayout">
      <Sidebar />

      <div class="main-layout">
        <Header />

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
