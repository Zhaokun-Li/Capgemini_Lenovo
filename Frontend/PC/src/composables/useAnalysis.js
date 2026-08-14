import { computed, ref } from "vue"
import { getLatestAnalysis } from "../api/analysis.js"

const analysisData = ref(null)
const analysisLoading = ref(false)
const analysisError = ref("")

export function useAnalysis() {
  const overview = computed(() => {
    return analysisData.value?.overview || {}
  })

  const sentiment = computed(() => {
    return analysisData.value?.sentiment || []
  })

  const products = computed(() => {
    return analysisData.value?.product || []
  })

  const memory = computed(() => {
    return analysisData.value?.memory || []
  })

  const storage = computed(() => {
    return analysisData.value?.storage || []
  })

  const trend = computed(() => {
    return analysisData.value?.trend || []
  })

  const keywords = computed(() => {
    return analysisData.value?.keywords || []
  })

  const risks = computed(() => {
    return analysisData.value?.risks || []
  })

  async function loadAnalysis(force = false) {
    if (analysisData.value && !force) {
      return
    }

    analysisLoading.value = true
    analysisError.value = ""

    try {
      const response = await getLatestAnalysis()
      analysisData.value = response.data.data
    } catch (error) {
      analysisError.value =
        error.response?.data?.message ||
        error.message ||
        "获取分析结果失败"
    } finally {
      analysisLoading.value = false
    }
  }

  function setAnalysis(data) {
    analysisData.value = data
  }

  function clearAnalysis() {
    analysisData.value = null
  }

  return {
    analysisData,
    analysisLoading,
    analysisError,
    overview,
    sentiment,
    products,
    memory,
    storage,
    trend,
    keywords,
    risks,
    loadAnalysis,
    setAnalysis,
    clearAnalysis
  }
}