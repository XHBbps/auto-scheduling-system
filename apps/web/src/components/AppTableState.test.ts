import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AppTableState from './AppTableState.vue'

describe('AppTableState', () => {
  it('renders auth state copy and action button', async () => {
    const wrapper = mount(AppTableState, {
      props: {
        state: 'auth',
        authActionText: '前往登录',
      },
    })

    expect(wrapper.text()).toContain('登录状态已失效')
    expect(wrapper.text()).toContain('请重新登录后继续查看列表数据')
    expect(wrapper.text()).toContain('前往登录')

    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('action')).toBeTruthy()
  })

  it('uses custom text first when provided', () => {
    const wrapper = mount(AppTableState, {
      props: {
        state: 'error',
        text: '自定义反馈文案',
      },
    })

    expect(wrapper.text()).toContain('列表加载失败')
    expect(wrapper.text()).toContain('自定义反馈文案')
  })
})