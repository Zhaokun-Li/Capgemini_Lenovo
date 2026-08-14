export const userRoutes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../../../../../../Desktop/user-system/user-system/Frontend/src/views/login.vue'),
    meta: { guestOnly: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../../../../../../Desktop/user-system/user-system/Frontend/src/views/register.vue'),
    meta: { guestOnly: true }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('../../../../../../Desktop/user-system/user-system/Frontend/src/views/profile.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/user-management',
    name: 'UserManagement',
    component: () => import('../../../../../../Desktop/user-system/user-system/Frontend/src/views/user_management.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  }
]

export function installUserGuard(router) {
  router.beforeEach((to) => {
    const token = localStorage.getItem('token')
    let user = null
    try {
      user = JSON.parse(localStorage.getItem('user') || 'null')
    } catch {
      user = null
    }

    if (to.meta.requiresAuth && !token) {
      return { path: '/login', query: { redirect: to.fullPath } }
    }
    if (to.meta.requiresAdmin && user?.role !== 'admin') {
      return '/overview'
    }
    if (to.meta.guestOnly && token) {
      return '/overview'
    }
  })
}

