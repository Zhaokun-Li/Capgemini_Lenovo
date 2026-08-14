<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import {
  getReviewOptions,
  getReviews,
  getReviewStatistics
} from '../api/review'

const filters = reactive({
  keyword: '',
  product_series: '',
  sentiment: '',
  memory: '',
  disk: '',
  risk_level: '',
  issue_type: '',
  min_rating: '',
  start_date: '',
  end_date: ''
})

const options = ref({
  sentiments: [],
  product_series: [],
  memory: [],
  disk: [],
  risk_levels: [],
  issue_types: []
})

const reviews = ref([])

const statistics = ref({
  summary: {},
  sentiment: []
})

const pagination = ref({
  page: 1,
  pages: 1,
  total: 0,
  has_next: false,
  has_prev: false
})

const loading = ref(false)
const error = ref('')
const detailItem = ref(null)
const sortDirection = ref('desc')

const negativeCount = computed(() => {
  const item = statistics.value.sentiment.find(
    value => value.name === '负面'
  )

  return Number(item?.count || 0)
})

const positiveCount = computed(() => {
  const item = statistics.value.sentiment.find(
    value => value.name === '正面'
  )

  return Number(item?.count || 0)
})

const queryParams = (page = 1) => {
  const params = {
    page,
    page_size: 10,
    sort_by: 'date',
    sort_order: sortDirection.value
  }

  Object.entries(filters).forEach(([key, value]) => {
    if (String(value).trim()) {
      params[key] = String(value).trim()
    }
  })

  return params
}

async function loadData(page = 1) {
  loading.value = true
  error.value = ''

  try {
    const params = queryParams(page)

    const [
      reviewResult,
      statisticResult
    ] = await Promise.all([
      getReviews(params),
      getReviewStatistics(params)
    ])

    reviews.value = reviewResult.data || []

    pagination.value =
      reviewResult.pagination || pagination.value

    statistics.value =
      statisticResult.data || statistics.value
  } catch (exception) {
    error.value =
      '数据加载失败，请确认 Flask 后端已启动'
  } finally {
    loading.value = false
  }
}

async function applyFilters() {
  if (
    filters.start_date &&
    filters.end_date &&
    filters.start_date > filters.end_date
  ) {
    error.value = '开始日期不能晚于结束日期'
    return
  }

  await loadData(1)
}

async function resetFilters() {
  Object.keys(filters).forEach(key => {
    filters[key] = ''
  })

  await loadData(1)
}

async function changeSort() {
  sortDirection.value =
    sortDirection.value === 'desc'
      ? 'asc'
      : 'desc'

  await loadData(1)
}

function exportCsv() {
  const rows = [
    [
      '索引',
      '用户',
      '产品系列',
      '评分',
      '内存',
      '硬盘',
      '情感',
      '模型标签',
      '差评概率',
      '问题类型',
      '风险等级',
      '有用数',
      '日期',
      '评论内容'
    ]
  ]

  reviews.value.forEach(item => {
    rows.push([
      item.data_index,
      item.username || '',
      item.product_series || '',
      item.rating ?? '',
      item.memory || '',
      item.disk || '',
      item.sentiment_label || '',
      item.model_label || '',
      item.negative_probability ?? '',
      item.issue_type || '',
      item.risk_level || '',
      item.helpful_count || 0,
      item.review_date || '',
      item.review_content || ''
    ])
  })

  const csv =
    '\uFEFF' +
    rows
      .map(row =>
        row
          .map(
            cell =>
              `"${String(cell).replaceAll(
                '"',
                '""'
              )}"`
          )
          .join(',')
      )
      .join('\n')

  const url = URL.createObjectURL(
    new Blob(
      [csv],
      {
        type: 'text/csv;charset=utf-8'
      }
    )
  )

  const link = document.createElement('a')

  link.href = url
  link.download = '舆情监控筛选结果.csv'
  link.click()

  URL.revokeObjectURL(url)
}

function sentimentClass(value) {
  return {
    正面: 'positive',
    中性: 'neutral',
    负面: 'negative'
  }[value] || 'neutral'
}

onMounted(async () => {
  try {
    const result = await getReviewOptions()

    options.value =
      result.data || options.value

    await loadData(1)
  } catch (exception) {
    error.value =
      '筛选项加载失败，请检查后端接口'
  }
})

const refreshAfterDatabaseChange = async () => {
  try {
    const result = await getReviewOptions()
    options.value = result.data || options.value
    await loadData(1)
  } catch {
    error.value = '数据库已更新，但页面刷新失败'
  }
}

onMounted(() => window.addEventListener('database-data-updated', refreshAfterDatabaseChange))
onBeforeUnmount(() => window.removeEventListener('database-data-updated', refreshAfterDatabaseChange))
</script>

<template>
  <div class="monitor-page">

    <main>
      <section class="page-heading">
        <div>
          <p>MONITORING</p>

          <h1>舆情监控</h1>

          <span>
            通过产品、情感、配置和日期筛选数据库中的真实评论。
          </span>
        </div>

        <div class="heading-actions">
          <button
            class="secondary"
            @click="exportCsv"
          >
            ⇩ 导出当前页
          </button>

          <button
            class="primary"
            @click="applyFilters"
          >
            ↻ 刷新数据
          </button>
        </div>
      </section>

      <section class="stat-grid">
        <article>
          <div class="stat-icon blue">
            ◎
          </div>

          <div>
            <span>筛选结果总量</span>

            <strong>
              {{
                Number(
                  statistics.summary.total || 0
                ).toLocaleString()
              }}
            </strong>

            <small class="up">
              数据库实时统计
            </small>
          </div>
        </article>

        <article>
          <div class="stat-icon red">
            !
          </div>

          <div>
            <span>负面评论</span>

            <strong>
              {{ negativeCount.toLocaleString() }}
            </strong>

            <small class="down">
              当前筛选范围
            </small>
          </div>
        </article>

        <article>
          <div class="stat-icon orange">
            ★
          </div>

          <div>
            <span>平均评分</span>

            <strong>
              {{
                statistics.summary.average_rating
                || 0
              }}
            </strong>

            <small>
              <b>对应 rating 字段</b>
            </small>
          </div>
        </article>

        <article>
          <div class="stat-icon green">
            ✓
          </div>

          <div>
            <span>正面评论</span>

            <strong>
              {{ positiveCount.toLocaleString() }}
            </strong>

            <small class="up">
              当前筛选范围
            </small>
          </div>
        </article>
      </section>

      <section class="filter-card">
        <div class="filter-head">
          <div>
            <h2>筛选条件</h2>

            <span>
              通过多维条件快速定位目标舆情
            </span>
          </div>

          <button @click="resetFilters">
            ↻ 重置条件
          </button>
        </div>

        <div class="filters">
          <label class="wide">
            <span>关键词</span>

            <div class="input-wrap">
              ⌕

              <input
                v-model="filters.keyword"
                placeholder="评论、配置、用户名或关键词"
                @keyup.enter="applyFilters"
              >
            </div>
          </label>

          <label>
            <span>产品系列</span>

            <select v-model="filters.product_series">
              <option value="">
                全部产品
              </option>

              <option
                v-for="item in options.product_series"
                :key="item"
                :value="item"
              >
                {{ item }}
              </option>
            </select>
          </label>

          <label>
            <span>情感倾向</span>

            <select v-model="filters.sentiment">
              <option value="">
                全部情感
              </option>

              <option
                v-for="item in options.sentiments"
                :key="item"
                :value="item"
              >
                {{ item }}
              </option>
            </select>
          </label>

          <label>
            <span>内存规格</span>

            <select v-model="filters.memory">
              <option value="">
                全部内存
              </option>

              <option
                v-for="item in options.memory"
                :key="item"
                :value="item"
              >
                {{ item }}
              </option>
            </select>
          </label>

          <label>
            <span>硬盘规格</span>

            <select v-model="filters.disk">
              <option value="">
                全部硬盘
              </option>

              <option
                v-for="item in options.disk"
                :key="item"
                :value="item"
              >
                {{ item }}
              </option>
            </select>
          </label>

          <label>
            <span>风险等级</span>
            <select v-model="filters.risk_level">
              <option value="">全部风险</option>
              <option v-for="item in options.risk_levels" :key="item" :value="item">{{ item }}</option>
            </select>
          </label>

          <label>
            <span>问题类型</span>
            <select v-model="filters.issue_type">
              <option value="">全部问题</option>
              <option v-for="item in options.issue_types" :key="item" :value="item">{{ item }}</option>
            </select>
          </label>

          <label>
            <span>最低评分</span>

            <select v-model="filters.min_rating">
              <option value="">
                全部评分
              </option>

              <option value="5">
                5 分
              </option>

              <option value="4">
                4 分及以上
              </option>

              <option value="3">
                3 分及以上
              </option>

              <option value="2">
                2 分及以上
              </option>

              <option value="1">
                1 分及以上
              </option>
            </select>
          </label>

          <label class="date-range">
            <span>评论日期</span>

            <div>
              <input
                v-model="filters.start_date"
                type="date"
              >

              <b>至</b>

              <input
                v-model="filters.end_date"
                type="date"
              >
            </div>
          </label>

          <button
              class="query"
              @click="applyFilters"
          >
            ⌕ 查询舆情
          </button>
        </div>

        <p
            v-if="error"
            class="empty"
        >
          {{ error }}
        </p>
      </section>      <section class="table-card">
        <div class="table-head">
          <div>
            <h2>舆情数据</h2>

            <span>
              共找到
              <b>{{ pagination.total || 0 }}</b>
              条相关评论
            </span>
          </div>

          <div class="batch">
            <button @click="changeSort">
              日期
              {{ sortDirection === 'desc' ? '↓' : '↑' }}
            </button>
          </div>
        </div>

        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>索引</th>
                <th>评论内容</th>
                <th>产品 / 配置</th>
                <th>情感倾向</th>
                <th>模型分析</th>
                <th>评分</th>
                <th>有用数</th>
                <th>评论日期</th>
                <th>操作</th>
              </tr>
            </thead>

            <tbody>
              <tr
                v-for="item in reviews"
                :key="item.id"
              >
                <td>
                  {{ item.data_index }}
                </td>

                <td class="content-cell">
                  <div>
                    <strong @click="detailItem = item">
                      {{ item.username || '匿名用户' }}
                    </strong>

                    <p>
                      {{ item.review_content }}
                    </p>

                    <div class="keywords">
                      <span v-if="item.keywords">
                        #{{ item.keywords }}
                      </span>
                    </div>
                  </div>
                </td>

                <td>
                  <strong class="product-name">
                    {{ item.product_series || '-' }}
                  </strong>

                  <span class="source-name">
                    {{
                      item.computer_config ||
                      `${item.memory || '-'} / ${item.disk || '-'}`
                    }}
                  </span>
                </td>

                <td>
                  <span
                    class="pill sentiment"
                    :class="sentimentClass(
                      item.sentiment_label
                    )"
                  >
                    <i></i>
                    {{ item.sentiment_label || '未分类' }}
                  </span>

                  <small class="confidence">
                    得分
                    {{
                      Number(
                        item.sentiment_score || 0
                      ).toFixed(3)
                    }}
                  </small>
                </td>

                <td>
                  <strong>{{ item.model_label || '-' }}</strong>
                  <small class="confidence">差评概率 {{ item.negative_probability == null ? '-' : `${(Number(item.negative_probability) * 100).toFixed(1)}%` }}</small>
                  <small class="confidence">{{ item.issue_type || '未识别问题' }} · {{ item.risk_level || '未分级' }}</small>
                </td>

                <td>
                  <strong class="heat">
                    {{ item.rating ?? '-' }}
                  </strong>
                </td>

                <td>
                  <strong class="heat">
                    {{
                      Number(
                        item.helpful_count || 0
                      ).toLocaleString()
                    }}
                  </strong>
                </td>

                <td>
                  <span class="date">
                    {{ item.review_date || '-' }}
                  </span>
                </td>

                <td>
                  <button
                    class="view"
                    @click="detailItem = item"
                  >
                    查看
                  </button>
                </td>
              </tr>

              <tr v-if="loading">
                <td
                  colspan="9"
                  class="empty"
                >
                  正在加载数据……
                </td>
              </tr>

              <tr v-else-if="!reviews.length">
                <td
                  colspan="9"
                  class="empty"
                >
                  没有找到符合条件的评论，请调整筛选条件
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="pagination">
          <span>
            第 {{ pagination.page || 1 }} /
            {{ pagination.pages || 1 }} 页，共
            {{ pagination.total || 0 }} 条
          </span>

          <div>
            <button
              :disabled="!pagination.has_prev"
              @click="loadData(pagination.page - 1)"
            >
              ‹ 上一页
            </button>

            <button class="active">
              {{ pagination.page || 1 }}
            </button>

            <button
              :disabled="!pagination.has_next"
              @click="loadData(pagination.page + 1)"
            >
              下一页 ›
            </button>
          </div>
        </div>
      </section>
    </main>

    <div
      v-if="detailItem"
      class="modal-mask"
      @click.self="detailItem = null"
    >
      <article class="detail-modal">
        <button
          class="close"
          @click="detailItem = null"
        >
          ×
        </button>

        <p class="eyebrow">
          REVIEW DETAIL
        </p>

        <h2>
          {{
            detailItem.product_series ||
            '产品评论详情'
          }}
        </h2>

        <div class="detail-tags">
          <span
            class="pill sentiment"
            :class="sentimentClass(
              detailItem.sentiment_label
            )"
          >
            {{
              detailItem.sentiment_label ||
              '未分类'
            }}
          </span>

          <span>
            {{ detailItem.memory || '内存未知' }}
          </span>

          <span>
            {{ detailItem.disk || '硬盘未知' }}
          </span>
        </div>

        <div class="detail-meta">
          <div>
            <small>评论用户</small>

            <strong>
              {{ detailItem.username || '匿名用户' }}
            </strong>
          </div>

          <div>
            <small>评论日期</small>

            <strong>
              {{ detailItem.review_date || '-' }}
            </strong>
          </div>

          <div>
            <small>评分</small>

            <strong>
              {{ detailItem.rating ?? '-' }}
            </strong>
          </div>

          <div>
            <small>有用数</small>

            <strong>
              {{ detailItem.helpful_count || 0 }}
            </strong>
          </div>
        </div>

        <div class="detail-meta">
          <div><small>模型标签</small><strong>{{ detailItem.model_label || '-' }}</strong></div>
          <div><small>差评概率</small><strong>{{ detailItem.negative_probability == null ? '-' : `${(Number(detailItem.negative_probability) * 100).toFixed(1)}%` }}</strong></div>
          <div><small>问题类型</small><strong>{{ detailItem.issue_type || '-' }}</strong></div>
          <div><small>风险等级</small><strong>{{ detailItem.risk_level || '-' }}</strong></div>
        </div>

        <div class="original">
          <h3>评论原文</h3>

          <p>
            {{ detailItem.review_content }}
          </p>
        </div>

        <div
          v-if="detailItem.keywords"
          class="keyword-block"
        >
          <h3>评论关键词</h3>

          <span>
            # {{ detailItem.keywords }}
          </span>
        </div>

        <div class="detail-footer">
          <button
            class="secondary"
            @click="detailItem = null"
          >
            关闭
          </button>
        </div>
      </article>
    </div>
  </div>
</template>
<style scoped>
* {
  box-sizing: border-box;
}

button,
input,
select {
  font: inherit;
}

button {
  cursor: pointer;
}

.monitor-page {
  min-height: 100vh;
  color: #172033;
  background: #f5f7fb;
}


.brand strong,
.brand small {
  display: block;
}

.brand strong {
  color: #ffffff;
  font-size: 13px;
  letter-spacing: 0.5px;
}

.brand small {
  margin-top: 4px;
  color: #828ca8;
  font-size: 11px;
}

.nav-title {
  margin: 0 12px 10px;
  color: #66718f;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.5px;
}

.service-card > div:first-child {
  display: flex;
  align-items: center;
  gap: 8px;
}

.service-card i {
  width: 7px;
  height: 7px;
  background: #35d59a;
  border-radius: 50%;
  box-shadow: 0 0 0 4px rgba(53, 213, 154, 0.12);
}

.service-card strong {
  color: #e6e9f3;
  font-size: 11px;
}

.service-card small {
  display: block;
  margin: 8px 0 10px;
  color: #69748f;
  font-size: 10px;
}

.progress {
  height: 3px;
  overflow: hidden;
  background: #27304f;
  border-radius: 4px;
}

.progress span {
  display: block;
  width: 86%;
  height: 100%;
  background: linear-gradient(90deg, #3bce9a, #55e1b0);
}


.help b {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  color: #909ab6;
  border: 1px solid #333c5b;
  border-radius: 50%;
}

.help strong,
.help small {
  display: block;
}

.help strong {
  color: #aeb6ca;
  font-size: 11px;
}

.help small {
  margin-top: 3px;
  color: #606b88;
  font-size: 10px;
}

main {
  width: 100%;
  min-height: 100vh;
  margin: 0;
  padding: 8px 0 38px;
}

.page-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 25px;
}

.page-heading p,
.eyebrow {
  margin: 0 0 7px;
  color: #6271f3;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 2px;
}

.page-heading h1 {
  margin: 0 0 8px;
  color: #172033;
  font-size: 29px;
  letter-spacing: -0.6px;
}

.page-heading > div > span {
  color: #7d8798;
  font-size: 13px;
}

.heading-actions {
  display: flex;
  gap: 10px;
}

.heading-actions button,
.detail-footer button {
  height: 40px;
  padding: 0 17px;
  font-size: 12px;
  font-weight: 600;
  border-radius: 8px;
}

.primary {
  color: #ffffff;
  background: #5765ea;
  border: 1px solid #5765ea;
  box-shadow: 0 6px 14px rgba(87, 101, 234, 0.2);
}

.secondary {
  color: #525d70;
  background: #ffffff;
  border: 1px solid #dfe4ec;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 15px;
  margin-bottom: 18px;
}

.stat-grid article {
  min-height: 116px;
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 20px;
  background: #ffffff;
  border: 1px solid #e8ebf1;
  border-radius: 12px;
  box-shadow: 0 4px 15px rgba(33, 43, 67, 0.035);
}

.stat-icon {
  flex: 0 0 auto;
  width: 43px;
  height: 43px;
  display: grid;
  place-items: center;
  font-size: 17px;
  font-weight: 700;
  border-radius: 11px;
}

.stat-icon.blue {
  color: #4b65e5;
  background: #edf1ff;
}

.stat-icon.red {
  color: #ef5567;
  background: #ffeff1;
}

.stat-icon.orange {
  color: #e69b36;
  background: #fff5e5;
}

.stat-icon.green {
  color: #2aad81;
  background: #eaf9f3;
}

.stat-grid article span,
.stat-grid article strong,
.stat-grid article small {
  display: block;
}

.stat-grid article > div:last-child > span {
  color: #8a93a3;
  font-size: 11px;
}

.stat-grid article > div:last-child > strong {
  margin: 5px 0 4px;
  color: #1c2639;
  font-size: 24px;
  letter-spacing: -0.5px;
}

.stat-grid article small {
  color: #99a1af;
  font-size: 10px;
}

.stat-grid article small.up,
.stat-grid article small b {
  color: #2eaf84;
  font-weight: 600;
}

.stat-grid article small.down {
  color: #ef5c6d;
}

.filter-card,
.table-card {
  margin-bottom: 18px;
  background: #ffffff;
  border: 1px solid #e7eaf0;
  border-radius: 12px;
  box-shadow: 0 5px 18px rgba(27, 37, 61, 0.035);
}

.filter-card {
  padding: 20px;
}

.filter-head,
.table-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.filter-head {
  margin-bottom: 18px;
}

.filter-head h2,
.table-head h2 {
  margin: 0 0 4px;
  color: #1d2738;
  font-size: 15px;
}

.filter-head span,
.table-head span {
  color: #939baa;
  font-size: 11px;
}

.filter-head button {
  padding: 7px 10px;
  color: #667085;
  font-size: 11px;
  background: transparent;
  border: 0;
}

.filters {
  display: grid;
  grid-template-columns: 1.4fr repeat(3, minmax(130px, 1fr));
  gap: 14px;
  align-items: end;
}

.filters label {
  display: grid;
  gap: 7px;
}

.filters label > span {
  color: #667085;
  font-size: 11px;
  font-weight: 600;
}

.filters .wide {
  grid-column: span 2;
}

.filters input,
.filters select {
  width: 100%;
  height: 39px;
  padding: 0 11px;
  color: #3c4658;
  background: #ffffff;
  border: 1px solid #dfe4eb;
  border-radius: 8px;
  outline: none;
  transition: 0.2s ease;
}

.filters input:focus,
.filters select:focus {
  border-color: #7180ec;
  box-shadow: 0 0 0 3px rgba(91, 107, 232, 0.1);
}

.input-wrap {
  height: 39px;
  display: flex;
  align-items: center;
  gap: 7px;
  padding-left: 11px;
  color: #9ba3b0;
  border: 1px solid #dfe4eb;
  border-radius: 8px;
}

.input-wrap:focus-within {
  border-color: #7180ec;
  box-shadow: 0 0 0 3px rgba(91, 107, 232, 0.1);
}

.input-wrap input {
  height: 37px;
  padding-left: 0;
  border: 0;
  box-shadow: none;
}

.input-wrap input:focus {
  box-shadow: none;
}

.date-range {
  grid-column: span 2;
}

.date-range > div {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 8px;
}

.date-range b {
  color: #969ead;
  font-size: 11px;
  font-weight: 400;
}

.query {
  height: 39px;
  color: #ffffff;
  font-size: 12px;
  font-weight: 600;
  background: #5967ea;
  border: 0;
  border-radius: 8px;
  box-shadow: 0 6px 14px rgba(89, 103, 234, 0.18);
}.table-card {
  overflow: hidden;
}

.table-head {
  padding: 19px 20px;
  border-bottom: 1px solid #edf0f4;
}

.table-head b {
  color: #5967ea;
}

.batch {
  display: flex;
  gap: 8px;
}

.batch button {
  height: 34px;
  padding: 0 13px;
  color: #626c7d;
  font-size: 11px;
  background: #ffffff;
  border: 1px solid #dfe4eb;
  border-radius: 7px;
}

.table-scroll {
  overflow-x: auto;
}

table {
  width: 100%;
  min-width: 1080px;
  border-collapse: collapse;
}

thead {
  background: #fafbfc;
}

th {
  padding: 12px 15px;
  color: #8d96a5;
  font-size: 10px;
  font-weight: 700;
  text-align: left;
  white-space: nowrap;
  border-bottom: 1px solid #e9edf2;
}

td {
  padding: 15px;
  color: #596477;
  font-size: 11px;
  vertical-align: middle;
  border-bottom: 1px solid #edf0f4;
}

tbody tr {
  transition: background 0.2s ease;
}

tbody tr:hover {
  background: #fafbff;
}

tbody tr:last-child td {
  border-bottom: 0;
}

.content-cell {
  width: 32%;
  min-width: 300px;
}

.content-cell strong {
  color: #263144;
  font-size: 11px;
  cursor: pointer;
}

.content-cell strong:hover {
  color: #5967ea;
}

.content-cell p {
  max-width: 430px;
  margin: 5px 0 7px;
  overflow: hidden;
  color: #626c7c;
  line-height: 1.55;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.keywords span {
  max-width: 330px;
  padding: 3px 7px;
  overflow: hidden;
  color: #6977dc;
  font-size: 9px;
  text-overflow: ellipsis;
  white-space: nowrap;
  background: #f0f2ff;
  border-radius: 5px;
}

.product-name,
.source-name {
  display: block;
}

.product-name {
  max-width: 155px;
  overflow: hidden;
  color: #273247;
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-name {
  max-width: 170px;
  margin-top: 5px;
  overflow: hidden;
  color: #939baa;
  font-size: 9px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 9px;
  font-size: 10px;
  font-weight: 600;
  white-space: nowrap;
  border-radius: 14px;
}

.pill i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
}

.sentiment.positive {
  color: #25966f;
  background: #e9f8f2;
}

.sentiment.positive i {
  background: #2bb586;
}

.sentiment.neutral {
  color: #b07825;
  background: #fff5df;
}

.sentiment.neutral i {
  background: #e3a03c;
}

.sentiment.negative {
  color: #d94f60;
  background: #ffedf0;
}

.sentiment.negative i {
  background: #ed5d6e;
}

.confidence {
  display: block;
  margin-top: 6px;
  color: #9aa2af;
  font-size: 9px;
}

.heat {
  color: #364155;
  font-size: 12px;
}

.date {
  color: #6f798a;
  white-space: nowrap;
}

.view {
  padding: 6px 10px;
  color: #5967df;
  font-size: 10px;
  font-weight: 600;
  background: #f0f2ff;
  border: 0;
  border-radius: 6px;
}

.view:hover {
  color: #ffffff;
  background: #5967df;
}

.empty {
  padding: 30px;
  color: #929bab;
  text-align: center;
}

.filter-card > .empty {
  margin: 16px 0 0;
  padding: 11px;
  color: #d65263;
  font-size: 11px;
  background: #fff1f3;
  border-radius: 7px;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 15px;
  padding: 15px 20px;
  border-top: 1px solid #edf0f4;
}

.pagination > span {
  color: #929baa;
  font-size: 10px;
}

.pagination > div {
  display: flex;
  gap: 6px;
}

.pagination button {
  min-width: 33px;
  height: 31px;
  padding: 0 10px;
  color: #687284;
  font-size: 10px;
  background: #ffffff;
  border: 1px solid #e0e5ec;
  border-radius: 6px;
}

.pagination button:hover:not(:disabled),
.pagination button.active {
  color: #ffffff;
  background: #5967e7;
  border-color: #5967e7;
}

.pagination button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.modal-mask {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(15, 22, 42, 0.58);
  backdrop-filter: blur(4px);
}

.detail-modal {
  position: relative;
  width: min(680px, 100%);
  max-height: calc(100vh - 48px);
  padding: 27px;
  overflow-y: auto;
  background: #ffffff;
  border-radius: 15px;
  box-shadow: 0 24px 70px rgba(17, 25, 54, 0.28);
}

.detail-modal .close {
  position: absolute;
  top: 18px;
  right: 18px;
  width: 32px;
  height: 32px;
  color: #7c8696;
  font-size: 20px;
  line-height: 1;
  background: #f4f6f9;
  border: 0;
  border-radius: 8px;
}

.detail-modal h2 {
  margin: 0 45px 14px 0;
  color: #1d2739;
  font-size: 23px;
}

.detail-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-bottom: 21px;
}

.detail-tags > span:not(.pill) {
  display: inline-flex;
  align-items: center;
  padding: 5px 9px;
  color: #667085;
  font-size: 10px;
  background: #f2f4f7;
  border-radius: 14px;
}

.detail-meta {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 20px;
}

.detail-meta > div {
  padding: 13px;
  background: #f7f8fb;
  border: 1px solid #edf0f4;
  border-radius: 9px;
}

.detail-meta small,
.detail-meta strong {
  display: block;
}

.detail-meta small {
  margin-bottom: 6px;
  color: #919aaa;
  font-size: 9px;
}

.detail-meta strong {
  overflow: hidden;
  color: #344054;
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.original,
.keyword-block {
  margin-top: 14px;
  padding: 17px;
  background: #fafbfc;
  border: 1px solid #eceff4;
  border-radius: 10px;
}

.original h3,
.keyword-block h3 {
  margin: 0 0 10px;
  color: #344054;
  font-size: 12px;
}

.original p {
  margin: 0;
  color: #586376;
  font-size: 12px;
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-word;
}

.keyword-block span {
  display: inline-block;
  color: #5d6bdb;
  font-size: 11px;
  line-height: 1.7;
  word-break: break-word;
}

.detail-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 21px;
}

@media (max-width: 1200px) {
  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .filters {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .filters .wide,
  .date-range {
    grid-column: span 2;
  }
}


  .service-card,
  .help {
    display: none;
  }


  main {
    padding: 25px 18px;
  }

  .global-search {
    width: min(420px, 58vw);
  }

  .top-actions > div:last-of-type,
  .chevron {
    display: none;
  }

  .page-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .detail-meta {
    grid-template-columns: repeat(2, 1fr);
  }

@media (max-width: 560px) {
  .sidebar nav,
  .stat-grid,
  .filters {
    grid-template-columns: 1fr;
  }

  .filters .wide,
  .date-range {
    grid-column: span 1;
  }

  .date-range > div {
    grid-template-columns: 1fr;
  }

  .date-range b {
    display: none;
  }

  .global-search {
    width: calc(100vw - 115px);
  }

  .global-search kbd,
  .icon-button {
    display: none;
  }

  .heading-actions {
    width: 100%;
  }

  .heading-actions button {
    flex: 1;
  }

  .pagination {
    align-items: flex-start;
    flex-direction: column;
  }

  .detail-modal {
    padding: 21px;
  }

  .detail-meta {
    grid-template-columns: 1fr;
  }
}
</style>
