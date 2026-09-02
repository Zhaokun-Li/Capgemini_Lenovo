<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { refreshAfterDatabaseChange } from '../store/analysisCache'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL
const fileInput = ref(null)
const selectedFile = ref(null)
const isDragging = ref(false)
const isUploading = ref(false)
const progress = ref(0)
const message = ref('')
const messageType = ref('')
const importResult = ref(null)
const importRecords = ref([])
const reviews = ref([])
const reviewsLoading = ref(false)
const reviewsError = ref('')
const reviewKeyword = ref('')
const reviewPage = ref(1)
const reviewPageSize = 10
const reviewTotal = ref(0)
const reviewPages = ref(1)
const editorOpen = ref(false)
const editorSaving = ref(false)
const editingId = ref(null)
const emptyReviewForm = () => ({
  data_index: '',
  username: '',
  computer_config: '',
  review_content: '',
  helpful_count: 0,
  repeat_purchase: '否',
  rating: 5,
  memory: '',
  disk: '',
  review_date: '',
  product_series: '',
  sentiment_score: '',
  sentiment_label: '',
  keywords: ''
})
const reviewForm = reactive(emptyReviewForm())

const allowedExtensions = ['csv', 'xls', 'xlsx']
const maxFileSize = 50 * 1024 * 1024

const formattedFileSize = computed(() => {
  if (!selectedFile.value) return ''
  const size = selectedFile.value.size
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
})

const fileExtension = computed(() => {
  if (!selectedFile.value) return ''
  return selectedFile.value.name.split('.').pop()?.toUpperCase() || ''
})

const openFilePicker = () => {
  if (!isUploading.value) fileInput.value?.click()
}

const validateFile = (file) => {
  const extension = file.name.split('.').pop()?.toLowerCase()

  if (!allowedExtensions.includes(extension)) {
    showMessage('仅支持 CSV、XLS 和 XLSX 格式', 'error')
    return false
  }

  if (file.size > maxFileSize) {
    showMessage('文件大小不能超过 50 MB', 'error')
    return false
  }

  return true
}

const selectFile = (file) => {
  if (!file || !validateFile(file)) return
  selectedFile.value = file
  importResult.value = null
  progress.value = 0
  message.value = ''
}

const handleFileChange = (event) => {
  selectFile(event.target.files?.[0])
  event.target.value = ''
}

const handleDrop = (event) => {
  isDragging.value = false
  selectFile(event.dataTransfer.files?.[0])
}

const removeFile = () => {
  if (isUploading.value) return
  selectedFile.value = null
  importResult.value = null
  progress.value = 0
  message.value = ''
}

const showMessage = (text, type) => {
  message.value = text
  messageType.value = type
}

const authHeaders = () => {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

const parseApiResult = async (response) => {
  const result = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(result.message || `请求失败（${response.status}）`)
  return result
}

const loadReviews = async (page = reviewPage.value) => {
  reviewsLoading.value = true
  reviewsError.value = ''
  try {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(reviewPageSize),
      keyword: reviewKeyword.value.trim()
    })
    const response = await fetch(`${API_BASE_URL}/admin/reviews?${params}`, {
      headers: authHeaders()
    })
    const result = await parseApiResult(response)
    reviews.value = result.data?.items || []
    reviewPage.value = result.data?.pagination?.page || 1
    reviewTotal.value = result.data?.pagination?.total || 0
    reviewPages.value = Math.max(result.data?.pagination?.pages || 1, 1)
  } catch (error) {
    reviews.value = []
    reviewTotal.value = 0
    reviewPages.value = 1
    reviewsError.value = error.message
  } finally {
    reviewsLoading.value = false
  }
}

const resetReviewForm = () => Object.assign(reviewForm, emptyReviewForm())

const openCreateEditor = () => {
  editingId.value = null
  resetReviewForm()
  editorOpen.value = true
}

const openEditEditor = (review) => {
  editingId.value = review.id
  Object.assign(reviewForm, emptyReviewForm(), review, {
    review_date: review.review_date || '',
    sentiment_score: review.sentiment_score ?? ''
  })
  editorOpen.value = true
}

const closeEditor = () => {
  if (!editorSaving.value) editorOpen.value = false
}

const saveReview = async () => {
  if (!String(reviewForm.data_index).trim() || !reviewForm.review_content.trim()) {
    showMessage('data_index 和评论内容不能为空', 'error')
    return
  }
  editorSaving.value = true
  try {
    const isEdit = Boolean(editingId.value)
    const response = await fetch(
      `${API_BASE_URL}/admin/reviews${isEdit ? `/${editingId.value}` : ''}`,
      {
        method: isEdit ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify(reviewForm)
      }
    )
    const result = await parseApiResult(response)
    showMessage(result.message || (isEdit ? '评论已更新' : '评论已新增'), 'success')
    editorOpen.value = false
    await loadReviews(isEdit ? reviewPage.value : 1)
    await refreshAfterDatabaseChange()
  } catch (error) {
    showMessage(error.message, 'error')
  } finally {
    editorSaving.value = false
  }
}

const deleteReview = async (review) => {
  if (!window.confirm(`确定删除编号 ${review.data_index} 的评论吗？删除后无法恢复。`)) return
  try {
    const response = await fetch(`${API_BASE_URL}/admin/reviews/${review.id}`, {
      method: 'DELETE',
      headers: authHeaders()
    })
    const result = await parseApiResult(response)
    showMessage(result.message || '评论已删除', 'success')
    const targetPage = reviews.value.length === 1 && reviewPage.value > 1
      ? reviewPage.value - 1
      : reviewPage.value
    await loadReviews(targetPage)
    await refreshAfterDatabaseChange()
  } catch (error) {
    showMessage(error.message, 'error')
  }
}

const clearAllReviews = async () => {
  if (!window.confirm(`数据库中共有 ${reviewTotal.value} 条评论，确定全部清空吗？`)) return
  const confirmation = window.prompt('此操作无法恢复。请输入“全部清空”继续：')
  if (confirmation !== '全部清空') {
    showMessage('已取消清空', 'error')
    return
  }
  try {
    const response = await fetch(`${API_BASE_URL}/admin/reviews`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ confirmation: 'CLEAR_ALL_REVIEWS' })
    })
    const result = await parseApiResult(response)
    showMessage(result.message || '数据库已清空', 'success')
    await loadReviews(1)
    await refreshAfterDatabaseChange()
  } catch (error) {
    showMessage(error.message, 'error')
  }
}

onMounted(() => loadReviews(1))

const downloadTemplate = () => {
  const columns = [
    'data_index',
    '用户名',
    '电脑配置',
    '评论内容',
    '有用数',
    '重复购买情况',
    '评分',
    '内存',
    '硬盘',
    'date',
    '产品系列',
    '评论长度',
    '月份',
    '评论分词',
    '评论分词_去停用词',
    '情感分数',
    '评论关键词',
    '情感标签',
    'TFIDF向量'
  ]

  const blob = new Blob([`\uFEFF${columns.join(',')}\n`], {
    type: 'text/csv;charset=utf-8'
  })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = '舆情数据导入模板.csv'
  link.click()
  URL.revokeObjectURL(url)
}

const addRecord = (status, result = {}) => {
  importRecords.value.unshift({
    id: Date.now(),
    fileName: selectedFile.value?.name || '-',
    time: new Date().toLocaleString('zh-CN', { hour12: false }),
    total: result.total ?? result.total_rows ?? '-',
    success: result.success ?? result.imported_rows ?? '-',
    failed: result.failed ?? result.failed_rows ?? '-',
    status
  })
}

const uploadFile = () => {
  if (!selectedFile.value || isUploading.value) return

  isUploading.value = true
  importResult.value = null
  progress.value = 0
  message.value = ''

  const formData = new FormData()
  formData.append('file', selectedFile.value)

  const xhr = new XMLHttpRequest()
  xhr.open('POST', `${API_BASE_URL}/api/admin/import`)

  const token = localStorage.getItem('token')
  if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)

  xhr.upload.onprogress = (event) => {
    if (event.lengthComputable) {
      progress.value = Math.min(95, Math.round((event.loaded / event.total) * 95))
    }
  }

  xhr.onload = async () => {
    isUploading.value = false

    let result = {}
    try {
      result = JSON.parse(xhr.responseText || '{}')
    } catch {
      result = {}
    }

    if (xhr.status >= 200 && xhr.status < 300) {
      progress.value = 100
      importResult.value = {
        total: result.total ?? result.total_rows ?? 0,
        success: result.success ?? result.imported_rows ?? 0,
        failed: result.failed ?? result.failed_rows ?? 0
      }
      showMessage('数据已成功导入数据库', 'success')
      addRecord('success', result)
      await loadReviews(1)
      await refreshAfterDatabaseChange()
      return
    }

    progress.value = 0
    showMessage(result.message || `导入失败（${xhr.status}）`, 'error')
    addRecord('failed', result)
  }

  xhr.onerror = () => {
    isUploading.value = false
    progress.value = 0
    showMessage('无法连接后端服务，请确认 Flask 已启动', 'error')
    addRecord('failed')
  }

  xhr.send(formData)
}
</script>

<template>
  <section class="data-import-page">
    <div class="page-header">
      <div>
        <div class="breadcrumb">管理员功能 / 数据导入</div>
        <h1>数据导入</h1>
        <p>上传评论数据文件，系统将校验字段并写入舆情数据库。</p>
      </div>

      <button class="template-button" type="button" @click="downloadTemplate">
        <svg viewBox="0 0 24 24">
          <path d="M12 3v12" />
          <path d="m7 10 5 5 5-5" />
          <path d="M5 21h14" />
        </svg>
        下载导入模板
      </button>
    </div>

    <div class="content-grid">
      <div class="main-column">
        <div class="panel upload-panel">
          <div class="panel-heading">
            <div>
              <h2>上传数据文件</h2>
              <p>请先下载模板，并保持表头名称与顺序一致。</p>
            </div>
            <span class="step-badge">步骤 1</span>
          </div>

          <div
            class="drop-zone"
            :class="{ dragging: isDragging, selected: selectedFile }"
            @click="openFilePicker"
            @dragenter.prevent="isDragging = true"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="handleDrop"
          >
            <input
              ref="fileInput"
              type="file"
              accept=".csv,.xls,.xlsx"
              @change="handleFileChange"
            >

            <template v-if="!selectedFile">
              <div class="upload-icon">
                <svg viewBox="0 0 24 24">
                  <path d="M12 16V4" />
                  <path d="m7 9 5-5 5 5" />
                  <path d="M5 14v5h14v-5" />
                </svg>
              </div>
              <h3>拖拽文件到此处，或点击选择文件</h3>
              <p>支持 CSV、XLS、XLSX，单个文件最大 50 MB</p>
              <button class="choose-button" type="button">选择文件</button>
            </template>

            <template v-else>
              <div class="file-card" @click.stop>
                <div class="file-type">{{ fileExtension }}</div>
                <div class="file-details">
                  <strong>{{ selectedFile.name }}</strong>
                  <span>{{ formattedFileSize }} · 等待导入</span>
                </div>
                <button
                  class="remove-button"
                  type="button"
                  :disabled="isUploading"
                  aria-label="移除文件"
                  @click="removeFile"
                >
                  <svg viewBox="0 0 24 24">
                    <path d="M6 6l12 12M18 6 6 18" />
                  </svg>
                </button>
              </div>
            </template>
          </div>

          <div v-if="selectedFile" class="upload-actions">
            <div class="upload-status">
              <template v-if="isUploading || progress">
                <div class="progress-meta">
                  <span>{{ isUploading ? '正在上传并处理数据...' : '处理完成' }}</span>
                  <strong>{{ progress }}%</strong>
                </div>
                <div class="progress-track">
                  <span :style="{ width: `${progress}%` }"></span>
                </div>
              </template>
              <span v-else>文件校验通过，可以开始导入</span>
            </div>

            <button
              class="import-button"
              type="button"
              :disabled="isUploading"
              @click="uploadFile"
            >
              <svg v-if="!isUploading" viewBox="0 0 24 24">
                <path d="M12 3v12" />
                <path d="m7 10 5 5 5-5" />
                <path d="M4 20h16" />
              </svg>
              <span v-else class="spinner"></span>
              {{ isUploading ? '正在导入' : '开始导入' }}
            </button>
          </div>

          <div v-if="message" class="message-box" :class="messageType">
            <svg v-if="messageType === 'success'" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="9" />
              <path d="m8 12 2.5 2.5L16.5 9" />
            </svg>
            <svg v-else viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="9" />
              <path d="M12 7v6M12 17h.01" />
            </svg>
            {{ message }}
          </div>
        </div>

        <div class="panel database-panel">
          <div class="database-toolbar">
            <div>
              <h2>已导入数据管理</h2>
              <p>直接管理数据库中的评论数据。</p>
            </div>
            <div class="database-actions">
              <button class="danger-outline-button" type="button" :disabled="!reviewTotal" @click="clearAllReviews">全部清空</button>
              <button class="primary-small-button" type="button" @click="openCreateEditor">＋ 新增评论</button>
            </div>
          </div>

          <div class="search-row">
            <input v-model="reviewKeyword" type="search" placeholder="搜索用户名、评论、产品系列或配置" @keyup.enter="loadReviews(1)">
            <button type="button" @click="loadReviews(1)">搜索</button>
            <button v-if="reviewKeyword" class="text-button" type="button" @click="reviewKeyword = ''; loadReviews(1)">重置</button>
            <span>共 {{ reviewTotal }} 条</span>
          </div>

          <div v-if="reviewsError" class="management-error">{{ reviewsError }}</div>
          <div class="table-wrap database-table-wrap">
            <table class="database-table">
              <thead>
                <tr>
                  <th>data_index</th>
                  <th>用户</th>
                  <th>评论内容</th>
                  <th>评分</th>
                  <th>产品系列</th>
                  <th>配置</th>
                  <th>日期</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="reviewsLoading"><td colspan="8" class="table-state">正在读取数据库...</td></tr>
                <tr v-else-if="!reviews.length"><td colspan="8" class="table-state">数据库中暂无评论数据</td></tr>
                <template v-else>
                  <tr v-for="review in reviews" :key="review.id">
                    <td>{{ review.data_index }}</td>
                    <td>{{ review.username || '-' }}</td>
                    <td><div class="review-preview" :title="review.review_content">{{ review.review_content }}</div></td>
                    <td><span class="rating-badge">{{ review.rating ?? '-' }}</span></td>
                    <td>{{ review.product_series || '-' }}</td>
                    <td>{{ [review.memory, review.disk].filter(Boolean).join(' / ') || '-' }}</td>
                    <td>{{ review.review_date || '-' }}</td>
                    <td>
                      <div class="row-actions">
                        <button type="button" @click="openEditEditor(review)">编辑</button>
                        <button class="delete-row-button" type="button" @click="deleteReview(review)">删除</button>
                      </div>
                    </td>
                  </tr>
                </template>
              </tbody>
            </table>
          </div>

          <div class="pagination-row">
            <button type="button" :disabled="reviewPage <= 1 || reviewsLoading" @click="loadReviews(reviewPage - 1)">上一页</button>
            <span>第 {{ reviewPage }} / {{ reviewPages }} 页</span>
            <button type="button" :disabled="reviewPage >= reviewPages || reviewsLoading" @click="loadReviews(reviewPage + 1)">下一页</button>
          </div>
        </div>

        <div v-if="importResult" class="result-grid">
          <div class="result-card total">
            <span>数据总行数</span>
            <strong>{{ importResult.total }}</strong>
          </div>
          <div class="result-card success">
            <span>成功导入</span>
            <strong>{{ importResult.success }}</strong>
          </div>
          <div class="result-card failed">
            <span>导入失败</span>
            <strong>{{ importResult.failed }}</strong>
          </div>
        </div>

        <div class="panel records-panel">
          <div class="panel-heading records-heading">
            <div>
              <h2>本次导入记录</h2>
              <p>当前页面完成的文件导入记录。</p>
            </div>
            <span class="record-count">{{ importRecords.length }} 条</span>
          </div>

          <div v-if="importRecords.length" class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>文件名称</th>
                  <th>导入时间</th>
                  <th>总行数</th>
                  <th>成功</th>
                  <th>失败</th>
                  <th>状态</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="record in importRecords" :key="record.id">
                  <td class="file-name-cell">{{ record.fileName }}</td>
                  <td>{{ record.time }}</td>
                  <td>{{ record.total }}</td>
                  <td class="success-text">{{ record.success }}</td>
                  <td class="failed-text">{{ record.failed }}</td>
                  <td>
                    <span class="status-tag" :class="record.status">
                      {{ record.status === 'success' ? '已完成' : '失败' }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-else class="empty-records">
            <svg viewBox="0 0 24 24">
              <path d="M5 4h14v16H5z" />
              <path d="M8 8h8M8 12h8M8 16h5" />
            </svg>
            <span>暂无导入记录</span>
          </div>
        </div>
      </div>

      <aside class="side-column">
        <div class="panel guide-panel">
          <div class="guide-title">
            <div class="guide-icon">
              <svg viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="9" />
                <path d="M12 11v5M12 8h.01" />
              </svg>
            </div>
            <div>
              <h2>导入说明</h2>
              <p>上传前请仔细检查文件</p>
            </div>
          </div>

          <ol class="guide-list">
            <li>
              <span>1</span>
              <div>
                <strong>使用标准模板</strong>
                <p>不要修改或删除模板中的字段名称。</p>
              </div>
            </li>
            <li>
              <span>2</span>
              <div>
                <strong>检查必填字段</strong>
                <p>用户名、评论内容、评分和日期不能为空。</p>
              </div>
            </li>
            <li>
              <span>3</span>
              <div>
                <strong>统一日期格式</strong>
                <p>日期建议使用 YYYY-MM-DD 格式。</p>
              </div>
            </li>
            <li>
              <span>4</span>
              <div>
                <strong>避免重复导入</strong>
                <p>系统将根据 data_index 判断重复数据。</p>
              </div>
            </li>
          </ol>
        </div>

        <div class="panel field-panel">
          <div class="field-heading">
            <h2>模板字段</h2>
            <span>19 列</span>
          </div>
          <div class="field-tags">
            <span>data_index</span>
            <span>用户名</span>
            <span>电脑配置</span>
            <span>评论内容</span>
            <span>有用数</span>
            <span>评分</span>
            <span>内存</span>
            <span>硬盘</span>
            <span>date</span>
            <span>产品系列</span>
            <span>情感分数</span>
            <span>情感标签</span>
            <span>+ 7 个字段</span>
          </div>
        </div>
      </aside>
    </div>

    <div v-if="editorOpen" class="modal-backdrop" @click.self="closeEditor">
      <form class="review-modal" @submit.prevent="saveReview">
        <div class="modal-header">
          <div>
            <h2>{{ editingId ? '编辑评论' : '新增评论' }}</h2>
            <p>保存后会更新数据库和分析缓存。</p>
          </div>
          <button type="button" aria-label="关闭" @click="closeEditor">×</button>
        </div>

        <div class="form-grid">
          <label><span>data_index *</span><input v-model.number="reviewForm.data_index" type="number" required></label>
          <label><span>用户名</span><input v-model="reviewForm.username" type="text"></label>
          <label class="form-wide"><span>评论内容 *</span><textarea v-model="reviewForm.review_content" rows="4" required></textarea></label>
          <label><span>评分（1–5）</span><input v-model.number="reviewForm.rating" type="number" min="1" max="5" step="0.1"></label>
          <label><span>评论日期</span><input v-model="reviewForm.review_date" type="date"></label>
          <label><span>产品系列</span><input v-model="reviewForm.product_series" type="text"></label>
          <label><span>电脑配置</span><input v-model="reviewForm.computer_config" type="text"></label>
          <label><span>内存</span><input v-model="reviewForm.memory" type="text" placeholder="例如 16G"></label>
          <label><span>硬盘</span><input v-model="reviewForm.disk" type="text" placeholder="例如 1T"></label>
          <label><span>有用数</span><input v-model.number="reviewForm.helpful_count" type="number" min="0"></label>
          <label><span>重复购买</span><select v-model="reviewForm.repeat_purchase"><option value="否">否</option><option value="是">是</option></select></label>
          <label><span>情感分数</span><input v-model.number="reviewForm.sentiment_score" type="number" step="0.01"></label>
          <label><span>情感标签</span><select v-model="reviewForm.sentiment_label"><option value="">未设置</option><option value="正面">正面</option><option value="中性">中性</option><option value="负面">负面</option></select></label>
          <label class="form-wide"><span>评论关键词</span><input v-model="reviewForm.keywords" type="text" placeholder="多个关键词可用空格或逗号分隔"></label>
        </div>

        <div class="modal-footer">
          <button class="cancel-button" type="button" @click="closeEditor">取消</button>
          <button class="save-button" type="submit" :disabled="editorSaving">{{ editorSaving ? '保存中...' : '保存' }}</button>
        </div>
      </form>
    </div>
  </section>
</template>

<style scoped>
.data-import-page {
  min-height: calc(100vh - var(--header-height, 72px));
  padding: 30px 32px 42px;
  color: #17233b;
  background: #f5f7fb;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  max-width: 1440px;
  margin: 0 auto 24px;
}

.breadcrumb {
  margin-bottom: 9px;
  color: #8b97aa;
  font-size: 12px;
}

.page-header h1 {
  margin: 0;
  color: #14213a;
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.5px;
}

.page-header p {
  margin: 8px 0 0;
  color: #7a879b;
  font-size: 14px;
}

button {
  font: inherit;
}

.template-button,
.import-button,
.choose-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 0;
  cursor: pointer;
}

.template-button {
  height: 40px;
  padding: 0 16px;
  border: 1px solid #dce3ee;
  border-radius: 8px;
  color: #38506f;
  background: #ffffff;
  font-size: 13px;
  font-weight: 600;
  box-shadow: 0 3px 10px rgba(27, 48, 82, 0.04);
}

.template-button:hover {
  border-color: #b7c8e3;
  color: #1f5fd0;
  background: #f9fbff;
}

.template-button svg,
.import-button svg {
  width: 17px;
  height: 17px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 310px;
  gap: 22px;
  max-width: 1440px;
  margin: 0 auto;
}

.main-column,
.side-column {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 22px;
}

.panel {
  border: 1px solid #e4e9f1;
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 5px 18px rgba(26, 45, 76, 0.04);
}

.upload-panel {
  padding: 24px;
}

.panel-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 20px;
}

.panel-heading h2,
.guide-title h2,
.field-heading h2 {
  margin: 0;
  color: #17233b;
  font-size: 16px;
  font-weight: 700;
}

.panel-heading p,
.guide-title p {
  margin: 6px 0 0;
  color: #8a96a8;
  font-size: 12px;
}

.step-badge {
  padding: 5px 10px;
  border-radius: 12px;
  color: #2767d5;
  background: #edf4ff;
  font-size: 11px;
  font-weight: 600;
}

.drop-zone {
  display: flex;
  min-height: 278px;
  padding: 28px;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  border: 2px dashed #cdd8e8;
  border-radius: 11px;
  background:
    linear-gradient(rgba(249, 251, 254, 0.9), rgba(249, 251, 254, 0.9)),
    repeating-linear-gradient(45deg, #f5f8fc 0, #f5f8fc 8px, #ffffff 8px, #ffffff 16px);
  cursor: pointer;
  transition: 0.2s ease;
}

.drop-zone:hover,
.drop-zone.dragging {
  border-color: #5c8ee4;
  background: #f5f9ff;
}

.drop-zone.selected {
  min-height: 150px;
  cursor: default;
}

.drop-zone input {
  display: none;
}

.upload-icon {
  display: grid;
  width: 58px;
  height: 58px;
  margin-bottom: 16px;
  place-items: center;
  border-radius: 16px;
  color: #2d6fd8;
  background: #eaf2ff;
}

.upload-icon svg {
  width: 27px;
  height: 27px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.7;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.drop-zone h3 {
  margin: 0;
  color: #263750;
  font-size: 15px;
  font-weight: 650;
}

.drop-zone > p {
  margin: 8px 0 18px;
  color: #8a96a8;
  font-size: 12px;
}

.choose-button {
  height: 36px;
  padding: 0 18px;
  border-radius: 7px;
  color: #2d68ca;
  background: #eaf2ff;
  font-size: 12px;
  font-weight: 600;
}

.file-card {
  display: flex;
  width: min(590px, 100%);
  padding: 17px 18px;
  align-items: center;
  gap: 14px;
  border: 1px solid #dce5f2;
  border-radius: 10px;
  background: #ffffff;
  box-shadow: 0 4px 12px rgba(35, 61, 96, 0.05);
}

.file-type {
  display: grid;
  width: 48px;
  height: 48px;
  flex-shrink: 0;
  place-items: center;
  border-radius: 9px;
  color: #168451;
  background: #eaf8f1;
  font-size: 10px;
  font-weight: 800;
}

.file-details {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 5px;
}

.file-details strong {
  overflow: hidden;
  color: #263750;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-details span {
  color: #8b97aa;
  font-size: 11px;
}

.remove-button {
  display: grid;
  width: 32px;
  height: 32px;
  padding: 0;
  place-items: center;
  border: 0;
  border-radius: 7px;
  color: #8c99ab;
  background: transparent;
  cursor: pointer;
}

.remove-button:hover {
  color: #d94b56;
  background: #fff1f2;
}

.remove-button svg {
  width: 17px;
  height: 17px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
}

.upload-actions {
  display: flex;
  min-height: 58px;
  margin-top: 18px;
  align-items: center;
  justify-content: space-between;
  gap: 22px;
}

.upload-status {
  min-width: 0;
  flex: 1;
  color: #7c899b;
  font-size: 12px;
}

.progress-meta {
  display: flex;
  margin-bottom: 8px;
  justify-content: space-between;
  gap: 15px;
}

.progress-meta strong {
  color: #2767d5;
}

.progress-track {
  height: 6px;
  overflow: hidden;
  border-radius: 8px;
  background: #e8edf4;
}

.progress-track span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #3377e5, #62a2ff);
  transition: width 0.25s ease;
}

.import-button {
  min-width: 126px;
  height: 40px;
  padding: 0 20px;
  border-radius: 8px;
  color: #ffffff;
  background: linear-gradient(135deg, #2f73df, #245fc4);
  font-size: 13px;
  font-weight: 600;
  box-shadow: 0 7px 16px rgba(37, 100, 204, 0.22);
}

.import-button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 9px 19px rgba(37, 100, 204, 0.28);
}

.import-button:disabled {
  cursor: not-allowed;
  opacity: 0.68;
}

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.42);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: spin 0.75s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.message-box {
  display: flex;
  margin-top: 16px;
  padding: 11px 13px;
  align-items: center;
  gap: 9px;
  border-radius: 8px;
  font-size: 12px;
}

.message-box svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.message-box.success {
  color: #14744b;
  background: #eaf8f1;
}

.message-box.error {
  color: #b93e49;
  background: #fff0f1;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

.result-card {
  position: relative;
  padding: 18px 20px;
  overflow: hidden;
  border: 1px solid #e4e9f1;
  border-radius: 10px;
  background: #ffffff;
}

.result-card::before {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  width: 3px;
  content: "";
}

.result-card.total::before {
  background: #3479e4;
}

.result-card.success::before {
  background: #24a56a;
}

.result-card.failed::before {
  background: #e85a65;
}

.result-card span {
  display: block;
  color: #8793a5;
  font-size: 11px;
}

.result-card strong {
  display: block;
  margin-top: 7px;
  color: #1b2a43;
  font-size: 24px;
}

.records-panel {
  padding: 22px 24px 24px;
}

.records-heading {
  align-items: center;
}

.record-count {
  color: #7c899b;
  font-size: 12px;
}

.table-wrap {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

th {
  padding: 11px 13px;
  color: #8290a4;
  background: #f7f9fc;
  font-weight: 600;
  text-align: left;
}

td {
  padding: 13px;
  border-bottom: 1px solid #edf0f5;
  color: #647287;
}

.file-name-cell {
  max-width: 230px;
  overflow: hidden;
  color: #35465f;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.success-text {
  color: #168451;
}

.failed-text {
  color: #cf4853;
}

.status-tag {
  display: inline-flex;
  padding: 4px 8px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 600;
}

.status-tag.success {
  color: #14744b;
  background: #eaf8f1;
}

.status-tag.failed {
  color: #b93e49;
  background: #fff0f1;
}

.empty-records {
  display: flex;
  min-height: 120px;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 10px;
  color: #a0aabb;
  font-size: 12px;
}

.empty-records svg {
  width: 30px;
  height: 30px;
  fill: none;
  stroke: #b6c0cf;
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.guide-panel,
.field-panel {
  padding: 21px;
}

.guide-title {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 18px;
  border-bottom: 1px solid #edf0f5;
}

.guide-icon {
  display: grid;
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  place-items: center;
  border-radius: 10px;
  color: #2d6fd8;
  background: #edf4ff;
}

.guide-icon svg {
  width: 20px;
  height: 20px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.7;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.guide-list {
  display: flex;
  margin: 20px 0 0;
  padding: 0;
  flex-direction: column;
  gap: 20px;
  list-style: none;
}

.guide-list li {
  display: flex;
  gap: 12px;
}

.guide-list li > span {
  display: grid;
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  place-items: center;
  border-radius: 50%;
  color: #3973d2;
  background: #edf4ff;
  font-size: 10px;
  font-weight: 700;
}

.guide-list strong {
  display: block;
  color: #38485f;
  font-size: 12px;
}

.guide-list p {
  margin: 5px 0 0;
  color: #909bad;
  font-size: 11px;
  line-height: 1.6;
}

.field-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.field-heading span {
  color: #8c98aa;
  font-size: 11px;
}

.field-tags {
  display: flex;
  margin-top: 16px;
  flex-wrap: wrap;
  gap: 7px;
}

.field-tags span {
  padding: 5px 8px;
  border: 1px solid #e1e7f0;
  border-radius: 6px;
  color: #67758a;
  background: #f8fafc;
  font-size: 10px;
}

.database-panel { padding: 24px; }
.database-toolbar, .database-actions, .search-row, .pagination-row, .row-actions, .modal-header, .modal-footer { display: flex; align-items: center; }
.database-toolbar { justify-content: space-between; gap: 18px; margin-bottom: 18px; }
.database-toolbar h2, .review-modal h2 { margin: 0; color: #17233b; font-size: 16px; }
.database-toolbar p, .review-modal p { margin: 6px 0 0; color: #8a96a8; font-size: 12px; }
.database-actions { gap: 10px; }
.danger-outline-button, .primary-small-button, .search-row button, .pagination-row button, .row-actions button, .modal-footer button { border: 0; border-radius: 7px; cursor: pointer; font-size: 12px; font-weight: 600; }
.danger-outline-button, .primary-small-button { height: 36px; padding: 0 14px; }
.danger-outline-button { border: 1px solid #f0b9bd; color: #c53c47; background: #fff; }
.primary-small-button, .save-button { color: #fff; background: #2d6fd8; }
.search-row { gap: 9px; margin-bottom: 15px; }
.search-row input { width: min(390px, 100%); height: 36px; padding: 0 12px; border: 1px solid #dce3ee; border-radius: 7px; outline: none; }
.search-row button { height: 36px; padding: 0 14px; color: #fff; background: #496d9e; }
.search-row .text-button { color: #60718a; background: #eef2f7; }
.search-row span { margin-left: auto; color: #7f8da1; font-size: 12px; }
.management-error { margin-bottom: 12px; padding: 10px 12px; border-radius: 7px; color: #b73742; background: #fff0f1; font-size: 12px; }
.database-table-wrap { border: 1px solid #e6eaf1; border-radius: 9px; }
.database-table { min-width: 1050px; }
.review-preview { max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rating-badge { display: inline-grid; min-width: 29px; height: 25px; place-items: center; border-radius: 6px; color: #a96b00; background: #fff4d8; font-weight: 700; }
.row-actions { gap: 7px; }
.row-actions button { padding: 6px 9px; color: #2664c3; background: #edf4ff; }
.row-actions .delete-row-button { color: #c83c47; background: #fff0f1; }
.table-state { padding: 34px !important; color: #8a96a8; text-align: center; }
.pagination-row { justify-content: flex-end; gap: 12px; margin-top: 15px; color: #738096; font-size: 12px; }
.pagination-row button { padding: 7px 12px; color: #385b8c; background: #edf3fb; }
button:disabled { opacity: .48; cursor: not-allowed; }
.modal-backdrop { position: fixed; z-index: 1000; inset: 0; display: grid; padding: 28px; place-items: center; background: rgba(14, 26, 47, .48); }
.review-modal { width: min(820px, 100%); max-height: calc(100vh - 56px); overflow: auto; border-radius: 14px; background: #fff; box-shadow: 0 22px 70px rgba(10, 23, 43, .25); }
.modal-header { justify-content: space-between; padding: 21px 24px; border-bottom: 1px solid #e8ecf2; }
.modal-header > button { width: 34px; height: 34px; border: 0; border-radius: 8px; color: #68768b; background: #f1f4f8; cursor: pointer; font-size: 23px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px 18px; padding: 22px 24px; }
.form-grid label { display: flex; min-width: 0; flex-direction: column; gap: 7px; }
.form-grid label > span { color: #53637a; font-size: 12px; font-weight: 600; }
.form-grid input, .form-grid textarea, .form-grid select { width: 100%; box-sizing: border-box; padding: 9px 11px; border: 1px solid #dce3ed; border-radius: 7px; color: #24334b; background: #fff; font: inherit; font-size: 13px; outline: none; }
.form-grid textarea { resize: vertical; }
.form-wide { grid-column: 1 / -1; }
.modal-footer { justify-content: flex-end; gap: 10px; padding: 16px 24px 22px; border-top: 1px solid #edf0f4; }
.modal-footer button { min-width: 88px; height: 38px; }
.cancel-button { color: #596a80; background: #eef2f6; }

@media (max-width: 1120px) {
  .content-grid {
    grid-template-columns: 1fr;
  }

  .side-column {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 720px) {
  .data-import-page {
    padding: 22px 16px 32px;
  }

  .page-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .template-button {
    width: 100%;
  }

  .upload-panel {
    padding: 18px;
  }

  .drop-zone {
    min-height: 240px;
    padding: 22px 16px;
    text-align: center;
  }

  .upload-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .import-button {
    width: 100%;
  }

  .result-grid,
  .side-column {
    grid-template-columns: 1fr;
  }

  .database-toolbar,
  .search-row {
    align-items: stretch;
    flex-direction: column;
  }

  .search-row input {
    width: 100%;
  }

  .search-row span {
    margin-left: 0;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .form-wide {
    grid-column: auto;
  }
}
</style>
