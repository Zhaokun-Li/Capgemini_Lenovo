import { ref } from 'vue'
import { getLatestAnalysis } from '../api/analysis'

const STORAGE_KEY = 'public_opinion_analysis_cache_v2'
const UPDATE_EVENT = 'database-data-updated'

function readStoredData() {
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null')
    return value && typeof value === 'object' ? value : null
  } catch {
    return null
  }
}

export const analysisData = ref(readStoredData())
export const analysisRefreshing = ref(false)

let pendingRequest = null

export async function loadAnalysis(force = false) {
  if (analysisData.value && !force) return analysisData.value
  if (pendingRequest) return pendingRequest

  analysisRefreshing.value = true
  pendingRequest = getLatestAnalysis()
    .then(response => {
      const body = response?.data || response
      if (body?.success === false) throw new Error(body.message || '分析数据加载失败')
      const result = body?.data || body
      analysisData.value = result
      localStorage.setItem(STORAGE_KEY, JSON.stringify(result))
      return result
    })
    .finally(() => {
      analysisRefreshing.value = false
      pendingRequest = null
    })

  return pendingRequest
}

export function clearAnalysisCache() {
  analysisData.value = null
  localStorage.removeItem(STORAGE_KEY)
  localStorage.removeItem('public_opinion_analysis_cache_v1')
  sessionStorage.removeItem('analysis-dashboard-cache')
  sessionStorage.removeItem('trend-dashboard-cache')
}

export async function refreshAfterDatabaseChange() {
  clearAnalysisCache()
  const result = await loadAnalysis(true)
  const updatedAt = String(Date.now())
  localStorage.setItem('databaseUpdatedAt', updatedAt)
  window.dispatchEvent(new CustomEvent(UPDATE_EVENT, {
    detail: { data: result, updatedAt }
  }))
  return result
}

export function onDatabaseUpdated(handler) {
  window.addEventListener(UPDATE_EVENT, handler)
  return () => window.removeEventListener(UPDATE_EVENT, handler)
}