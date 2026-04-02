import { init, use, type EChartsType } from 'echarts/core'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([
  PieChart,
  BarChart,
  LineChart,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  CanvasRenderer,
])

export type DashboardChartInstance = EChartsType

export interface PieDataItem {
  name: string
  value: number
  itemStyle?: Record<string, any>
}

export interface DonutChartOptions {
  data: PieDataItem[]
  centerLabel?: string
  innerRadius?: string
  outerRadius?: string
  showLegend?: boolean
}

export interface BarChartSeriesOptions {
  name: string
  data: number[]
  color?: string
}

export interface BarChartOptions {
  categories: string[]
  series: BarChartSeriesOptions[]
  dualAxis?: boolean
}

export interface LineChartSeriesOptions {
  name: string
  data: number[]
  color?: string
  areaColor?: string
}

export interface LineChartOptions {
  categories: string[]
  series: LineChartSeriesOptions[]
  smooth?: boolean
  showArea?: boolean
}

interface DonutMouseEventParams {
  componentType?: string
  seriesType?: string
  seriesIndex?: number
  dataIndex?: number
  name?: string
  value?: string | number | Date | Record<string, unknown> | unknown[] | null
}

const DEFAULT_GRID = {
  left: '3%',
  right: '3%',
  bottom: '3%',
  top: '14%',
  containLabel: true,
}

const DEFAULT_AXIS_LABEL_COLOR = '#717a82'
const DEFAULT_SPLIT_LINE_COLOR = '#242827'
const DEFAULT_TOOLTIP = {
  backgroundColor: '#1e2120',
  borderColor: '#2a2e2d',
  textStyle: { color: '#ffffff' },
}

const getReusableChart = (
  element: HTMLElement,
  currentChart?: DashboardChartInstance | null,
): DashboardChartInstance => {
  if (currentChart && !currentChart.isDisposed()) {
    const currentDom = currentChart.getDom()
    if (currentDom === element) {
      return currentChart
    }
    currentChart.dispose()
  }
  return init(element)
}

const buildDonutCenterLabel = (label?: string) => {
  if (!label) return ''
  const parts = label.split('\n')
  if (parts.length < 2) return label
  // 第一行数值用粗体大号，第二行说明用细体小号
  return `{value|${parts[0]}}\n{desc|${parts[1]}}`
}

const pickChartColors = (colors: Array<string | undefined>) => colors.filter((color): color is string => Boolean(color))

const buildDonutChartOption = ({
  data,
  centerLabel,
  innerRadius = '58%',
  outerRadius = '76%',
  showLegend = true,
}: DonutChartOptions) => ({
  color: data.map((item) => item.itemStyle?.color).filter(Boolean),
  tooltip: {
    ...DEFAULT_TOOLTIP,
    trigger: 'item',
    formatter: (params: any) => {
      if (!params?.name || !params?.percent) return ''
      return `${params.marker} ${params.name}：${params.value} 单（${params.percent}%）`
    },
  },
  legend: showLegend
    ? {
        bottom: '1%',
        left: 'center',
        icon: 'circle',
        itemWidth: 8,
        itemHeight: 8,
        textStyle: { color: '#8f9ca4', fontSize: 12 },
      }
    : undefined,
  series: [
    {
      type: 'pie',
      radius: [innerRadius, outerRadius],
      center: ['50%', '42%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 8,
        borderColor: '#141716',
        borderWidth: 3,
      },
      label: {
        show: Boolean(centerLabel),
        position: 'center',
        formatter: buildDonutCenterLabel(centerLabel),
        rich: {
          value: {
            color: '#ffffff',
            fontSize: 18,
            fontWeight: 700,
            lineHeight: 24,
            align: 'center',
          },
          desc: {
            color: '#8f9ca4',
            fontSize: 12,
            fontWeight: 400,
            lineHeight: 18,
            align: 'center',
          },
        },
      },
      emphasis: {
        scale: true,
        scaleSize: 3,
        label: {
          show: false,
        },
      },
      labelLine: { show: false },
      data,
    },
  ],
})

const updateDonutCenterLabel = (chart: DashboardChartInstance, label?: string) => {
  chart.setOption(
    {
      series: [
        {
          label: {
            show: Boolean(label),
            formatter: buildDonutCenterLabel(label),
          },
        },
      ],
    },
    { lazyUpdate: true },
  )
}

const isMouseOnRing = (
  chart: DashboardChartInstance,
  event: DonutMouseEventParams,
  innerRadiusPct: number,
  outerRadiusPct: number,
  centerPct: [number, number],
): boolean => {
  const nativeEvent = (event as any).event?.event as MouseEvent | undefined
  if (!nativeEvent) return true // fallback: allow
  const dom = chart.getDom()
  if (!dom) return true
  const rect = dom.getBoundingClientRect()
  const refSize = Math.min(rect.width, rect.height)
  const cx = rect.width * centerPct[0]
  const cy = rect.height * centerPct[1]
  const mx = nativeEvent.clientX - rect.left
  const my = nativeEvent.clientY - rect.top
  const dist = Math.sqrt((mx - cx) ** 2 + (my - cy) ** 2)
  const innerPx = (refSize * innerRadiusPct) / 2
  const outerPx = (refSize * outerRadiusPct) / 2
  return dist >= innerPx && dist <= outerPx
}

const bindDonutCenterLabelInteractions = (
  chart: DashboardChartInstance,
  defaultCenterLabel?: string,
  innerRadius = 0.58,
  outerRadius = 0.76,
  center: [number, number] = [0.5, 0.42],
) => {
  const restoreDefaultLabel = () => {
    updateDonutCenterLabel(chart, defaultCenterLabel)
  }

  chart.off('mouseover')
  chart.off('mouseout')
  chart.off('globalout')

  chart.on('mouseover', (params: DonutMouseEventParams) => {
    if (params.componentType !== 'series' || params.seriesType !== 'pie' || params.dataIndex === undefined) return
    if (!isMouseOnRing(chart, params, innerRadius, outerRadius, center)) return
    const hoveredLabel = `${params.value ?? '-'}\n${params.name || '-'}`
    updateDonutCenterLabel(chart, hoveredLabel)
  })

  chart.on('mouseout', (params: DonutMouseEventParams) => {
    if (params.componentType !== 'series' || params.seriesType !== 'pie' || params.dataIndex === undefined) return
    restoreDefaultLabel()
  })

  chart.on('globalout', restoreDefaultLabel)

  chart.on('legendselectchanged', () => {
    restoreDefaultLabel()
  })
}

const buildVerticalBarChartOption = ({ categories, series, dualAxis }: BarChartOptions) => {
  const seriesColors = pickChartColors(series.map((item) => item.color))
  const isDual = dualAxis && series.length === 2

  return {
    color: seriesColors,
    tooltip: {
      ...DEFAULT_TOOLTIP,
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: isDual
        ? (params: Array<{ marker: string; seriesName: string; value: number; axisValue: string }>) => {
            if (!Array.isArray(params) || !params.length) return ''
            let html = `<div style="font-weight:600;margin-bottom:6px">${params[0].axisValue}</div>`
            params.forEach((p) => {
              const unit = p.seriesName.includes('金额') ? ' 万元' : ' 单'
              html += `<div>${p.marker} ${p.seriesName}：${p.value}${unit}</div>`
            })
            return html
          }
        : undefined,
    },
    legend: series.length > 1
      ? {
          top: 0,
          left: 0,
          icon: 'roundRect',
          itemWidth: 8,
          itemHeight: 8,
          textStyle: { color: '#8f9ca4', fontSize: 12 },
        }
      : undefined,
    grid: isDual
      ? { left: '3%', right: '3%', bottom: '3%', top: '14%', containLabel: true }
      : DEFAULT_GRID,
    xAxis: {
      type: 'category',
      data: categories,
      axisTick: { show: false },
      axisLabel: { color: DEFAULT_AXIS_LABEL_COLOR, margin: 12, fontSize: 12 },
      axisLine: { show: false },
    },
    yAxis: isDual
      ? [
          {
            type: 'value',
            position: 'left',
            axisLabel: { color: series[0]?.color || DEFAULT_AXIS_LABEL_COLOR, fontSize: 12 },
            splitLine: { lineStyle: { color: DEFAULT_SPLIT_LINE_COLOR, type: 'dashed' } },
          },
          {
            type: 'value',
            position: 'right',
            axisLabel: { color: series[1]?.color || DEFAULT_AXIS_LABEL_COLOR, fontSize: 12 },
            splitLine: { show: false },
          },
        ]
      : {
          type: 'value',
          axisLabel: { color: DEFAULT_AXIS_LABEL_COLOR, fontSize: 12 },
          splitLine: { lineStyle: { color: DEFAULT_SPLIT_LINE_COLOR, type: 'dashed' } },
        },
    series: series.map((item, index) => ({
      name: item.name,
      type: 'bar',
      barWidth: series.length > 1 ? 14 : '30%',
      barGap: series.length > 1 ? '20%' : '0%',
      yAxisIndex: isDual ? index : 0,
      data: item.data,
      itemStyle: {
        color: item.color,
        borderRadius: [6, 6, 0, 0],
      },
      emphasis: {
        itemStyle: {
          color: item.color,
          opacity: 0.92,
        },
      },
      z: index + 1,
    })),
  }
}

const buildHorizontalBarChartOption = ({ categories, series }: BarChartOptions) => ({
  color: pickChartColors(series.map((item) => item.color)),
  tooltip: {
    ...DEFAULT_TOOLTIP,
    trigger: 'axis',
    axisPointer: { type: 'shadow' },
  },
  legend: series.length > 1
    ? {
        top: 0,
        left: 0,
        icon: 'roundRect',
        itemWidth: 8,
        itemHeight: 8,
        textStyle: { color: '#8f9ca4', fontSize: 12 },
      }
    : undefined,
  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    top: '8%',
    containLabel: true,
  },
  xAxis: {
    type: 'value',
    axisLabel: { color: DEFAULT_AXIS_LABEL_COLOR, fontSize: 12 },
    splitLine: { lineStyle: { color: DEFAULT_SPLIT_LINE_COLOR, type: 'dashed' } },
  },
  yAxis: {
    type: 'category',
    data: categories,
    axisTick: { show: false },
    axisLine: { show: false },
    axisLabel: { color: '#a0aab2', margin: 10, fontSize: 12 },
  },
  series: series.map((item) => ({
    name: item.name,
    type: 'bar',
    data: item.data,
    barWidth: series.length > 1 ? 10 : 12,
    itemStyle: {
      color: item.color,
      borderRadius: [0, 6, 6, 0],
    },
  })),
})

const buildLineChartOption = ({ categories, series, smooth = true, showArea = false }: LineChartOptions) => ({
  tooltip: {
    ...DEFAULT_TOOLTIP,
    trigger: 'axis',
  },
  legend: series.length > 1
    ? {
        top: 0,
        left: 0,
        icon: 'roundRect',
        itemWidth: 8,
        itemHeight: 8,
        textStyle: { color: '#8f9ca4', fontSize: 12 },
      }
    : undefined,
  grid: series.length > 1 ? DEFAULT_GRID : { ...DEFAULT_GRID, top: '8%' },
  xAxis: {
    type: 'category',
    data: categories,
    boundaryGap: false,
    axisTick: { show: false },
    axisLabel: { color: DEFAULT_AXIS_LABEL_COLOR, margin: 12, fontSize: 12 },
    axisLine: { show: false },
  },
  yAxis: {
    type: 'value',
    axisLabel: { color: DEFAULT_AXIS_LABEL_COLOR, fontSize: 12 },
    splitLine: { lineStyle: { color: DEFAULT_SPLIT_LINE_COLOR, type: 'dashed' } },
  },
  series: series.map((item) => ({
    name: item.name,
    type: 'line',
    smooth,
    symbol: 'circle',
    symbolSize: 6,
    data: item.data,
    lineStyle: {
      width: 2,
      color: item.color,
    },
    itemStyle: {
      color: item.color,
      borderColor: '#121413',
      borderWidth: 2,
    },
    areaStyle: showArea
      ? {
          color: item.areaColor || item.color,
          opacity: 0.12,
        }
      : undefined,
  })),
})

export const renderDonutChart = (
  element: HTMLElement,
  options: DonutChartOptions,
  currentChart?: DashboardChartInstance | null,
): DashboardChartInstance => {
  const chart = getReusableChart(element, currentChart)
  chart.setOption(buildDonutChartOption(options), { notMerge: true, lazyUpdate: true })
  bindDonutCenterLabelInteractions(chart, options.centerLabel)
  return chart
}

export const renderVerticalBarChart = (
  element: HTMLElement,
  options: BarChartOptions,
  currentChart?: DashboardChartInstance | null,
): DashboardChartInstance => {
  const chart = getReusableChart(element, currentChart)
  chart.setOption(buildVerticalBarChartOption(options), { notMerge: true, lazyUpdate: true })
  return chart
}

export const renderHorizontalBarChart = (
  element: HTMLElement,
  options: BarChartOptions,
  currentChart?: DashboardChartInstance | null,
): DashboardChartInstance => {
  const chart = getReusableChart(element, currentChart)
  chart.setOption(buildHorizontalBarChartOption(options), { notMerge: true, lazyUpdate: true })
  return chart
}

export const renderLineChart = (
  element: HTMLElement,
  options: LineChartOptions,
  currentChart?: DashboardChartInstance | null,
): DashboardChartInstance => {
  const chart = getReusableChart(element, currentChart)
  chart.setOption(buildLineChartOption(options), { notMerge: true, lazyUpdate: true })
  return chart
}
