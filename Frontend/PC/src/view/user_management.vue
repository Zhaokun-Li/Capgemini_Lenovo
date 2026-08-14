<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000'

const users = ref([])
const loading = ref(false)
const saving = ref(false)
const message = ref('')
const messageType = ref('success')
const keyword = ref('')
const roleFilter = ref('')
const statusFilter = ref('')
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
const pages = ref(1)
const showUserModal = ref(false)
const showPasswordModal = ref(false)
const showDeleteModal = ref(false)
const editingUser = ref(null)
const selectedUser = ref(null)

const form = reactive({
  username: '',
  display_name: '',
  email: '',
  phone: '',
  password: '',
  role: 'user',
  status: 'active'
})

const passwordForm = reactive({
  password: '',
  confirmPassword: ''
})

const currentUser = computed(() => {
  try {
    return JSON.parse(localStorage.getItem('user') || 'null')
  } catch {
    return null
  }
})

const filteredUsers = computed(() => {
  return users.value.filter((user) => {
    const matchesRole = !roleFilter.value || user.role === roleFilter.value
    const matchesStatus = !statusFilter.value || user.status === statusFilter.value
    return matchesRole && matchesStatus
  })
})

const activeCount = computed(() => users.value.filter((user) => user.status === 'active').length)
const adminCount = computed(() => users.value.filter((user) => user.role === 'admin').length)
const disabledCount = computed(() => users.value.filter((user) => user.status === 'disabled').length)

const pageNumbers = computed(() => {
  const start = Math.max(1, page.value - 2)
  const end = Math.min(pages.value, start + 4)
  const result = []
  for (let number = Math.max(1, end - 4); number <= end; number += 1) result.push(number)
  return result
})

const request = async (path, options = {}) => {
  const token = localStorage.getItem('token')
  const headers = {
    ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers })
  let result = {}
  try {
    result = await response.json()
  } catch {
    result = {}
  }

  if (!response.ok) {
    const error = new Error(result.message || `请求失败（${response.status}）`)
    error.status = response.status
    throw error
  }
  return result
}

const notify = (text, type = 'success') => {
  message.value = text
  messageType.value = type
  window.clearTimeout(notify.timer)
  notify.timer = window.setTimeout(() => {
    message.value = ''
  }, 3500)
}

const loadUsers = async () => {
  loading.value = true
  try {
    const params = new URLSearchParams({
      page: String(page.value),
      page_size: String(pageSize.value)
    })
    if (keyword.value.trim()) params.set('keyword', keyword.value.trim())

    const result = await request(`/api/admin/users?${params}`)
    users.value = result.data?.items || []
    total.value = result.data?.pagination?.total || 0
    pages.value = Math.max(result.data?.pagination?.pages || 1, 1)
  } catch (error) {
    users.value = []
    notify(error.message === 'Failed to fetch' ? '无法连接后端服务，请确认 Flask 已启动' : error.message, 'error')
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  Object.assign(form, {
    username: '',
    display_name: '',
    email: '',
    phone: '',
    password: '',
    role: 'user',
    status: 'active'
  })
}

const openCreate = () => {
  editingUser.value = null
  resetForm()
  showUserModal.value = true
}

const openEdit = (user) => {
  editingUser.value = user
  Object.assign(form, {
    username: user.username,
    display_name: user.display_name || '',
    email: user.email,
    phone: user.phone || '',
    password: '',
    role: user.role,
    status: user.status
  })
  showUserModal.value = true
}

const saveUser = async () => {
  if (!form.display_name.trim()) {
    notify('请输入显示名称', 'error')
    return
  }

  if (!editingUser.value && (!form.username.trim() || !form.email.trim() || !form.password)) {
    notify('请填写用户名、邮箱和初始密码', 'error')
    return
  }

  if (!editingUser.value && (form.password.length < 8 || !/[A-Za-z]/.test(form.password) || !/\d/.test(form.password))) {
    notify('密码至少 8 位，且必须包含字母和数字', 'error')
    return
  }

  saving.value = true
  try {
    if (editingUser.value) {
      await request(`/api/admin/users/${editingUser.value.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          display_name: form.display_name.trim(),
          role: form.role,
          status: form.status
        })
      })
      notify('用户信息已更新')
    } else {
      await request('/api/admin/users', {
        method: 'POST',
        body: JSON.stringify({
          username: form.username.trim(),
          display_name: form.display_name.trim(),
          email: form.email.trim(),
          phone: form.phone.trim(),
          password: form.password,
          role: form.role
        })
      })
      notify('用户创建成功')
    }
    showUserModal.value = false
    await loadUsers()
  } catch (error) {
    notify(error.message, 'error')
  } finally {
    saving.value = false
  }
}

const toggleStatus = async (user) => {
  try {
    await request(`/api/admin/users/${user.id}`, {
      method: 'PUT',
      body: JSON.stringify({
        display_name: user.display_name,
        role: user.role,
        status: user.status === 'active' ? 'disabled' : 'active'
      })
    })
    notify(user.status === 'active' ? '账号已禁用' : '账号已启用')
    await loadUsers()
  } catch (error) {
    notify(error.message, 'error')
  }
}

const openPassword = (user) => {
  selectedUser.value = user
  passwordForm.password = ''
  passwordForm.confirmPassword = ''
  showPasswordModal.value = true
}

const resetPassword = async () => {
  if (passwordForm.password.length < 8 || !/[A-Za-z]/.test(passwordForm.password) || !/\d/.test(passwordForm.password)) {
    notify('密码至少 8 位，且必须包含字母和数字', 'error')
    return
  }
  if (passwordForm.password !== passwordForm.confirmPassword) {
    notify('两次输入的密码不一致', 'error')
    return
  }

  saving.value = true
  try {
    await request(`/api/admin/users/${selectedUser.value.id}/reset-password`, {
      method: 'PUT',
      body: JSON.stringify({ new_password: passwordForm.password })
    })
    showPasswordModal.value = false
    notify('密码重置成功')
  } catch (error) {
    notify(error.message, 'error')
  } finally {
    saving.value = false
  }
}

const openDelete = (user) => {
  selectedUser.value = user
  showDeleteModal.value = true
}

const deleteUser = async () => {
  saving.value = true
  try {
    await request(`/api/admin/users/${selectedUser.value.id}`, { method: 'DELETE' })
    showDeleteModal.value = false
    notify('用户已删除')
    if (users.value.length === 1 && page.value > 1) page.value -= 1
    await loadUsers()
  } catch (error) {
    notify(error.message, 'error')
  } finally {
    saving.value = false
  }
}

const search = () => {
  page.value = 1
  loadUsers()
}

const clearFilters = () => {
  keyword.value = ''
  roleFilter.value = ''
  statusFilter.value = ''
  page.value = 1
  loadUsers()
}

const changePage = (value) => {
  if (value < 1 || value > pages.value || value === page.value) return
  page.value = value
  loadUsers()
}

watch(pageSize, () => {
  page.value = 1
  loadUsers()
})

onMounted(loadUsers)
</script>

<template>
  <section class="users-page">
    <div class="page-header">
      <div>
        <div class="breadcrumb">管理员功能 / 用户管理</div>
        <h1>用户管理</h1>
        <p>查看系统账号，管理用户角色、账号状态和登录权限。</p>
      </div>
      <button class="primary-button" type="button" @click="openCreate">
        <svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14" /></svg>
        新增用户
      </button>
    </div>

    <Transition name="toast">
      <div v-if="message" class="toast" :class="messageType">
        <svg v-if="messageType === 'success'" viewBox="0 0 24 24"><path d="m5 12 4 4L19 6" /></svg>
        <svg v-else viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" /><path d="M12 7v6M12 17h.01" /></svg>
        {{ message }}
      </div>
    </Transition>

    <div class="stats-grid">
      <article class="stat-card">
        <div class="stat-icon blue"><svg viewBox="0 0 24 24"><circle cx="9" cy="8" r="3" /><circle cx="17" cy="9" r="2" /><path d="M3 20c0-4 2-7 6-7s6 3 6 7M15 14c3 0 5 2 5 5" /></svg></div>
        <div><span>用户总数</span><strong>{{ total }}</strong></div>
      </article>
      <article class="stat-card">
        <div class="stat-icon green"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" /><path d="m8 12 3 3 5-6" /></svg></div>
        <div><span>本页正常账号</span><strong>{{ activeCount }}</strong></div>
      </article>
      <article class="stat-card">
        <div class="stat-icon purple"><svg viewBox="0 0 24 24"><path d="m12 3 7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6l7-3Z" /><path d="m9 12 2 2 4-5" /></svg></div>
        <div><span>本页管理员</span><strong>{{ adminCount }}</strong></div>
      </article>
      <article class="stat-card">
        <div class="stat-icon red"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" /><path d="M8 8l8 8M16 8l-8 8" /></svg></div>
        <div><span>本页禁用账号</span><strong>{{ disabledCount }}</strong></div>
      </article>
    </div>

    <div class="panel">
      <div class="toolbar">
        <div class="search-box">
          <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></svg>
          <input v-model.trim="keyword" placeholder="搜索用户名、姓名或邮箱" @keyup.enter="search">
        </div>
        <select v-model="roleFilter">
          <option value="">全部角色</option>
          <option value="admin">管理员</option>
          <option value="user">普通用户</option>
        </select>
        <select v-model="statusFilter">
          <option value="">全部状态</option>
          <option value="active">正常</option>
          <option value="disabled">已禁用</option>
        </select>
        <button class="search-button" type="button" @click="search">查询</button>
        <button class="text-button" type="button" @click="clearFilters">重置</button>
      </div>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>用户</th>
              <th>联系方式</th>
              <th>角色</th>
              <th>状态</th>
              <th>注册时间</th>
              <th>最后登录</th>
              <th class="operation-column">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="7"><div class="empty-state"><span class="loader"></span><p>正在加载用户数据...</p></div></td>
            </tr>
            <tr v-else-if="filteredUsers.length === 0">
              <td colspan="7">
                <div class="empty-state">
                  <svg viewBox="0 0 24 24"><circle cx="9" cy="8" r="3" /><circle cx="17" cy="9" r="2" /><path d="M3 20c0-4 2-7 6-7s6 3 6 7M15 14c3 0 5 2 5 5" /></svg>
                  <strong>暂无符合条件的用户</strong>
                  <p>请更换筛选条件或新增用户。</p>
                </div>
              </td>
            </tr>
            <template v-else>
              <tr v-for="user in filteredUsers" :key="user.id">
                <td>
                  <div class="user-cell">
                    <span class="avatar">{{ (user.display_name || user.username).slice(0, 1).toUpperCase() }}</span>
                    <div><strong>{{ user.display_name || user.username }}</strong><small>@{{ user.username }}</small></div>
                  </div>
                </td>
                <td><div class="contact-cell"><span>{{ user.email }}</span><small>{{ user.phone || '未填写手机号' }}</small></div></td>
                <td><span class="role-tag" :class="user.role">{{ user.role === 'admin' ? '管理员' : '普通用户' }}</span></td>
                <td><span class="status-tag" :class="user.status"><i></i>{{ user.status === 'active' ? '正常' : '已禁用' }}</span></td>
                <td>{{ user.created_at ? user.created_at.replace('T', ' ').slice(0, 16) : '-' }}</td>
                <td>{{ user.last_login_at ? user.last_login_at.replace('T', ' ').slice(0, 16) : '从未登录' }}</td>
                <td>
                  <div class="actions">
                    <button title="编辑用户" type="button" @click="openEdit(user)"><svg viewBox="0 0 24 24"><path d="m14 5 5 5M4 20l4-1 11-11-4-4L4 15v5Z" /></svg></button>
                    <button title="重置密码" type="button" @click="openPassword(user)"><svg viewBox="0 0 24 24"><circle cx="8" cy="15" r="4" /><path d="m11 12 8-8M16 7l2 2M14 9l2 2" /></svg></button>
                    <button :title="user.status === 'active' ? '禁用账号' : '启用账号'" type="button" :disabled="user.id === currentUser?.id" @click="toggleStatus(user)">
                      <svg v-if="user.status === 'active'" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" /><path d="M8 8l8 8" /></svg>
                      <svg v-else viewBox="0 0 24 24"><path d="m5 12 4 4L19 6" /></svg>
                    </button>
                    <button class="danger-action" title="删除用户" type="button" :disabled="user.id === currentUser?.id" @click="openDelete(user)"><svg viewBox="0 0 24 24"><path d="M4 7h16M9 3h6l1 4H8l1-4ZM7 7l1 14h8l1-14M10 11v6M14 11v6" /></svg></button>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <div class="pagination">
        <span>共 {{ total }} 条记录</span>
        <div class="page-controls">
          <button type="button" :disabled="page === 1" @click="changePage(page - 1)">‹</button>
          <button v-for="number in pageNumbers" :key="number" type="button" :class="{ active: number === page }" @click="changePage(number)">{{ number }}</button>
          <button type="button" :disabled="page === pages" @click="changePage(page + 1)">›</button>
        </div>
        <select v-model="pageSize"><option :value="10">10 条/页</option><option :value="20">20 条/页</option><option :value="50">50 条/页</option></select>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="showUserModal" class="modal-mask" @mousedown.self="showUserModal = false">
        <div class="modal-card">
          <div class="modal-header">
            <div><h2>{{ editingUser ? '编辑用户' : '新增用户' }}</h2><p>{{ editingUser ? '修改账号角色、状态和显示名称。' : '创建一个可登录系统的新账号。' }}</p></div>
            <button type="button" @click="showUserModal = false">×</button>
          </div>
          <form class="form-grid" @submit.prevent="saveUser">
            <label><span>用户名 <b>*</b></span><input v-model.trim="form.username" :disabled="Boolean(editingUser)" maxlength="50" placeholder="请输入用户名"></label>
            <label><span>显示名称 <b>*</b></span><input v-model.trim="form.display_name" maxlength="50" placeholder="请输入显示名称"></label>
            <label><span>邮箱地址 <b>*</b></span><input v-model.trim="form.email" :disabled="Boolean(editingUser)" type="email" placeholder="name@example.com"></label>
            <label><span>手机号</span><input v-model.trim="form.phone" :disabled="Boolean(editingUser)" placeholder="请输入手机号"></label>
            <label v-if="!editingUser" class="full-row"><span>初始密码 <b>*</b></span><input v-model="form.password" type="password" autocomplete="new-password" placeholder="至少 8 位，包含字母和数字"><small>用户登录后可以在个人中心修改密码。</small></label>
            <label><span>用户角色 <b>*</b></span><select v-model="form.role"><option value="user">普通用户</option><option value="admin">管理员</option></select></label>
            <label v-if="editingUser"><span>账号状态 <b>*</b></span><select v-model="form.status"><option value="active">正常</option><option value="disabled">已禁用</option></select></label>
            <div class="modal-actions full-row"><button class="cancel-button" type="button" @click="showUserModal = false">取消</button><button class="primary-button" type="submit" :disabled="saving">{{ saving ? '保存中...' : '确认保存' }}</button></div>
          </form>
        </div>
      </div>

      <div v-if="showPasswordModal" class="modal-mask" @mousedown.self="showPasswordModal = false">
        <div class="modal-card small">
          <div class="modal-header"><div><h2>重置密码</h2><p>为 {{ selectedUser?.display_name || selectedUser?.username }} 设置新密码。</p></div><button type="button" @click="showPasswordModal = false">×</button></div>
          <form class="form-grid one-column" @submit.prevent="resetPassword">
            <label><span>新密码 <b>*</b></span><input v-model="passwordForm.password" type="password" autocomplete="new-password" placeholder="至少 8 位，包含字母和数字"></label>
            <label><span>确认新密码 <b>*</b></span><input v-model="passwordForm.confirmPassword" type="password" autocomplete="new-password" placeholder="再次输入新密码"></label>
            <div class="modal-actions"><button class="cancel-button" type="button" @click="showPasswordModal = false">取消</button><button class="primary-button" type="submit" :disabled="saving">{{ saving ? '提交中...' : '确认重置' }}</button></div>
          </form>
        </div>
      </div>

      <div v-if="showDeleteModal" class="modal-mask" @mousedown.self="showDeleteModal = false">
        <div class="modal-card confirm-card">
          <div class="warning-icon"><svg viewBox="0 0 24 24"><path d="M12 3 2.5 20h19L12 3Z" /><path d="M12 9v5M12 17h.01" /></svg></div>
          <h2>确认删除用户？</h2>
          <p>账号 <strong>{{ selectedUser?.username }}</strong> 将被永久删除，此操作无法撤销。</p>
          <div class="modal-actions"><button class="cancel-button" type="button" @click="showDeleteModal = false">取消</button><button class="delete-button" type="button" :disabled="saving" @click="deleteUser">{{ saving ? '删除中...' : '确认删除' }}</button></div>
        </div>
      </div>
    </Teleport>
  </section>
</template>

<style scoped>
.users-page { min-height: calc(100vh - var(--header-height)); padding: 28px; color: #182338; background: #f5f7fb; }
.page-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; margin-bottom: 24px; }
.breadcrumb { margin-bottom: 9px; color: #8a96a8; font-size: 12px; }
.page-header h1 { margin: 0; color: #17233b; font-size: 25px; line-height: 1.25; }
.page-header p { margin: 8px 0 0; color: #7b8799; font-size: 14px; }
button, input, select { font: inherit; }
button { cursor: pointer; }
button:disabled { cursor: not-allowed; opacity: .45; }
.primary-button { display: inline-flex; min-height: 40px; padding: 0 17px; align-items: center; justify-content: center; gap: 8px; border: 0; border-radius: 8px; color: #fff; background: #2563eb; font-size: 13px; font-weight: 600; box-shadow: 0 5px 14px rgba(37, 99, 235, .18); }
.primary-button:hover:not(:disabled) { background: #1d4ed8; }
.primary-button svg { width: 17px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; }
.stats-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; margin-bottom: 18px; }
.stat-card { display: flex; min-height: 92px; padding: 18px; align-items: center; gap: 14px; border: 1px solid #e7ebf1; border-radius: 11px; background: #fff; box-shadow: 0 2px 8px rgba(20, 36, 68, .03); }
.stat-icon { display: grid; width: 46px; height: 46px; flex-shrink: 0; place-items: center; border-radius: 11px; }
.stat-icon svg { width: 23px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.stat-icon.blue { color: #2563eb; background: #eef4ff; }.stat-icon.green { color: #059669; background: #eafaf4; }.stat-icon.purple { color: #7c3aed; background: #f3efff; }.stat-icon.red { color: #dc2626; background: #fff0f0; }
.stat-card div:last-child { display: flex; flex-direction: column; gap: 6px; }.stat-card span { color: #8490a2; font-size: 12px; }.stat-card strong { color: #17233b; font-size: 23px; }
.panel { overflow: hidden; border: 1px solid #e5eaf1; border-radius: 11px; background: #fff; box-shadow: 0 3px 12px rgba(20, 36, 68, .035); }
.toolbar { display: flex; padding: 17px 18px; align-items: center; gap: 10px; border-bottom: 1px solid #edf0f4; }
.search-box { position: relative; width: min(360px, 100%); }.search-box svg { position: absolute; top: 50%; left: 12px; width: 17px; fill: none; stroke: #93a0b2; stroke-width: 1.8; transform: translateY(-50%); }.search-box input { width: 100%; padding-left: 38px; }
.toolbar input, .toolbar select, .form-grid input, .form-grid select { height: 40px; padding: 0 12px; border: 1px solid #dbe1ea; border-radius: 7px; outline: none; color: #344054; background: #fff; font-size: 13px; box-sizing: border-box; }
.toolbar input:focus, .toolbar select:focus, .form-grid input:focus, .form-grid select:focus { border-color: #4f80ec; box-shadow: 0 0 0 3px rgba(37, 99, 235, .08); }
.toolbar select { min-width: 120px; }.search-button { min-height: 40px; padding: 0 18px; border: 0; border-radius: 7px; color: #fff; background: #315fca; font-size: 13px; }.text-button { min-height: 40px; padding: 0 10px; border: 0; color: #667085; background: transparent; font-size: 13px; }
.table-wrap { width: 100%; overflow-x: auto; }
table { width: 100%; min-width: 1050px; border-collapse: collapse; }
th, td { padding: 14px 16px; border-bottom: 1px solid #edf0f4; text-align: left; white-space: nowrap; }
th { color: #718096; background: #fafbfc; font-size: 12px; font-weight: 600; }.operation-column { width: 170px; }
td { color: #536174; font-size: 12px; }tbody tr:hover { background: #fbfcff; }tbody tr:last-child td { border-bottom: 0; }
.user-cell { display: flex; align-items: center; gap: 11px; }.avatar { display: grid; width: 36px; height: 36px; flex-shrink: 0; place-items: center; border-radius: 9px; color: #2f5fc8; background: #edf3ff; font-size: 14px; font-weight: 700; }.user-cell div, .contact-cell { display: flex; flex-direction: column; gap: 4px; }.user-cell strong { color: #263449; font-size: 13px; }.user-cell small, .contact-cell small { color: #98a2b3; font-size: 11px; }
.role-tag, .status-tag { display: inline-flex; height: 25px; padding: 0 9px; align-items: center; gap: 6px; border-radius: 20px; font-size: 11px; font-weight: 600; }.role-tag.admin { color: #6941c6; background: #f4f0ff; }.role-tag.user { color: #315fca; background: #eef4ff; }.status-tag.active { color: #087a55; background: #eafaf4; }.status-tag.disabled { color: #b42318; background: #fff0f0; }.status-tag i { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.actions { display: flex; gap: 5px; }.actions button { display: grid; width: 30px; height: 30px; padding: 0; place-items: center; border: 1px solid #e1e6ed; border-radius: 6px; color: #657286; background: #fff; }.actions button:hover:not(:disabled) { color: #2563eb; border-color: #b9cdf9; background: #f6f9ff; }.actions button.danger-action:hover:not(:disabled) { color: #dc2626; border-color: #fecaca; background: #fff7f7; }.actions svg { width: 15px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.empty-state { display: flex; min-height: 250px; align-items: center; justify-content: center; flex-direction: column; color: #98a2b3; }.empty-state svg { width: 44px; margin-bottom: 12px; fill: none; stroke: #c2c9d3; stroke-width: 1.4; }.empty-state strong { color: #667085; }.empty-state p { margin: 7px 0 0; font-size: 12px; }.loader { width: 27px; height: 27px; border: 3px solid #e4e8ef; border-top-color: #2563eb; border-radius: 50%; animation: spin .8s linear infinite; }
.pagination { display: flex; min-height: 62px; padding: 0 18px; align-items: center; justify-content: space-between; gap: 16px; border-top: 1px solid #edf0f4; color: #7a8698; font-size: 12px; }.page-controls { display: flex; gap: 5px; }.page-controls button { min-width: 31px; height: 31px; padding: 0 8px; border: 1px solid #e0e5ec; border-radius: 6px; color: #667085; background: #fff; }.page-controls button.active { color: #fff; border-color: #2563eb; background: #2563eb; }.pagination select { height: 33px; border: 1px solid #e0e5ec; border-radius: 6px; color: #667085; background: #fff; font-size: 12px; }
.toast { position: fixed; top: 88px; right: 25px; z-index: 3000; display: flex; max-width: 400px; padding: 12px 16px; align-items: center; gap: 9px; border: 1px solid; border-radius: 9px; font-size: 13px; box-shadow: 0 9px 30px rgba(25, 38, 65, .13); }.toast.success { color: #067647; border-color: #abefc6; background: #ecfdf3; }.toast.error { color: #b42318; border-color: #fecdca; background: #fef3f2; }.toast svg { width: 18px; flex-shrink: 0; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; }
.modal-mask { position: fixed; inset: 0; z-index: 4000; display: grid; padding: 20px; place-items: center; background: rgba(15, 23, 42, .44); backdrop-filter: blur(2px); }
.modal-card { width: min(620px, 100%); overflow: hidden; border-radius: 12px; background: #fff; box-shadow: 0 24px 65px rgba(15, 23, 42, .24); }.modal-card.small { width: min(460px, 100%); }.modal-header { display: flex; padding: 21px 23px 17px; align-items: flex-start; justify-content: space-between; border-bottom: 1px solid #edf0f4; }.modal-header h2 { margin: 0; color: #17233b; font-size: 19px; }.modal-header p { margin: 7px 0 0; color: #8490a2; font-size: 12px; }.modal-header > button { width: 30px; height: 30px; border: 0; border-radius: 6px; color: #7d899a; background: transparent; font-size: 23px; line-height: 1; }
.form-grid { display: grid; padding: 21px 23px 23px; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 17px; }.form-grid.one-column { grid-template-columns: 1fr; }.form-grid label { display: flex; flex-direction: column; gap: 7px; }.form-grid label > span { color: #475467; font-size: 12px; font-weight: 600; }.form-grid b { color: #ef4444; }.form-grid input:disabled { color: #98a2b3; background: #f5f6f8; }.form-grid label > small { color: #98a2b3; font-size: 11px; }.full-row { grid-column: 1 / -1; }
.modal-actions { display: flex; padding-top: 3px; align-items: center; justify-content: flex-end; gap: 9px; }.cancel-button, .delete-button { min-height: 39px; padding: 0 17px; border: 1px solid #d9dfe7; border-radius: 7px; color: #536174; background: #fff; font-size: 13px; }.delete-button { color: #fff; border-color: #dc2626; background: #dc2626; }.confirm-card { width: min(420px, 100%); padding: 27px; text-align: center; }.confirm-card h2 { margin: 15px 0 8px; color: #17233b; font-size: 19px; }.confirm-card p { margin: 0; color: #687588; font-size: 13px; line-height: 1.7; }.confirm-card .modal-actions { margin-top: 23px; justify-content: center; }.warning-icon { display: grid; width: 50px; height: 50px; margin: 0 auto; place-items: center; border-radius: 50%; color: #dc2626; background: #fff0f0; }.warning-icon svg { width: 25px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.toast-enter-active, .toast-leave-active { transition: .2s ease; }.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateY(-8px); }
@keyframes spin { to { transform: rotate(360deg); } }
@media (max-width: 1100px) { .stats-grid { grid-template-columns: repeat(2, 1fr); }.toolbar { flex-wrap: wrap; } }
@media (max-width: 700px) { .users-page { padding: 18px; }.page-header { align-items: flex-start; flex-direction: column; }.stats-grid { grid-template-columns: 1fr; }.toolbar { align-items: stretch; flex-direction: column; }.search-box, .toolbar select { width: 100%; }.pagination { padding: 14px; flex-wrap: wrap; justify-content: center; }.form-grid { grid-template-columns: 1fr; }.full-row { grid-column: auto; }.toast { top: 15px; right: 15px; left: 15px; } }
</style>
