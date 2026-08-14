import axios from 'axios'

const api = axios.create({
  baseURL: 'http://127.0.0.1:5000/api',
  timeout: 15000
})

export async function getReviews(params = {}) {
  const response = await api.get('/reviews', {
    params
  })

  return response.data
}

export async function getReviewStatistics(params = {}) {
  const statisticsParams = {
    ...params
  }

  delete statisticsParams.page
  delete statisticsParams.page_size
  delete statisticsParams.sort_by
  delete statisticsParams.sort_order

  const response = await api.get('/reviews/statistics', {
    params: statisticsParams
  })

  return response.data
}

export async function getReviewOptions() {
  const response = await api.get('/reviews/options')

  return response.data
}

export async function getReviewDashboard(days = 30, params = {}) {
  const response = await api.get('/reviews/dashboard', {
    params: {
      days,
      ...params
    }
  })

  return response.data
}

export async function getAnalysisSummary(params = {}) {
  const response = await api.get('/reviews/analysis-summary', { params })
  return response.data
}

export async function getReviewById(id) {
  const response = await api.get(`/reviews/${id}`)

  return response.data
}

export default api
