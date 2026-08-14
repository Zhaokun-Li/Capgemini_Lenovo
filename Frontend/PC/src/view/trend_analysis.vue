<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { analysisData, loadAnalysis } from '../store/analysisCache'

const selectedDays = ref(30)
const loading = ref(false)
const error = ref('')
const dashboard = ref({
  summary: {},
  sentiment: [],
  trend: [],
  products: [],
  hot_reviews: []
})
const analysis = ref({
  summary: {},
  issues: [],
  risk_trend: [],
  product_negative: [],
  rating_alignment: [],
  hot_reviews: []
})


const volumeChartEl = ref(null)
const sentimentChartEl = ref(null)
const productChartEl = ref(null)
const riskChartEl = ref(null)
const issueChartEl = ref(null)
const negativeProductChartEl = ref(null)
const alignmentChartEl = ref(null)
let volumeChart
let sentimentChart
let productChart
let riskChart
let issueChart
let negativeProductChart
let alignmentChart

const colors = {
  positive: '#3978e8',
  neutral: '#f2ad2f',
  negative: '#ef5962',
  total: '#5a8dee'
}

const trend = computed(() => dashboard.value.trend || [])
const products = computed(() => dashboard.value.products || [])
const issues = computed(() => analysis.value.issues || [])
const riskTrend = computed(() => analysis.value.risk_trend || [])
const productNegative = computed(() => analysis.value.product_negative || [])
const hotReviews = computed(() => analysis.value.hot_reviews || [])

const total = computed(() => {
  const summaryTotal = Number(
    dashboard.value.summary?.period_total ||
    dashboard.value.summary?.total ||
    0
  )
  if (summaryTotal) return summaryTotal
  return trend.value.reduce((sum, item) => {
    return sum + Number(item.positive || 0) + Number(item.neutral || 0) + Number(item.negative || 0)
  }, 0)
})

const currentVolume = computed(() => {
  const last = trend.value.at(-1) || {}
  return Number(last.positive || 0) + Number(last.neutral || 0) + Number(last.negative || 0)
})

const previousVolume = computed(() => {
  const previous = trend.value.at(-2) || {}
  return Number(previous.positive || 0) + Number(previous.neutral || 0) + Number(previous.negative || 0)
})

const dailyChange = computed(() => {
  if (!previousVolume.value) return 0
  return ((currentVolume.value - previousVolume.value) / previousVolume.value) * 100
})

const averageDaily = computed(() => {
  if (!trend.value.length) return 0
  return Math.round(total.value / trend.value.length)
})

const peak = computed(() => {
  if (!trend.value.length) return { date: '-', value: 0 }
  return trend.value
    .map(item => ({
      date: item.date,
      value: Number(item.positive || 0) + Number(item.neutral || 0) + Number(item.negative || 0)
    }))
    .sort((a, b) => b.value - a.value)[0]
})

const negativeRate = computed(() => {
  const item = (dashboard.value.sentiment || []).find(row => row.label === '负面')
  return Number(item?.percentage || 0)
})

const insights = computed(() => {
  const result = []
  if (peak.value.value) {
    result.push({
      tone: 'blue',
      title: '舆情峰值',
      text: `${formatDate(peak.value.date)}达到 ${peak.value.value} 条，为所选周期内最高点。`
    })
  }
  result.push({
    tone: dailyChange.value >= 0 ? 'orange' : 'green',
    title: dailyChange.value >= 0 ? '热度正在上升' : '热度有所回落',
    text: `最近一天舆情量较前一天${dailyChange.value >= 0 ? '增长' : '下降'} ${Math.abs(dailyChange.value).toFixed(1)}%。`
  })
  result.push({
    tone: negativeRate.value >= 20 ? 'red' : 'green',
    title: negativeRate.value >= 20 ? '负面情绪需关注' : '整体情绪稳定',
    text: `当前负面舆情占比为 ${negativeRate.value.toFixed(1)}%。`
  })
  return result
})

function formatNumber(value) {
  return Number(value || 0).toLocaleString()
}

function formatDate(value) {
  if (!value) return '-'
  return String(value).slice(5).replace('-', '/')
}

function signedPercent(value) {
  const number = Number(value || 0)
  return `${number >= 0 ? '+' : ''}${number.toFixed(1)}%`
}

async function loadData(force = false, suppliedData = null) {
  loading.value = true
  error.value = ''
  try {
    const source = suppliedData || await loadAnalysis(force) || {}
    const latest = source.trend_dashboard || {}
    const allTrend = latest.trend || []
    const latestDate = allTrend.length ? new Date(allTrend.at(-1).date) : null
    const cutoff = latestDate ? new Date(latestDate) : null
    cutoff?.setDate(cutoff.getDate() - selectedDays.value + 1)
    const periodTrend = cutoff
      ? allTrend.filter(item => new Date(item.date) >= cutoff)
      : []
    const periodTotal = periodTrend.reduce((sum, item) => (
      sum + Number(item.positive || 0) + Number(item.neutral || 0) + Number(item.negative || 0)
    ), 0)
    const filtered = {
      ...latest,
      summary: { ...(latest.summary || {}), period_total: periodTotal },
      trend: periodTrend
    }
    dashboard.value = filtered
    analysis.value = filtered
    await nextTick()
    renderCharts()
  } catch (exception) {
    error.value = '趋势缓存读取失败'
    await nextTick()
    renderCharts()
  } finally {
    loading.value = false
  }
}

function handleDatabaseUpdated(event) {
  loadData(false, event.detail?.data || analysisData.value || {})
}

function renderCharts() {
  if (volumeChartEl.value) volumeChart ||= echarts.init(volumeChartEl.value)
  if (sentimentChartEl.value) sentimentChart ||= echarts.init(sentimentChartEl.value)
  if (productChartEl.value) productChart ||= echarts.init(productChartEl.value)
  if (riskChartEl.value) riskChart ||= echarts.init(riskChartEl.value)
  if (issueChartEl.value) issueChart ||= echarts.init(issueChartEl.value)
  if (negativeProductChartEl.value) negativeProductChart ||= echarts.init(negativeProductChartEl.value)
  if (alignmentChartEl.value) alignmentChart ||= echarts.init(alignmentChartEl.value)

  const labels = trend.value.map(item => formatDate(item.date))
  const totals = trend.value.map(item =>
    Number(item.positive || 0) + Number(item.neutral || 0) + Number(item.negative || 0)
  )

  volumeChart?.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 48, right: 20, top: 28, bottom: 34 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: labels,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#dfe6f0' } },
      axisLabel: { color: '#8793a6', hideOverlap: true }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#8793a6' },
      splitLine: { lineStyle: { color: '#edf1f6' } }
    },
    series: [{
      name: '舆情总量',
      type: 'line',
      smooth: true,
      showSymbol: true,
      symbol: 'circle',
      symbolSize: 7,
      connectNulls: true,
      data: totals,
      lineStyle: { width: 3, color: colors.total },
      itemStyle: { color: colors.total },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(90,141,238,.28)' },
            { offset: 1, color: 'rgba(90,141,238,.02)' }
          ]
        }
      }
    }]
  }, true)

  sentimentChart?.setOption({
    tooltip: { trigger: 'axis' },
    legend: {
      top: 0,
      right: 4,
      itemWidth: 14,
      itemHeight: 8,
      textStyle: { color: '#68768b' }
    },
    grid: { left: 48, right: 20, top: 42, bottom: 34 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: labels,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#dfe6f0' } },
      axisLabel: { color: '#8793a6', hideOverlap: true }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#8793a6' },
      splitLine: { lineStyle: { color: '#edf1f6' } }
    },
    series: [
      ['正面', 'positive', colors.positive],
      ['中性', 'neutral', colors.neutral],
      ['负面', 'negative', colors.negative]
    ].map(([name, key, color]) => ({
      name,
      type: 'line',
      smooth: true,
      showSymbol: false,
      data: trend.value.map(item => Number(item[key] || 0)),
      lineStyle: { width: 2.4, color },
      itemStyle: { color }
    }))
  }, true)

  const productRows = products.value.slice(0, 6)
  productChart?.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 90, right: 32, top: 18, bottom: 28 },
    xAxis: {
      type: 'value',
      axisLabel: { color: '#8793a6' },
      splitLine: { lineStyle: { color: '#edf1f6' } }
    },
    yAxis: {
      type: 'category',
      inverse: true,
      data: productRows.map(item => item.name || item.product_series || '其他'),
      axisTick: { show: false },
      axisLine: { show: false },
      axisLabel: { color: '#59677c', width: 72, overflow: 'truncate' }
    },
    series: [{
      type: 'bar',
      data: productRows.map(item => Number(item.mentions || item.count || item.total || 0)),
      barWidth: 14,
      itemStyle: {
        borderRadius: [0, 7, 7, 0],
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 1,
          y2: 0,
          colorStops: [
            { offset: 0, color: '#3b78e7' },
            { offset: 1, color: '#75b8f5' }
          ]
        }
      }
    }]
  }, true)

  const riskLabels = riskTrend.value.map(item => formatDate(item.date))
  riskChart?.setOption({
    tooltip: { trigger: 'axis' },
    legend: { top: 0, right: 4, textStyle: { color: '#68768b' } },
    grid: { left: 48, right: 20, top: 42, bottom: 34 },
    xAxis: { type: 'category', data: riskLabels, axisLabel: { color: '#8793a6', hideOverlap: true }, axisTick: { show: false } },
    yAxis: { type: 'value', axisLabel: { color: '#8793a6' }, splitLine: { lineStyle: { color: '#edf1f6' } } },
    series: [
      ['高风险', 'high', '#ef5962'],
      ['中风险', 'medium', '#f2ad2f'],
      ['低风险', 'low', '#28af72']
    ].map(([name, key, color]) => ({
      name,
      type: 'line',
      smooth: true,
      showSymbol: false,
      data: riskTrend.value.map(item => Number(item[key] || 0)),
      lineStyle: { width: 2.4, color },
      itemStyle: { color }
    }))
  }, true)

  const issueRows = issues.value.slice(0, 8).reverse()
  issueChart?.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 92, right: 28, top: 18, bottom: 26 },
    xAxis: { type: 'value', axisLabel: { color: '#8793a6' }, splitLine: { lineStyle: { color: '#edf1f6' } } },
    yAxis: { type: 'category', data: issueRows.map(item => item.name), axisLabel: { color: '#59677c', width: 76, overflow: 'truncate' }, axisTick: { show: false }, axisLine: { show: false } },
    series: [{ type: 'bar', barWidth: 13, data: issueRows.map(item => item.count), itemStyle: { color: '#ef7c64', borderRadius: [0, 7, 7, 0] } }]
  }, true)

  const negativeRows = productNegative.value.slice(0, 8).reverse()
  negativeProductChart?.setOption({
    tooltip: { trigger: 'axis', formatter: params => `${params[0].name}<br/>差评率：${params[0].value}%` },
    grid: { left: 96, right: 38, top: 18, bottom: 26 },
    xAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%', color: '#8793a6' }, splitLine: { lineStyle: { color: '#edf1f6' } } },
    yAxis: { type: 'category', data: negativeRows.map(item => item.name), axisLabel: { color: '#59677c', width: 80, overflow: 'truncate' }, axisTick: { show: false }, axisLine: { show: false } },
    series: [{ type: 'bar', barWidth: 13, data: negativeRows.map(item => item.negative_rate), itemStyle: { color: '#df5965', borderRadius: [0, 7, 7, 0] } }]
  }, true)

  const alignmentRows = analysis.value.rating_alignment || []
  alignmentChart?.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, textStyle: { color: '#68768b' } },
    series: [{
      type: 'pie',
      radius: ['42%', '68%'],
      center: ['50%', '44%'],
      label: { formatter: '{b}\n{c}条', color: '#59677c' },
      data: alignmentRows.map((item, index) => ({
        ...item,
        value: item.count,
        itemStyle: { color: ['#3978e8', '#ef5962', '#45b890', '#f2ad2f'][index] }
      }))
    }]
  }, true)
}

function resizeCharts() {
  volumeChart?.resize()
  sentimentChart?.resize()
  productChart?.resize()
  riskChart?.resize()
  issueChart?.resize()
  negativeProductChart?.resize()
  alignmentChart?.resize()
}

onMounted(() => {
  loadData()
  window.addEventListener('resize', resizeCharts)
  window.addEventListener('database-data-updated', handleDatabaseUpdated)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  window.removeEventListener('database-data-updated', handleDatabaseUpdated)
  volumeChart?.dispose()
  sentimentChart?.dispose()
  productChart?.dispose()
  riskChart?.dispose()
  issueChart?.dispose()
  negativeProductChart?.dispose()
  alignmentChart?.dispose()
})
</script>

<template>
  <div class="trend-page">
    <header class="page-heading">
      <div>
        <h1>趋势洞察</h1>
        <p>分析舆情热度、情感变化及产品关注度的发展趋势</p>
      </div>
      <div class="period-switch" aria-label="趋势时间范围">
        <button
          v-for="days in [7, 30, 90]"
          :key="days"
          :class="{ active: selectedDays === days }"
          type="button"
          @click="selectedDays = days; loadData()"
        >
          近{{ days }}天
        </button>
      </div>
    </header>

    <div v-if="error" class="error-banner">
      <span>{{ error }}</span>
      <button type="button" @click="loadData">重新加载</button>
    </div>

    <section class="metric-grid">
      <article class="metric-card">
        <div class="metric-icon blue">趋</div>
        <div>
          <p>周期舆情总量</p>
          <strong>{{ formatNumber(total) }}</strong>
          <span>近 {{ selectedDays }} 天累计</span>
        </div>
      </article>
      <article class="metric-card">
        <div class="metric-icon cyan">均</div>
        <div>
          <p>日均舆情量</p>
          <strong>{{ formatNumber(averageDaily) }}</strong>
          <span>条 / 天</span>
        </div>
      </article>
      <article class="metric-card">
        <div class="metric-icon orange">峰</div>
        <div>
          <p>单日最高热度</p>
          <strong>{{ formatNumber(peak.value) }}</strong>
          <span>{{ formatDate(peak.date) }}</span>
        </div>
      </article>
      <article class="metric-card">
        <div class="metric-icon" :class="dailyChange >= 0 ? 'red' : 'green'">
          {{ dailyChange >= 0 ? '↑' : '↓' }}
        </div>
        <div>
          <p>最近一日环比</p>
          <strong :class="dailyChange >= 0 ? 'rise' : 'fall'">
            {{ signedPercent(dailyChange) }}
          </strong>
          <span>较前一日</span>
        </div>
      </article>
    </section>

    <section class="chart-grid">
      <article class="panel wide">
        <div class="panel-heading">
          <div>
            <h2>舆情热度趋势</h2>
            <p>每日评论总量变化</p>
          </div>
          <span class="legend-dot">舆情总量</span>
        </div>
        <div ref="volumeChartEl" class="chart"></div>
        <div v-if="!loading && !trend.length" class="empty">暂无趋势数据</div>
      </article>

      <article class="panel">
        <div class="panel-heading">
          <div>
            <h2>趋势分析结论</h2>
            <p>自动识别主要变化</p>
          </div>
        </div>
        <div class="insight-list">
          <div v-for="item in insights" :key="item.title" class="insight-item">
            <i :class="item.tone"></i>
            <div>
              <strong>{{ item.title }}</strong>
              <p>{{ item.text }}</p>
            </div>
          </div>
        </div>
      </article>

      <article class="panel wide">
        <div class="panel-heading">
          <div>
            <h2>情感倾向趋势</h2>
            <p>正面、中性与负面舆情的每日变化</p>
          </div>
        </div>
        <div ref="sentimentChartEl" class="chart"></div>
        <div v-if="!loading && !trend.length" class="empty">暂无情感趋势数据</div>
      </article>

      <article class="panel">
        <div class="panel-heading">
          <div>
            <h2>产品关注度排行</h2>
            <p>不同产品系列的舆情量</p>
          </div>
        </div>
        <div ref="productChartEl" class="chart"></div>
        <div v-if="!loading && !products.length" class="empty">暂无产品数据</div>
      </article>

      <article class="panel wide">
        <div class="panel-heading">
          <div>
            <h2>舆情风险趋势</h2>
            <p>高、中、低风险评论随时间的变化</p>
          </div>
        </div>
        <div ref="riskChartEl" class="chart"></div>
        <div v-if="!loading && !riskTrend.length" class="empty">暂无风险趋势数据</div>
      </article>

      <article class="panel">
        <div class="panel-heading">
          <div>
            <h2>主要问题分布</h2>
            <p>用户最集中反馈的问题类型</p>
          </div>
        </div>
        <div ref="issueChartEl" class="chart"></div>
        <div v-if="!loading && !issues.length" class="empty">暂无问题分类数据</div>
      </article>

      <article class="panel wide">
        <div class="panel-heading">
          <div>
            <h2>产品负面率排行</h2>
            <p>识别差评占比最高的产品系列</p>
          </div>
        </div>
        <div ref="negativeProductChartEl" class="chart"></div>
        <div v-if="!loading && !productNegative.length" class="empty">暂无产品负面率数据</div>
      </article>

      <article class="panel">
        <div class="panel-heading">
          <div>
            <h2>评分与文本一致性</h2>
            <p>发现高评分但文本负面的隐性差评</p>
          </div>
        </div>
        <div ref="alignmentChartEl" class="chart"></div>
      </article>

      <article class="panel full risk-table-panel">
        <div class="panel-heading">
          <div>
            <h2>高风险舆情预警</h2>
            <p>按风险等级、差评概率和有用数综合排序</p>
          </div>
          <span class="risk-count">{{ hotReviews.length }} 条重点舆情</span>
        </div>
        <div v-if="hotReviews.length" class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>日期</th>
                <th>产品</th>
                <th>问题类型</th>
                <th>风险等级</th>
                <th>差评概率</th>
                <th>评论内容</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in hotReviews" :key="item.id || item.data_index">
                <td>{{ item.date || item.review_date || '-' }}</td>
                <td>{{ item['产品系列'] || item.product_series || '-' }}</td>
                <td>{{ item['问题类型'] || item.issue_type || '-' }}</td>
                <td><span class="risk-tag" :class="item.risk_level === '高风险' || item['风险等级'] === '高风险' ? 'high' : 'medium'">{{ item['风险等级'] || item.risk_level || '-' }}</span></td>
                <td>{{ (Number(item.negative_probability ?? item['差评概率'] ?? 0) * 100).toFixed(1) }}%</td>
                <td class="review-text" :title="item.review_content || item['评论内容']">{{ item.review_content || item['评论内容'] || '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else-if="!loading" class="table-empty">暂无高风险评论</div>
      </article>
    </section>

    <div v-if="loading" class="loading-mask">
      <span class="spinner"></span>
      正在加载趋势数据
    </div>
  </div>
</template>

<style scoped>
.trend-page {
  position: relative;
  box-sizing: border-box;
  width: 100%;
  min-width: 0;
  min-height: calc(100vh - 72px);
  padding: 28px 34px 42px;
  background: #f5f7fb;
  color: #1e293b;
}

.page-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 24px;
}

.page-heading h1 {
  margin: 0;
  color: #17243a;
  font-size: 30px;
  line-height: 1.2;
  letter-spacing: -1px;
}

.page-heading p,
.panel-heading p {
  margin: 8px 0 0;
  color: #94a0b2;
  font-size: 14px;
}

.period-switch {
  display: flex;
  padding: 4px;
  border: 1px solid #e1e7ef;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 4px 14px rgba(31, 54, 88, .04);
}

.period-switch button {
  min-width: 70px;
  padding: 8px 13px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: #748197;
  cursor: pointer;
}

.period-switch button.active {
  background: #3978e8;
  color: #fff;
  box-shadow: 0 4px 10px rgba(57, 120, 232, .24);
}

.error-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
  padding: 12px 16px;
  border: 1px solid #ffd6d8;
  border-radius: 10px;
  background: #fff3f3;
  color: #c9464c;
  font-size: 13px;
}

.error-banner button {
  border: 0;
  background: transparent;
  color: #3978e8;
  cursor: pointer;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 18px;
}

.metric-card {
  display: flex;
  align-items: center;
  gap: 15px;
  min-width: 0;
  padding: 19px;
  border: 1px solid #e8edf3;
  border-radius: 13px;
  background: #fff;
  box-shadow: 0 7px 22px rgba(35, 55, 86, .05);
}

.metric-icon {
  display: grid;
  flex: 0 0 46px;
  height: 46px;
  place-items: center;
  border-radius: 12px;
  font-weight: 700;
}

.metric-icon.blue { background: #e9f1ff; color: #3978e8; }
.metric-icon.cyan { background: #e8f8fb; color: #17a6c1; }
.metric-icon.orange { background: #fff4dd; color: #eaa029; }
.metric-icon.red { background: #ffebec; color: #e84e57; }
.metric-icon.green { background: #e7f8ef; color: #20a568; }

.metric-card p {
  margin: 0 0 5px;
  color: #7c899d;
  font-size: 12px;
}

.metric-card strong {
  display: inline-block;
  margin-right: 8px;
  color: #18243a;
  font-size: 25px;
  line-height: 1;
}

.metric-card span {
  color: #a2adbc;
  font-size: 11px;
}

.metric-card .rise { color: #e94d57; }
.metric-card .fall { color: #20a568; }

.chart-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.65fr) minmax(310px, .75fr);
  gap: 18px;
}

.panel {
  position: relative;
  min-width: 0;
  min-height: 330px;
  padding: 20px 22px;
  border: 1px solid #e8edf3;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(35, 55, 86, .045);
}

.panel.full {
  grid-column: 1 / -1;
}

.panel-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.panel-heading h2 {
  margin: 0;
  color: #243149;
  font-size: 16px;
}

.panel-heading p {
  margin-top: 5px;
  font-size: 12px;
}

.legend-dot {
  color: #6e7b90;
  font-size: 12px;
}

.legend-dot::before {
  display: inline-block;
  width: 8px;
  height: 8px;
  margin-right: 6px;
  border-radius: 50%;
  background: #5a8dee;
  content: '';
}

.chart {
  width: 100%;
  height: 255px;
  margin-top: 10px;
}

.insight-list {
  display: grid;
  gap: 12px;
  margin-top: 22px;
}

.insight-item {
  display: flex;
  gap: 12px;
  padding: 14px;
  border: 1px solid #edf1f5;
  border-radius: 10px;
  background: #fafbfd;
}

.insight-item i {
  flex: 0 0 9px;
  height: 9px;
  margin-top: 5px;
  border-radius: 50%;
}

.insight-item i.blue { background: #3978e8; }
.insight-item i.orange { background: #f2ad2f; }
.insight-item i.red { background: #ef5962; }
.insight-item i.green { background: #28af72; }

.insight-item strong {
  color: #344157;
  font-size: 13px;
}

.insight-item p {
  margin: 5px 0 0;
  color: #8490a3;
  font-size: 12px;
  line-height: 1.6;
}

.empty {
  position: absolute;
  inset: 110px 0 auto;
  color: #a0aabd;
  text-align: center;
  font-size: 13px;
}

.risk-count {
  padding: 6px 10px;
  border-radius: 999px;
  background: #ffedef;
  color: #dc4e59;
  font-size: 12px;
}

.risk-table-panel {
  min-height: 260px;
}

.table-wrap {
  margin-top: 18px;
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

th,
td {
  padding: 12px 10px;
  border-bottom: 1px solid #edf1f5;
  color: #607086;
  text-align: left;
  font-size: 12px;
}

th {
  background: #f8fafc;
  color: #8390a3;
  font-weight: 600;
}

th:nth-child(1) { width: 92px; }
th:nth-child(2) { width: 105px; }
th:nth-child(3) { width: 90px; }
th:nth-child(4) { width: 82px; }
th:nth-child(5) { width: 82px; }

.review-text {
  overflow: hidden;
  color: #3f4d62;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.risk-tag {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 999px;
  background: #fff4dd;
  color: #d8901f;
}

.risk-tag.high {
  background: #ffebed;
  color: #df4f59;
}

.table-empty {
  padding: 70px 0;
  color: #a0aabd;
  text-align: center;
  font-size: 13px;
}

.loading-mask {
  position: fixed;
  z-index: 20;
  right: 28px;
  bottom: 28px;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 11px 15px;
  border: 1px solid #e1e7ef;
  border-radius: 10px;
  background: rgba(255, 255, 255, .96);
  color: #66758b;
  box-shadow: 0 8px 26px rgba(31, 54, 88, .12);
  font-size: 12px;
}

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid #d9e4f7;
  border-top-color: #3978e8;
  border-radius: 50%;
  animation: spin .8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 1180px) {
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .chart-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .trend-page {
    padding: 18px 16px 30px;
  }

  .page-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .metric-grid {
    grid-template-columns: 1fr;
  }

  .period-switch {
    width: 100%;
  }

  .period-switch button {
    flex: 1;
  }
}
</style>
