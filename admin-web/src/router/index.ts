import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/store/user'
import Layout from '@/components/Layout.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/Login.vue'),
      meta: { public: true }
    },
    {
      path: '/',
      component: Layout,
      redirect: '/dashboard',
      children: [
        {
          path: 'dashboard',
          name: 'Dashboard',
          component: () => import('@/views/Dashboard.vue'),
          meta: { title: '仪表盘' }
        },
        {
          path: 'devices',
          name: 'Devices',
          component: () => import('@/views/Devices.vue'),
          meta: { title: '设备管理' }
        },
        {
          path: 'alerts',
          name: 'Alerts',
          component: () => import('@/views/Alerts.vue'),
          meta: { title: '报警中心' }
        },
        {
          path: 'animals',
          name: 'Animals',
          component: () => import('@/views/Animals.vue'),
          meta: { title: '林麝管理' }
        },
        {
          path: 'data',
          name: 'DataAnalysis',
          component: () => import('@/views/DataAnalysis.vue'),
          meta: { title: '数据分析' }
        },
        {
          path: 'users',
          name: 'Users',
          component: () => import('@/views/Users.vue'),
          meta: { title: '用户管理' }
        },
        {
          path: 'settings',
          name: 'Settings',
          component: () => import('@/views/Settings.vue'),
          meta: { title: '系统设置' }
        }
      ]
    }
  ]
})

router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  
  if (!to.meta.public && !userStore.token) {
    next('/login')
  } else {
    next()
  }
})

export default router
