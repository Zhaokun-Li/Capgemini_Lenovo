import axios from "axios"

const analysisRequest = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 120000
})

analysisRequest.interceptors.request.use(config => {
  const token = localStorage.getItem("token")

  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  return config
})

export function getLatestAnalysis() {
  return analysisRequest.get("/analysis/latest")
}