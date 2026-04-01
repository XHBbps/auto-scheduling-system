import { defineComponent } from 'vue'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import SyncSourceGrid from './SyncSourceGrid.vue'

const IconStub = defineComponent({
  template: '<span class="icon-stub" />',
})

const buildProps = (description = '', sourceKey: 'bom' | 'salesPlan' = 'bom') => ({
  bomForm: {
    material_no: '',
    plant: '',
  },
  getSyncStateDescription: () => description,
  getSyncViewStatusBadgeMeta: () => ({ label: '待触发', tone: 'neutral' as const }),
  isSyncButtonDisabled: () => false,
  syncButtonLabel: () => '手动同步',
  syncSources: [
    {
      title: sourceKey === 'bom' ? 'BOM' : '销售计划',
      key: sourceKey,
      icon: IconStub,
      desc:
        sourceKey === 'bom'
          ? '按物料号手动从 SAP 拉取 BOM 数据，适合单物料补数或联调验证。'
          : '从观远拉取销售计划数据，并触发图纸下发状态回填与自动补 BOM 入队。',
      api: sourceKey === 'bom' ? '/api/admin/sync/bom' : '/api/admin/sync/sales-plan',
    },
  ],
  syncState: {
    salesPlan: { triggering: false, status: 'idle' as const, result: null, jobId: null, message: '' },
    bom: { triggering: false, status: 'idle' as const, result: null, jobId: null, message: '' },
    productionOrders: { triggering: false, status: 'idle' as const, result: null, jobId: null, message: '' },
    research: { triggering: false, status: 'idle' as const, result: null, jobId: null, message: '' },
  },
  onHandleSync: () => undefined,
})

const globalStubs = {
  AppStatusBadge: {
    template: '<div class="app-status-badge-stub" />',
  },
  ElRow: {
    template: '<div><slot /></div>',
  },
  ElCol: {
    template: '<div><slot /></div>',
  },
  ElIcon: {
    template: '<div><slot /></div>',
  },
  ElInput: {
    props: ['modelValue'],
    emits: ['update:modelValue'],
    template: '<input />',
  },
  ElButton: {
    template: '<button><slot /></button>',
  },
}

describe('SyncSourceGrid', () => {
  it('hides idle helper text and bom static note', () => {
    const wrapper = mount(SyncSourceGrid, {
      props: buildProps(''),
      global: {
        stubs: globalStubs,
      },
    })

    expect(wrapper.text()).toContain('BOM')
    expect(wrapper.text()).not.toContain('当前尚未手动触发该同步任务。')
    expect(wrapper.text()).not.toContain('仅支持按单个物料号 + 工厂维度手动补数。')
  })

  it('renders runtime description when provided', () => {
    const wrapper = mount(SyncSourceGrid, {
      props: buildProps('任务已进入后台队列，等待 worker 认领执行。'),
      global: {
        stubs: globalStubs,
      },
    })

    expect(wrapper.text()).toContain('任务已进入后台队列，等待 worker 认领执行。')
  })

  it('keeps bom inputs and action button in the same footer band', () => {
    const wrapper = mount(SyncSourceGrid, {
      props: buildProps('', 'bom'),
      global: {
        stubs: globalStubs,
      },
    })

    expect(wrapper.find('.sync-source-card__footer--bom').exists()).toBe(true)
    expect(wrapper.find('.sync-source-card__bom-fields').exists()).toBe(true)
    expect(wrapper.findAll('input')).toHaveLength(2)
    expect(wrapper.find('button').text()).toContain('手动同步')
  })

  it('aligns non-bom action button to the right footer area', () => {
    const wrapper = mount(SyncSourceGrid, {
      props: buildProps('', 'salesPlan'),
      global: {
        stubs: globalStubs,
      },
    })

    expect(wrapper.find('.sync-source-card__footer--default').exists()).toBe(true)
    expect(wrapper.find('.sync-source-card__bom-fields').exists()).toBe(false)
    expect(wrapper.find('button').text()).toContain('手动同步')
  })
})
