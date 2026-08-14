<script setup>
import { onMounted, reactive, ref } from 'vue'
import { changePassword, getMe, updateProfile } from '../api/auth'

const profile = reactive({ username: '', display_name: '', email: '', phone: '', role: '' })
const passwords = reactive({ old_password: '', new_password: '', confirm: '' })
const message = ref('')

onMounted(async () => {
  try {
    Object.assign(profile, (await getMe()).data.user)
  } catch {
    message.value = '个人信息加载失败'
  }
})

const save = async () => {
  try {
    const result = await updateProfile(profile)
    Object.assign(profile, result.data.user)
    localStorage.setItem('user', JSON.stringify(result.data.user))
    message.value = '个人信息保存成功'
  } catch (error) {
    message.value = error.response?.data?.message || '保存失败'
  }
}

const savePassword = async () => {
  if (passwords.new_password !== passwords.confirm) {
    message.value = '两次输入的新密码不一致'
    return
  }
  try {
    await changePassword(passwords)
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    window.location.href = '/login'
  } catch (error) {
    message.value = error.response?.data?.message || '密码修改失败'
  }
}
</script>

<template>
  <div class="profile-page">
    <header><h1>个人中心</h1><p>查看和维护当前账号信息</p></header>
    <p v-if="message" class="message">{{ message }}</p>
    <div class="columns">
      <form class="card" @submit.prevent="save">
        <h2>基本信息</h2>
        <label>用户名<input v-model="profile.username" disabled></label>
        <label>显示名称<input v-model="profile.display_name" required></label>
        <label>邮箱<input v-model="profile.email" required type="email"></label>
        <label>手机号<input v-model="profile.phone"></label>
        <label>角色<input :value="profile.role === 'admin' ? '管理员' : '普通用户'" disabled></label>
        <button>保存信息</button>
      </form>
      <form class="card" @submit.prevent="savePassword">
        <h2>修改密码</h2>
        <label>原密码<input v-model="passwords.old_password" required type="password"></label>
        <label>新密码<input v-model="passwords.new_password" required type="password" minlength="8"></label>
        <label>确认新密码<input v-model="passwords.confirm" required type="password"></label>
        <button>修改密码</button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.profile-page { min-height: calc(100vh - 72px); padding: 28px; background: #f5f7fb; color: #182338; }
header p { color: #7c8798; }
.columns { display: grid; grid-template-columns: 1fr 1fr; gap: 22px; max-width: 1050px; }
.card { display: grid; gap: 16px; padding: 24px; border: 1px solid #e6eaf0; border-radius: 12px; background: white; }
label { display: grid; gap: 7px; color: #475467; font-size: 14px; font-weight: 600; }
input { padding: 11px; border: 1px solid #d8dee8; border-radius: 7px; }
button { padding: 12px; border: 0; border-radius: 7px; color: white; background: #2563eb; font-weight: 700; }
.message { max-width: 1050px; padding: 12px; border-radius: 8px; color: #175cd3; background: #eff8ff; }
@media (max-width: 760px) { .columns { grid-template-columns: 1fr; } }
</style>

