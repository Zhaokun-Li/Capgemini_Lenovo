import { createRouter, createWebHistory } from 'vue-router'
import MainPage from '../view/main_page.vue'
import SentimentMonitor from '../view/sentiment_monitor.vue'
import PublicOpinionAnalysis from '../view/public_opinion_analysis.vue'
import TrendAnalysis from '../view/trend_analysis.vue'
import Login from '../view/login.vue'
import Register from '../view/register.vue'
import DataImport from '../view/data_import.vue'
import UserManagement from '../view/user_management.vue'

const routes = [
  {
    path: '/',
    name: 'login',
    component: Login,
    meta: { title: '登录', hideLayout: true }
  },
  {
    path: '/register',
    name: 'register',
    component: Register,
    meta: { hideLayout: true, guestOnly: true }
  },
  {
    path: '/overview',
    name: 'overview',
    component: MainPage,
    meta: { title: '数据总览', keepAlive: true }
  },
  {
    path: '/monitor',
    name: 'monitor',
    component: SentimentMonitor,
    meta: { title: '舆情监控', keepAlive: true }
  },
  {
    path: '/sentiment',
    name: 'sentiment',
    component: PublicOpinionAnalysis,
    meta: {
      title: '舆情分析',
      description: '查看正面、中性和负面舆情的分布与变化',
      keepAlive: true
    }
  },
  {
    path: '/trend',
    name: 'trend',
    component: TrendAnalysis,
    meta: {
      title: '趋势洞察',
      description: '分析舆情热度、关键词和话题的发展趋势',
      keepAlive: true
    }
  },
  {
    path: '/admin/import',
    name: 'AdminDataImport',
    component: DataImport,
    meta: { title: '数据导入' }
  },
  {
    path: '/admin/users',
    name: 'UserManagement',
    component: UserManagement,
    meta: { title: '用户管理' }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.afterEach(to => {
  document.title = `${to.meta.title || '数据总览'} - 舆情监控平台`
})

export default router