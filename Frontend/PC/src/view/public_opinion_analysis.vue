<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { analysisData, loadAnalysis } from '../store/analysisCache'

const emptyData = {
  overview: {}, rating_distribution: [], product: [], product_rating_distribution: [],
  memory: [], storage: [], issues: [], issue_by_product: [], positive_keywords: [],
  negative_keywords: [], confusion_matrix: {}, risks: []
}
const data = ref(analysisData.value || emptyData)
const loading = ref(false)
const error = ref('')

const ratingEl = ref(null)
const productEl = ref(null)
const productRatingEl = ref(null)
const riskEl = ref(null)
const issueEl = ref(null)
const issueProductEl = ref(null)
const keywordEl = ref(null)
const confusionEl = ref(null)

const chartRefs = [ratingEl, productEl, productRatingEl, riskEl, issueEl, issueProductEl, keywordEl, confusionEl]
let charts = []

const overview = computed(() => data.value?.overview || {})
const hasData = computed(() => Number(overview.value.total || 0) > 0)

function number(value) {
  return Number(value || 0).toLocaleString('zh-CN')
}

function percent(value) {
  return `${Number(value || 0).toFixed(1)}%`
}

async function loadLatest(force = false) {
  loading.value = true
  error.value = ''
  try {
    data.value = await loadAnalysis(force) || emptyData
    await nextTick()
    renderCharts()
  } catch (exception) {
    data.value = data.value || emptyData
    error.value = exception?.response?.data?.message || exception.message || '暂无分析结果，请先导入数据文件'
  } finally {
    loading.value = false
  }
}

async function handleDatabaseUpdated(event) {
  data.value = event.detail?.data || analysisData.value || emptyData
  await nextTick()
  renderCharts()
}

function initChart(index) {
  const element = chartRefs[index].value
  if (!element) return null
  charts[index] ||= echarts.init(element)
  return charts[index]
}

function baseGrid(left = 46, right = 20, bottom = 34, top = 24) {
  return { left, right, bottom, top, containLabel: true }
}

function renderCharts() {
  if (!data.value) return
  const rating = data.value.rating_distribution || []
  const products = data.value.product || []
  const productRatings = data.value.product_rating_distribution || []
  const issues = data.value.issues || []
  const issueByProduct = data.value.issue_by_product || []
  const positiveWords = data.value.positive_keywords || []
  const negativeWords = data.value.negative_keywords || []
  const matrix = data.value.confusion_matrix || {}

  initChart(0)?.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: baseGrid(),
    xAxis: { type: 'category', data: rating.map(item => `${item.rating}星`), axisTick: { show: false } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: '#edf1f7' } } },
    series: [{
      type: 'bar',
      barWidth: '48%',
      data: rating.map((item, index) => ({ value: item.count, itemStyle: { color: ['#ef5b62', '#f08b56', '#f2ba4d', '#69b98b', '#3478df'][index], borderRadius: [5, 5, 0, 0] } })),
      label: { show: true, position: 'top', color: '#5e6b7e', fontSize: 10 }
    }]
  }, true)

  initChart(1)?.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0, right: 4, textStyle: { fontSize: 10, color: '#66758a' } },
    grid: baseGrid(42, 44, 36, 42),
    xAxis: { type: 'category', data: products.map(item => item['产品系列']), axisLabel: { interval: 0, rotate: products.length > 5 ? 25 : 0 } },
    yAxis: [
      { type: 'value', name: '评论数', splitLine: { lineStyle: { color: '#edf1f7' } } },
      { type: 'value', name: '评分', min: 0, max: 5, splitLine: { show: false } }
    ],
    series: [
      { name: '评论数', type: 'bar', barWidth: '42%', data: products.map(item => item['评论数']), itemStyle: { color: '#3478df', borderRadius: [4, 4, 0, 0] } },
      { name: '平均评分', type: 'line', yAxisIndex: 1, smooth: true, symbolSize: 7, data: products.map(item => item['平均评分']), itemStyle: { color: '#f1a51e' }, lineStyle: { width: 2.5 } }
    ]
  }, true)

  initChart(2)?.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0, textStyle: { fontSize: 9, color: '#66758a' } },
    grid: baseGrid(42, 18, 38, 44),
    xAxis: { type: 'category', data: productRatings.map(item => item.product_series), axisLabel: { interval: 0, rotate: productRatings.length > 5 ? 25 : 0 } },
    yAxis: { type: 'value', name: '评论数', splitLine: { lineStyle: { color: '#edf1f7' } } },
    series: [1, 2, 3, 4, 5].map((ratingValue, index) => ({
      name: `${ratingValue}星`, type: 'bar', stack: 'rating', barMaxWidth: 38,
      data: productRatings.map(item => item[`rating_${ratingValue}`] || 0),
      itemStyle: { color: ['#ef5b62', '#f08b56', '#f2ba4d', '#69b98b', '#3478df'][index] }
    }))
  }, true)

  const riskGroups = [
    ['产品系列', products.map(item => ({ name: item['产品系列'], value: item['差评率'] }))],
    ['内存', (data.value.memory || []).map(item => ({ name: item['内存'], value: item['差评率'] }))],
    ['硬盘', (data.value.storage || []).map(item => ({ name: item['硬盘'], value: item['差评率'] }))]
  ]
  const riskRanking = riskGroups
    .flatMap(([group, list], groupIndex) => list.map(item => ({ ...item, group, groupIndex })))
    .sort((a, b) => b.value - a.value)
    .slice(0, 9)
    .reverse()
  initChart(3)?.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, valueFormatter: value => `${value}%` },
    grid: baseGrid(96, 36, 28, 18),
    xAxis: { type: 'value', name: '差评率(%)', splitLine: { lineStyle: { color: '#edf1f7' } } },
    yAxis: { type: 'category', data: riskRanking.map(item => `${item.group} · ${item.name}`), axisLabel: { width: 88, overflow: 'truncate', fontSize: 9 } },
    series: [{
      type: 'bar', barWidth: 10,
      data: riskRanking.map(item => ({ value: item.value, itemStyle: { color: ['#ef5b62', '#f1a51e', '#8b6ee8'][item.groupIndex], borderRadius: [0, 5, 5, 0] } })),
      label: { show: true, position: 'right', formatter: '{c}%', color: '#68778b', fontSize: 9 }
    }]
  }, true)

  initChart(4)?.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: baseGrid(82, 34, 26, 18),
    xAxis: { type: 'value', splitLine: { lineStyle: { color: '#edf1f7' } } },
    yAxis: { type: 'category', data: [...issues].reverse().map(item => item.name), axisTick: { show: false }, axisLine: { show: false } },
    series: [{ type: 'bar', barWidth: 12, data: [...issues].reverse().map(item => item.count), itemStyle: { color: '#ef5b62', borderRadius: [0, 6, 6, 0] }, label: { show: true, position: 'right', color: '#65748a' } }]
  }, true)

  const issueNames = [...new Set(issueByProduct.map(item => item['问题类型']))].slice(0, 6)
  const productNames = [...new Set(issueByProduct.map(item => item['产品系列']))]
  initChart(5)?.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { type: 'scroll', top: 0, textStyle: { fontSize: 9, color: '#66758a' } },
    grid: baseGrid(44, 18, 38, 44),
    xAxis: { type: 'category', data: productNames, axisLabel: { interval: 0, rotate: productNames.length > 5 ? 25 : 0 } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: '#edf1f7' } } },
    series: issueNames.map((name, index) => ({
      name, type: 'bar', stack: 'issue', barMaxWidth: 40,
      data: productNames.map(product => issueByProduct.find(item => item['产品系列'] === product && item['问题类型'] === name)?.count || 0),
      itemStyle: { color: ['#ef5b62', '#f08b56', '#f2ba4d', '#8b6ee8', '#4f95e8', '#52b9ae'][index] }
    }))
  }, true)

  const maxWordCount = Math.max(1, ...positiveWords.map(item => item.count), ...negativeWords.map(item => item.count))
  initChart(6)?.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0, textStyle: { fontSize: 10, color: '#66758a' } },
    grid: baseGrid(72, 28, 28, 42),
    xAxis: { type: 'value', min: -maxWordCount, max: maxWordCount, axisLabel: { formatter: value => Math.abs(value) }, splitLine: { lineStyle: { color: '#edf1f7' } } },
    yAxis: { type: 'category', data: Array.from({ length: 10 }, (_, i) => positiveWords[i]?.word || negativeWords[i]?.word || `词汇${i + 1}`), axisTick: { show: false } },
    series: [
      { name: '负面词', type: 'bar', stack: 'word', data: Array.from({ length: 10 }, (_, i) => -(negativeWords[i]?.count || 0)), itemStyle: { color: '#ef5b62', borderRadius: [5, 0, 0, 5] } },
      { name: '正面词', type: 'bar', stack: 'word', data: Array.from({ length: 10 }, (_, i) => positiveWords[i]?.count || 0), itemStyle: { color: '#42b883', borderRadius: [0, 5, 5, 0] } }
    ]
  }, true)

  initChart(7)?.setOption({
    tooltip: { position: 'top', formatter: params => `${params.name}<br>${params.data[2]} 条` },
    grid: { left: 72, right: 28, top: 18, bottom: 48 },
    xAxis: { type: 'category', data: ['预测差评', '预测好评'], splitArea: { show: true }, axisTick: { show: false } },
    yAxis: { type: 'category', data: ['实际差评', '实际好评'], splitArea: { show: true }, axisTick: { show: false } },
    visualMap: { min: 0, max: Math.max(matrix.tn || 0, matrix.fp || 0, matrix.fn || 0, matrix.tp || 0, 1), calculable: false, orient: 'horizontal', left: 'center', bottom: 0, inRange: { color: ['#eef5ff', '#3478df'] }, textStyle: { fontSize: 9 } },
    series: [{ type: 'heatmap', data: [[0, 0, matrix.tn || 0], [1, 0, matrix.fp || 0], [0, 1, matrix.fn || 0], [1, 1, matrix.tp || 0]], label: { show: true, color: '#172c49', fontWeight: 700 } }]
  }, true)
}

function resizeCharts() {
  charts.forEach(chart => chart?.resize())
}

onMounted(() => {
  loadLatest()
  window.addEventListener('resize', resizeCharts)
  window.addEventListener('database-data-updated', handleDatabaseUpdated)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  window.removeEventListener('database-data-updated', handleDatabaseUpdated)
  charts.forEach(chart => chart?.dispose())
  charts = []
})
</script>

<template>
  <div class="analysis-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">PUBLIC OPINION INTELLIGENCE</p>
        <h1>舆情分析决策看板</h1>
        <p class="subtitle">产品满意度、差评问题与模型识别结果的综合分析</p>
      </div>
      <div class="header-actions">
        <span v-if="hasData" class="status"><i></i>数据已更新</span>
        <button class="secondary-button" :disabled="loading" @click="loadLatest(true)">{{ loading ? '刷新中…' : '刷新数据' }}</button>
      </div>
    </header>

    <div v-if="error" class="notice">
      <span>{{ error }}</span>
      <button :disabled="loading" @click="loadLatest">重新读取</button>
    </div>

    <section class="kpi-grid">
      <article class="kpi-card blue"><span>评论总量</span><strong>{{ number(overview.total) }}</strong><small>当前分析样本</small><i>总</i></article>
      <article class="kpi-card amber"><span>平均评分</span><strong>{{ Number(overview.average_rating || 0).toFixed(2) }}</strong><small>满分 5.00</small><i>星</i></article>
      <article class="kpi-card red"><span>模型差评率</span><strong>{{ percent(overview.negative_rate) }}</strong><small>{{ number(overview.negative_count) }} 条差评</small><i>警</i></article>
      <article class="kpi-card purple"><span>高风险评论</span><strong>{{ number(overview.high_risk_count) }}</strong><small>需优先复核</small><i>险</i></article>
      <article class="kpi-card green"><span>潜在隐性差评</span><strong>{{ number(overview.hidden_negative_count) }}</strong><small>高评分但模型判负</small><i>隐</i></article>
    </section>

    <section class="dashboard-grid">
      <article class="panel rating-panel"><div class="panel-title"><div><h2>整体评分分布</h2><p>各星级评论数量</p></div><span>核心指标</span></div><div ref="ratingEl" class="chart"></div></article>
      <article class="panel product-panel"><div class="panel-title"><div><h2>产品系列讨论量与满意度</h2><p>柱形为评论量，折线为平均评分</p></div></div><div ref="productEl" class="chart"></div></article>
      <article class="panel issue-panel"><div class="panel-title"><div><h2>差评主要问题 TOP10</h2><p>模型差评中的问题类别</p></div><span class="danger-tag">重点关注</span></div><div ref="issueEl" class="chart"></div></article>
      <article class="panel risk-panel"><div class="panel-title"><div><h2>高风险维度差评率排名</h2><p>产品系列 / 内存 / 硬盘</p></div></div><div ref="riskEl" class="chart"></div></article>
      <article class="panel stack-panel"><div class="panel-title"><div><h2>各系列评分分布</h2><p>不同星级评论构成对比</p></div></div><div ref="productRatingEl" class="chart"></div></article>
      <article class="panel issue-stack-panel"><div class="panel-title"><div><h2>各系列差评问题构成</h2><p>定位不同产品的主要问题差异</p></div></div><div ref="issueProductEl" class="chart"></div></article>
      <article class="panel keyword-panel"><div class="panel-title"><div><h2>Top10 正面 / 负面词汇</h2><p>文本内容的主要驱动因素</p></div></div><div ref="keywordEl" class="chart"></div></article>
      <article class="panel matrix-panel"><div class="panel-title"><div><h2>XGBoost 混淆矩阵</h2><p>当前导入样本的模型判断结果</p></div><b>准确率 {{ percent(data?.confusion_matrix?.accuracy) }}</b></div><div ref="confusionEl" class="chart"></div></article>
    </section>

  </div>
</template>

<style scoped>
:global(body){margin:0;background:#f3f6fb}.analysis-page{position:relative;width:100%;min-height:calc(100vh - 64px);padding:22px 26px 34px;box-sizing:border-box;background:#f3f6fb;color:#172b49;font-family:Inter,"PingFang SC","Microsoft YaHei",sans-serif}.page-header{display:flex;align-items:center;justify-content:space-between;gap:24px;margin-bottom:18px}.eyebrow{margin:0 0 5px;color:#3478df;font-size:10px;font-weight:800;letter-spacing:1.6px}.page-header h1{margin:0;font-size:25px;line-height:1.25;letter-spacing:-.4px}.subtitle{margin:6px 0 0;color:#8491a4;font-size:12px}.header-actions{display:flex;align-items:center;gap:9px}.status{display:flex;align-items:center;gap:6px;margin-right:4px;color:#64748a;font-size:11px}.status i{width:7px;height:7px;border-radius:50%;background:#35b47d;box-shadow:0 0 0 4px rgba(53,180,125,.12)}button{height:36px;padding:0 15px;border-radius:8px;font:600 11px inherit;cursor:pointer;transition:.2s}button:disabled{cursor:wait;opacity:.6}.secondary-button{border:1px solid #dce4ef;background:#fff;color:#53637a}.primary-button{border:1px solid #3478df;background:#3478df;color:#fff;box-shadow:0 6px 14px rgba(52,120,223,.2)}.primary-button:hover{background:#2869c9}.file-input{display:none}.notice{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;padding:11px 14px;border:1px solid #f5c9cc;border-radius:9px;background:#fff4f5;color:#c94752;font-size:11px}.notice button{height:28px;border:0;background:transparent;color:#3478df}.kpi-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:13px;margin-bottom:14px}.kpi-card{position:relative;min-height:106px;padding:17px 18px;overflow:hidden;box-sizing:border-box;border:1px solid #e1e8f1;border-radius:11px;background:#fff;box-shadow:0 6px 20px rgba(28,50,82,.04)}.kpi-card span,.kpi-card strong,.kpi-card small{display:block}.kpi-card span{color:#69778b;font-size:11px;font-weight:600}.kpi-card strong{margin:9px 0 5px;color:#172b49;font-size:25px;line-height:1}.kpi-card small{color:#96a1b1;font-size:9px}.kpi-card>i{position:absolute;right:15px;top:17px;display:grid;width:38px;height:38px;place-items:center;border-radius:10px;font-size:12px;font-style:normal;font-weight:800}.kpi-card:after{position:absolute;right:-28px;bottom:-40px;width:92px;height:92px;border-radius:50%;content:"";opacity:.12}.kpi-card.blue>i,.kpi-card.blue:after{background:#dceaff;color:#3478df}.kpi-card.amber>i,.kpi-card.amber:after{background:#fff0cf;color:#e59a15}.kpi-card.red>i,.kpi-card.red:after{background:#ffe1e3;color:#e94f58}.kpi-card.purple>i,.kpi-card.purple:after{background:#eee7ff;color:#8061df}.kpi-card.green>i,.kpi-card.green:after{background:#ddf5ea;color:#26a66f}.dashboard-grid{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:14px}.panel{height:300px;min-width:0;box-sizing:border-box;border:1px solid #e1e8f1;border-radius:11px;background:#fff;box-shadow:0 6px 20px rgba(28,50,82,.04)}.rating-panel{grid-column:span 4}.product-panel{grid-column:span 5}.issue-panel{grid-column:span 3}.risk-panel{grid-column:span 4}.stack-panel{grid-column:span 4}.issue-stack-panel{grid-column:span 4}.keyword-panel{grid-column:span 7}.matrix-panel{grid-column:span 5}.panel-title{display:flex;height:58px;padding:14px 17px 0;box-sizing:border-box;align-items:flex-start;justify-content:space-between;gap:10px}.panel-title h2{margin:0;color:#253952;font-size:13px}.panel-title p{margin:5px 0 0;color:#97a2b2;font-size:9px}.panel-title>span{padding:4px 8px;border-radius:10px;background:#eaf2ff;color:#3478df;font-size:8px;font-weight:700}.panel-title>.danger-tag{background:#ffeaeb;color:#e94f58}.panel-title>b{padding:5px 8px;border-radius:6px;background:#e7f6ef;color:#279d6d;font-size:9px}.chart{width:100%;height:calc(100% - 58px)}.loading-mask{position:absolute;inset:0;display:grid;place-content:center;justify-items:center;background:rgba(243,246,251,.78);backdrop-filter:blur(2px);z-index:5}.loading-mask span{width:30px;height:30px;border:3px solid #d8e3f2;border-top-color:#3478df;border-radius:50%;animation:spin .8s linear infinite}.loading-mask p{margin:10px 0;color:#64748a;font-size:11px}@keyframes spin{to{transform:rotate(360deg)}}@media(max-width:1400px){.kpi-grid{grid-template-columns:repeat(3,1fr)}.rating-panel,.issue-panel,.risk-panel,.stack-panel{grid-column:span 6}.product-panel,.issue-stack-panel,.keyword-panel,.matrix-panel{grid-column:span 6}}@media(max-width:980px){.analysis-page{padding:18px}.page-header{align-items:flex-start;flex-direction:column}.header-actions{width:100%;flex-wrap:wrap}.kpi-grid{grid-template-columns:repeat(2,1fr)}.dashboard-grid>.panel{grid-column:span 12}}@media(max-width:600px){.analysis-page{padding:14px 12px 26px}.page-header h1{font-size:21px}.status{width:100%;margin-bottom:3px}.header-actions button{flex:1}.kpi-grid{grid-template-columns:1fr;gap:10px}.panel{height:310px}}
</style>
