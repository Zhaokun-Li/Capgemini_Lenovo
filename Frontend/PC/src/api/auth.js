import axios from 'axios'

const authApi = axios.create({
  baseURL: 'http://127.0.0.1:5000/api',
  timeout: 15000
})

authApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

authApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    }
    return Promise.reject(error)
  }
)

export const register = (data) => authApi.post('/auth/register', data).then((r) => r.data)
export const login = (account, password) =>
  authApi.post('/auth/login', { account, password }).then((r) => r.data)
export const getMe = () => authApi.get('/auth/me').then((r) => r.data)
export const updateProfile = (data) =>
  authApi.put('/auth/profile', data).then((r) => r.data)
export const changePassword = (data) =>
  authApi.put('/auth/password', data).then((r) => r.data)
export const getUsers = (params) =>
  authApi.get('/admin/users', { params }).then((r) => r.data)
export const createUser = (data) =>
  authApi.post('/admin/users', data).then((r) => r.data)
export const updateUser = (id, data) =>
  authApi.put(`/admin/users/${id}`, data).then((r) => r.data)
export const resetUserPassword = (id, newPassword) =>
  authApi.put(`/admin/users/${id}/reset-password`, {
    new_password: newPassword
  }).then((r) => r.data)
export const deleteUser = (id) =>
  authApi.delete(`/admin/users/${id}`).then((r) => r.data)

export const saveSession = (result) => {
  localStorage.setItem('token', result.data.token)
  localStorage.setItem('user', JSON.stringify(result.data.user))
}

export const getStoredUser = () => {
  try {
    return JSON.parse(localStorage.getItem('user') || 'null')
  } catch {
    return null
  }
}

export const logout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
}

export default authApi

