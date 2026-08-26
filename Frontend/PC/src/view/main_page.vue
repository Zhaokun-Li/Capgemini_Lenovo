<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { getReviewStatistics, getReviews } from '../api/review'

const statistics = ref({
  summary: {},
  sentiment: [],
  rating: [],
  product_series: [],
  memory: [],
  disk: [],
  monthly: []
})

const reviews = ref([])
const pagination = ref({
  page: 1,
  pages: 1,
  total: 0,
  has_next: false,
  has_prev: false
})

const page = ref(1)
const keyword = ref('')
const sentiment = ref('')
const loading = ref(false)
const error = ref('')

const colors = [
  '#2f69d9',
  '#e5a83d',
  '#d65357',
  '#58a77a',
  '#7c6ee6',
  '#38a8a4'
]

const formatNumber = (value) =>
  Number(value || 0).toLocaleString()

const maxCount = (items) =>
  Math.max(
    1,
    ...items.map(
      (item) => Number(item.count || 0)
    )
  )

const barWidth = (count, items) =>
  `${Number(count || 0) * 100 / maxCount(items)}%`

const sentimentTotal = computed(() =>
  statistics.value.sentiment.reduce(
    (sum, item) =>
      sum + Number(item.count || 0),
    0
  )
)

const sentimentStyle = computed(() => {
  let start = 0

  const parts =
    statistics.value.sentiment.map(
      (item, index) => {
        const end =
          start
          + Number(item.count || 0)
          * 100
          / Math.max(
            1,
            sentimentTotal.value
          )

        const part =
          `${colors[index]} ${start}% ${end}%`

        start = end

        return part
      }
    )

  return {
    background:
      `conic-gradient(${parts.join(',')})`
  }
})

const loadStatistics = async () => {
  const result =
    await getReviewStatistics()

  statistics.value =
    result.data || statistics.value
}

const loadReviews = async (
  targetPage = 1
) => {
  loading.value = true
  error.value = ''

  try {
    const result = await getReviews({
      page: targetPage,
      page_size: 20,
      keyword:
        keyword.value.trim() || undefined,
      sentiment:
        sentiment.value || undefined
    })

    reviews.value =
      result.data || []

    pagination.value =
      result.pagination
      || pagination.value

    page.value =
      pagination.value.page
      || targetPage
  } catch (exception) {
    error.value =
      '数据加载失败，请检查 Flask 后端是否正常运行'
  } finally {
    loading.value = false
  }
}

const search = () =>
  loadReviews(1)

const reset = () => {
  keyword.value = ''
  sentiment.value = ''

  loadReviews(1)
}

onMounted(async () => {
  try {
    await Promise.all([
      loadStatistics(),
      loadReviews()
    ])
  } catch (exception) {
    error.value =
      '统计接口加载失败，请重启 Flask 后端'
  }
})

const refreshAfterDatabaseChange = () => Promise.all([
  loadStatistics(),
  loadReviews(1)
]).catch(() => {
  error.value = '数据库已更新，但页面刷新失败'
})

onMounted(() => window.addEventListener('database-data-updated', refreshAfterDatabaseChange))
onBeforeUnmount(() => window.removeEventListener('database-data-updated', refreshAfterDatabaseChange))
</script>

<template>
  <main class="database-dashboard">
    <header class="page-heading">
      <div>
        <p>DATABASE OVERVIEW</p>
        <h1>产品评论数据总览</h1>

        <span>
          所有内容均来自 MySQL 的
          product_review 表
        </span>
      </div>

      <div class="date-box">
        最新评论日期：
        {{
          statistics.summary.latest_date
          || '暂无'
        }}
      </div>
    </header>

    <section class="summary-grid">
      <article>
        <span>评论总数</span>

        <strong>
          {{
            formatNumber(
              statistics.summary.total
            )
          }}
        </strong>

        <small>
          对应 id / data_index
        </small>
      </article>

      <article>
        <span>平均评分</span>

        <strong>
          {{
            statistics.summary.average_rating
            || 0
          }}
        </strong>

        <small>对应 rating</small>
      </article>

      <article>
        <span>高风险评论</span>

        <strong>
          {{
            formatNumber(
              statistics.summary.high_risk_count
            )
          }}
        </strong>

        <small>
          对应 risk_level
        </small>
      </article>

      <article>
        <span>平均差评概率</span>

        <strong>
          {{
            `${(Number(statistics.summary.average_negative_probability || 0) * 100).toFixed(1)}%`
          }}
        </strong>

        <small>
          对应 negative_probability
        </small>
      </article>
    </section>

    <section class="chart-grid">
      <article class="panel">
        <h2>情感标签分布</h2>
        <p>对应 sentiment_label</p>

        <div class="donut-wrap">
          <div
            class="donut"
            :style="sentimentStyle"
          >
            <span>
              {{
                formatNumber(
                  sentimentTotal
                )
              }}

              <small>条评论</small>
            </span>
          </div>

          <div class="legend">
            <div
              v-for="(item, index)
                in statistics.sentiment"
              :key="item.name"
            >
              <i
                :style="{
                  background: colors[index]
                }"
              ></i>

              <span>{{ item.name }}</span>

              <strong>
                {{ item.count }}（{{
                  (
                    item.count
                    * 100
                    / Math.max(
                      1,
                      sentimentTotal
                    )
                  ).toFixed(1)
                }}%）
              </strong>
            </div>
          </div>
        </div>
      </article>

      <article class="panel">
        <h2>评分分布</h2>
        <p>对应 rating</p>

        <div class="bars">
          <div
            v-for="item
              in statistics.rating"
            :key="item.name"
          >
            <span>{{ item.name }}</span>

            <i>
              <b
                :style="{
                  width: barWidth(
                    item.count,
                    statistics.rating
                  )
                }"
              ></b>
            </i>

            <strong>
              {{ item.count }}
            </strong>
          </div>
        </div>
      </article>

      <article class="panel wide">
        <h2>产品系列评论量</h2>
        <p>对应 product_series</p>

        <div class="bars">
          <div
            v-for="item
              in statistics.product_series"
            :key="item.name"
          >
            <span>{{ item.name }}</span>

            <i>
              <b
                :style="{
                  width: barWidth(
                    item.count,
                    statistics.product_series
                  )
                }"
              ></b>
            </i>

            <strong>
              {{ item.count }}
            </strong>
          </div>
        </div>
      </article>

      <article class="panel">
        <h2>内存规格分布</h2>
        <p>对应 memory</p>

        <div class="bars">
          <div
            v-for="item
              in statistics.memory"
            :key="item.name"
          >
            <span>{{ item.name }}</span>

            <i>
              <b
                :style="{
                  width: barWidth(
                    item.count,
                    statistics.memory
                  )
                }"
              ></b>
            </i>

            <strong>
              {{ item.count }}
            </strong>
          </div>
        </div>
      </article>

      <article class="panel">
        <h2>硬盘规格分布</h2>
        <p>对应 disk</p>

        <div class="bars">
          <div
            v-for="item
              in statistics.disk"
            :key="item.name"
          >
            <span>{{ item.name }}</span>

            <i>
              <b
                :style="{
                  width: barWidth(
                    item.count,
                    statistics.disk
                  )
                }"
              ></b>
            </i>

            <strong>
              {{ item.count }}
            </strong>
          </div>
        </div>
      </article>

      <article class="panel wide">
        <h2>月度评论数量</h2>

        <p>
          对应 review_month，
          并按 review_date 排序
        </p>

        <div class="month-chart">
          <div
            v-for="item
              in statistics.monthly"
            :key="item.name"
          >
            <strong>
              {{ item.count }}
            </strong>

            <i
              :style="{
                height: barWidth(
                  item.count,
                  statistics.monthly
                )
              }"
            ></i>

            <span>{{ item.name }}</span>
          </div>
        </div>
      </article>
    </section>

    <section class="panel detail-panel">
      <div class="detail-heading">
        <div>
          <h2>数据库评论明细</h2>

          <p>
            共
            {{
              formatNumber(
                pagination.total
              )
            }}
            条
          </p>
        </div>

        <form @submit.prevent="search">
          <input
            v-model="keyword"
            placeholder="搜索评论、配置、关键词"
          >

          <select v-model="sentiment">
            <option value="">
              全部情感
            </option>

            <option value="正面">
              正面
            </option>

            <option value="中性">
              中性
            </option>

            <option value="负面">
              负面
            </option>
          </select>

          <button>查询</button>

          <button
            type="button"
            @click="reset"
          >
            重置
          </button>
        </form>
      </div>

      <p v-if="loading">
        正在加载……
      </p>

      <p
        v-else-if="error"
        class="error"
      >
        {{ error }}
      </p>

      <div
        v-else
        class="table-wrap"
      >
        <table>
          <thead>
            <tr>
              <th>索引</th>
              <th>用户</th>
              <th>产品系列</th>
              <th>配置</th>
              <th>评分</th>
              <th>内存</th>
              <th>硬盘</th>
              <th>情感</th>
              <th>有用数</th>
              <th>评论内容</th>
              <th>日期</th>
            </tr>
          </thead>

          <tbody>
            <tr
              v-for="review in reviews"
              :key="review.id"
            >
              <td>
                {{ review.data_index }}
              </td>

              <td>
                {{ review.username || '-' }}
              </td>

              <td>
                {{
                  review.product_series
                  || '-'
                }}
              </td>

              <td>
                {{
                  review.computer_config
                  || '-'
                }}
              </td>

              <td>
                {{ review.rating ?? '-' }}
              </td>

              <td>
                {{ review.memory || '-' }}
              </td>

              <td>
                {{ review.disk || '-' }}
              </td>

              <td>
                {{
                  review.sentiment_label
                  || '-'
                }}
              </td>

              <td>
                {{ review.helpful_count }}
              </td>

              <td class="content">
                {{ review.review_content }}
              </td>

              <td>
                {{
                  review.review_date
                  || '-'
                }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="pagination">
        <button
          :disabled="!pagination.has_prev"
          @click="loadReviews(page - 1)"
        >
          上一页
        </button>

        <span>
          第 {{ page }} /
          {{ pagination.pages || 1 }} 页
        </span>

        <button
          :disabled="!pagination.has_next"
          @click="loadReviews(page + 1)"
        >
          下一页
        </button>
      </div>
    </section>
  </main>
</template>

<style scoped>
.database-dashboard {
  min-height: 100vh;
  padding: 28px;
  background: #f3f6fa;
  color: #17233d;
  font-family: Arial, "Microsoft YaHei", sans-serif;
}

.page-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 22px;
}

.page-heading p {
  margin: 0 0 6px;
  color: #2f69d9;
  font-size: 12px;
  font-weight: 700;
}

.page-heading h1 {
  margin: 0 0 8px;
  font-size: 28px;
}

.page-heading span,
.panel p {
  color: #8b96aa;
}

.date-box {
  padding: 12px 18px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 18px;
  margin-bottom: 18px;
}

.summary-grid article,
.panel {
  background: #fff;
  border: 1px solid #e1e7ef;
  border-radius: 16px;
  box-shadow: 0 8px 24px rgba(22, 39, 70, 0.05);
}

.summary-grid article {
  padding: 22px;
}

.summary-grid span {
  display: block;
  color: #7c879b;
}

.summary-grid strong {
  display: block;
  margin: 12px 0;
  font-size: 30px;
}

.summary-grid small {
  color: #9ba5b6;
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 18px;
}

.chart-grid > * {
  min-width: 0;
}

.panel {
  min-width: 0;
  padding: 22px;
  overflow: hidden;
}

.panel h2 {
  margin: 0 0 5px;
  font-size: 18px;
}

.panel p {
  margin: 0 0 22px;
  font-size: 13px;
}

.wide {
  grid-column: span 2;
}

.donut-wrap {
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: space-around;
  gap: 24px;
}

.donut {
  width: 180px;
  height: 180px;
  flex: 0 0 180px;
  border-radius: 50%;
  display: grid;
  place-items: center;
}

.donut > span {
  width: 112px;
  height: 112px;
  border-radius: 50%;
  background: #fff;
  display: grid;
  place-items: center;
  font-size: 24px;
  font-weight: 700;
}

.donut small {
  display: block;
  color: #8993a5;
  font-size: 12px;
  font-weight: 400;
}

.legend {
  width: min(100%, 300px);
  min-width: 240px;
}

.legend div {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid #eef1f5;
}

.legend i {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.legend strong {
  margin-left: auto;
}

.bars > div {
  display: grid;
  grid-template-columns: 130px 1fr 55px;
  gap: 12px;
  align-items: center;
  margin: 13px 0;
}

.bars > div > span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bars i {
  height: 9px;
  background: #edf1f6;
  border-radius: 6px;
  overflow: hidden;
}

.bars b {
  display: block;
  height: 100%;
  background: #3973dd;
  border-radius: 6px;
}

.month-chart {
  height: 240px;
  display: flex;
  align-items: flex-end;
  gap: 12px;
  overflow-x: auto;
  padding-top: 20px;
}

.month-chart div {
  height: 100%;
  min-width: 54px;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: center;
}

.month-chart i {
  width: 30px;
  max-height: 180px;
  min-height: 3px;
  background: #3973dd;
  border-radius: 5px 5px 0 0;
}

.month-chart strong,
.month-chart span {
  font-size: 11px;
}

.detail-panel {
  margin-top: 18px;
}

.detail-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-heading form {
  display: flex;
  gap: 8px;
}

.detail-heading input,
.detail-heading select,
.detail-heading button,
.pagination button {
  padding: 9px 12px;
  border: 1px solid #dce3ed;
  border-radius: 8px;
  background: #fff;
}

.detail-heading button,
.pagination button {
  cursor: pointer;
}

.table-wrap {
  overflow: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  white-space: nowrap;
}

th,
td {
  padding: 12px;
  border-bottom: 1px solid #edf0f4;
  text-align: left;
  font-size: 13px;
}

.content {
  max-width: 320px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
  margin-top: 18px;
}

.error {
  color: #d65357;
}

@media (max-width: 900px) {
  .summary-grid,
  .chart-grid {
    grid-template-columns: 1fr;
  }

  .wide {
    grid-column: auto;
  }

  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .page-heading,
  .detail-heading {
    align-items: flex-start;
    flex-direction: column;
    gap: 15px;
  }

  .detail-heading form {
    flex-wrap: wrap;
  }

  .donut-wrap {
    flex-direction: column;
    gap: 20px;
  }

  .legend {
    width: 100%;
    min-width: 0;
  }
}

@media (max-width: 600px) {
  .database-dashboard {
    width: 100%;
    padding: 18px 12px 28px;
    overflow-x: hidden;
  }

  .page-heading h1 {
    font-size: 23px;
  }

  .date-box {
    width: 100%;
  }

  .summary-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .summary-grid article,
  .panel {
    width: 100%;
    min-width: 0;
    border-radius: 13px;
  }

  .panel {
    padding: 18px 16px;
  }

  .donut {
    width: 156px;
    height: 156px;
    flex-basis: 156px;
  }

  .donut > span {
    width: 96px;
    height: 96px;
    font-size: 21px;
  }

  .legend div {
    width: 100%;
  }

  .legend strong {
    overflow-wrap: anywhere;
    text-align: right;
  }

  .bars {
    width: 100%;
    min-width: 0;
  }

  .bars > div {
    width: 100%;
    min-width: 0;
    grid-template-columns: minmax(52px, 26%) minmax(0, 1fr) auto;
    gap: 8px;
  }

  .bars > div > span {
    min-width: 0;
  }

  .bars > div > strong {
    min-width: 28px;
    text-align: right;
  }

  .detail-heading form,
  .detail-heading input,
  .detail-heading select,
  .detail-heading button {
    width: 100%;
  }

  .pagination {
    justify-content: center;
    flex-wrap: wrap;
  }
}
</style>
