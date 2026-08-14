<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { login, saveSession } from '../api/auth'

const router = useRouter()

const username = ref('')
const password = ref('')
const remember = ref(false)
const passwordVisible = ref(false)
const loading = ref(false)
const message = ref('')
const messageType = ref('')

const setMessage = (text, type) => {
  message.value = text
  messageType.value = type
}

const handleLogin = async () => {
  message.value = ''

  if (!username.value.trim()) {
    setMessage('请输入用户名或邮箱', 'error')
    return
  }

  if (!password.value) {
    setMessage('请输入密码', 'error')
    return
  }

  loading.value = true

  try {
    const result = await login(
      username.value.trim(),
      password.value
    )

    saveSession(result)

    if (remember.value) {
      localStorage.setItem(
        'rememberedUsername',
        username.value.trim()
      )
    } else {
      localStorage.removeItem('rememberedUsername')
    }

    setMessage('登录成功，正在进入系统', 'success')

    await router.replace('/overview')
  } catch (error) {
    console.error('登录失败：', error)

    if (error.response) {
      setMessage(
        error.response.data?.message || '用户名或密码错误',
        'error'
      )
    } else if (error.request) {
      setMessage('无法连接后端，请确认 Flask 已启动', 'error')
    } else {
      setMessage('登录请求发生错误', 'error')
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  const savedUsername =
    localStorage.getItem('rememberedUsername') || ''

  if (savedUsername) {
    username.value = savedUsername
    remember.value = true
  }
})
</script>

<template>
  <main class="auth-page">
    <section class="brand-panel">
      <div class="logo">L</div>
      <p class="brand-name">LENOVO INSIGHT</p>
      <h1>洞察每一条声音<br><span>驱动产品决策</span></h1>
      <p>3C 产品舆情监控与分析平台</p>
    </section>

    <section class="form-panel">
            <form class="auth-card" @submit.prevent="handleLogin">
        <p class="eyebrow">ACCOUNT LOGIN</p>
        <h2>欢迎回来</h2>
        <p class="description">管理员和普通用户使用同一个入口登录</p>

        <p
          v-if="message"
          class="message"
          :class="messageType"
        >
          {{ message }}
        </p>

        <label>
          用户名或邮箱
          <input
            v-model="username"
            type="text"
            autocomplete="username"
            placeholder="请输入用户名或邮箱"
          >
        </label>

        <label>
          密码
          <input
            v-model="password"
            type="password"
            autocomplete="current-password"
            placeholder="请输入密码"
          >
        </label>

        <label class="remember">
          <input v-model="remember" type="checkbox">
          记住账号
        </label>

        <button type="submit" :disabled="loading">
          {{ loading ? '正在登录...' : '登录系统' }}
        </button>

        <RouterLink class="register-link" to="/register">
          还没有账号？立即注册
        </RouterLink>
      </form>
    </section>
  </main>
</template>

<style scoped>
* { box-sizing: border-box; }
.auth-page { display: grid; grid-template-columns: 1.15fr .85fr; min-height: 100vh; background: #f4f7fb; }
.brand-panel { display: flex; flex-direction: column; justify-content: center; padding: 10%; color: white; background: linear-gradient(145deg, #071a3d, #103d78); }
.logo { display: grid; place-items: center; width: 48px; height: 48px; border: 2px solid white; font-size: 28px; font-weight: 800; }
.brand-name { letter-spacing: 3px; }
.brand-panel h1 { margin: 70px 0 18px; font-size: clamp(38px, 5vw, 68px); line-height: 1.15; }
.brand-panel h1 span { color: #3b82f6; }
.form-panel { display: grid; place-items: center; padding: 32px; }
.auth-card { width: min(440px, 100%); padding: 42px; border-radius: 18px; background: white; box-shadow: 0 18px 50px rgba(15, 35, 65, .1); }
.eyebrow { color: #2563eb; font-size: 12px; font-weight: 800; letter-spacing: 2px; }
h2 { margin: 8px 0; color: #16233a; font-size: 30px; }
.description { margin-bottom: 28px; color: #7b879a; }
label { display: grid; gap: 8px; margin: 18px 0; color: #374151; font-weight: 600; }
input { width: 100%; padding: 13px 14px; border: 1px solid #d9e0ea; border-radius: 8px; outline: none; }
input:focus { border-color: #2563eb; box-shadow: 0 0 0 3px #dbeafe; }
.remember { display: flex; align-items: center; font-weight: 400; }
.remember input { width: auto; }
button { width: 100%; margin-top: 8px; padding: 14px; border: 0; border-radius: 8px; color: white; background: #2563eb; font-weight: 700; cursor: pointer; }
button:disabled { opacity: .6; }
.register-link { display: block; margin-top: 22px; color: #2563eb; text-align: center; text-decoration: none; }
.message { padding: 11px 13px; border-radius: 7px; color: #b42318; background: #fef3f2; }
@media (max-width: 850px) { .auth-page { grid-template-columns: 1fr; } .brand-panel { display: none; } }
</style>

