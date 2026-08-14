import axios from "axios"

const analysisRequest = axios.create({
  baseURL: "http://127.0.0.1:5000/api",
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