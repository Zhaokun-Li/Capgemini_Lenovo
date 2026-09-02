import axios from "axios"

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30000
})

request.interceptors.response.use(
  response => response.data,
  error => {
    console.error('接口请求失败：', error)
    return Promise.reject(error)
  }
)

export default request