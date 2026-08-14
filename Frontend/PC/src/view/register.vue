<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { register } from '../api/auth'

const router = useRouter()
const form = reactive({
  username: '',
  display_name: '',
  email: '',
  phone: '',
  password: '',
  confirmPassword: ''
})
const loading = ref(false)
const message = ref('')
const success = ref(false)

const submit = async () => {
  message.value = ''
  success.value = false
  if (form.password !== form.confirmPassword) {
    message.value = '两次输入的密码不一致'
    return
  }
  loading.value = true
  try {
    await register(form)
    success.value = true
    message.value = '注册成功，即将返回登录页'
    setTimeout(() => router.replace('/login'), 1000)
  } catch (error) {
    message.value = error.response?.data?.message || '注册失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="register-page">
    <form class="card" @submit.prevent="submit">
      <p class="eyebrow">CREATE ACCOUNT</p>
      <h1>创建普通用户账号</h1>
      <p class="tip">注册后，用户信息将安全写入 MySQL 数据库</p>
      <p v-if="message" class="message" :class="{ success }">{{ message }}</p>
      <div class="grid">
        <label>用户名<input v-model.trim="form.username" required minlength="3"></label>
        <label>显示名称<input v-model.trim="form.display_name" placeholder="如：张三"></label>
        <label>邮箱<input v-model.trim="form.email" required type="email"></label>
        <label>手机号<input v-model.trim="form.phone"></label>
        <label>密码<input v-model="form.password" required type="password" minlength="8" placeholder="至少8位，包含字母和数字"></label>
        <label>确认密码<input v-model="form.confirmPassword" required type="password"></label>
      </div>
      <button :disabled="loading">{{ loading ? '正在注册...' : '注册账号' }}</button>
      <RouterLink to="/login">已有账号？返回登录</RouterLink>
    </form>
  </main>
</template>

<style scoped>
* { box-sizing: border-box; }
.register-page { display: grid; min-height: 100vh; place-items: center; padding: 30px; background: linear-gradient(145deg, #071a3d, #164d8c); }
.card { width: min(720px, 100%); padding: 42px; border-radius: 18px; background: white; box-shadow: 0 25px 70px rgba(0, 0, 0, .2); }
.eyebrow { color: #2563eb; font-size: 12px; font-weight: 800; letter-spacing: 2px; }
h1 { margin: 8px 0; color: #16233a; }
.tip { margin-bottom: 28px; color: #7b879a; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
label { display: grid; gap: 8px; color: #374151; font-weight: 600; }
input { padding: 12px; border: 1px solid #d9e0ea; border-radius: 8px; outline: none; }
input:focus { border-color: #2563eb; box-shadow: 0 0 0 3px #dbeafe; }
button { width: 100%; margin: 28px 0 18px; padding: 14px; border: 0; border-radius: 8px; color: white; background: #2563eb; font-weight: 700; }
a { display: block; color: #2563eb; text-align: center; text-decoration: none; }
.message { padding: 11px; color: #b42318; background: #fef3f2; border-radius: 7px; }
.message.success { color: #027a48; background: #ecfdf3; }
@media (max-width: 650px) { .grid { grid-template-columns: 1fr; } .card { padding: 28px; } }
</style>

