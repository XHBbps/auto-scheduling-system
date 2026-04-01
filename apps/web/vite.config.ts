import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      input: 'index.html',
      output: {
        manualChunks(id) {
          const normalizedId = id.replace(/\\/g, '/')
          if (!normalizedId.includes('/node_modules/')) {
            return
          }
          if (normalizedId.includes('/node_modules/zrender/')) {
            return 'charts-zrender-vendor'
          }
          if (normalizedId.includes('/node_modules/echarts/')) {
            if (
              normalizedId.includes('/echarts/charts') ||
              normalizedId.includes('/echarts/lib/export/charts.js') ||
              normalizedId.includes('/echarts/lib/chart/')
            ) {
              return 'charts-series-vendor'
            }
            if (
              normalizedId.includes('/echarts/components') ||
              normalizedId.includes('/echarts/lib/export/components.js') ||
              normalizedId.includes('/echarts/lib/component/')
            ) {
              return 'charts-components-vendor'
            }
            if (
              normalizedId.includes('/echarts/renderers') ||
              normalizedId.includes('/echarts/lib/export/renderers.js') ||
              normalizedId.includes('/echarts/lib/renderer/')
            ) {
              return 'charts-renderers-vendor'
            }
            if (
              normalizedId.includes('/echarts/lib/label/') ||
              normalizedId.includes('/echarts/lib/layout/')
            ) {
              return 'charts-layout-vendor'
            }
            if (
              normalizedId.includes('/echarts/lib/util/') ||
              normalizedId.includes('/echarts/lib/data/') ||
              normalizedId.includes('/echarts/lib/animation/')
            ) {
              return 'charts-utils-vendor'
            }
            return 'charts-core-vendor'
          }
          if (normalizedId.includes('/node_modules/element-plus/')) {
            if (
              normalizedId.includes('/element-plus/es/components/table/') ||
              normalizedId.includes('/element-plus/es/components/pagination/') ||
              normalizedId.includes('/element-plus/es/components/scrollbar/')
            ) {
              return 'element-plus-table-vendor'
            }
            if (
              normalizedId.includes('/element-plus/es/components/date-picker/') ||
              normalizedId.includes('/element-plus/es/components/time-picker/') ||
              normalizedId.includes('/element-plus/es/components/calendar/')
            ) {
              return 'element-plus-date-vendor'
            }
            if (
              normalizedId.includes('/element-plus/es/components/dialog/') ||
              normalizedId.includes('/element-plus/es/components/drawer/') ||
              normalizedId.includes('/element-plus/es/components/message-box/') ||
              normalizedId.includes('/element-plus/es/components/tooltip/') ||
              normalizedId.includes('/element-plus/es/components/popover/') ||
              normalizedId.includes('/element-plus/es/components/popconfirm/') ||
              normalizedId.includes('/element-plus/es/components/select/') ||
              normalizedId.includes('/element-plus/es/components/dropdown/')
            ) {
              return 'element-plus-overlay-vendor'
            }
            return 'element-plus-vendor'
          }
          if (normalizedId.includes('/node_modules/@element-plus/icons-vue/')) {
            return 'element-plus-icons-vendor'
          }
          if (
            normalizedId.includes('/node_modules/vue/') ||
            normalizedId.includes('/node_modules/@vue/') ||
            normalizedId.includes('/node_modules/vue-router/')
          ) {
            return 'vue-vendor'
          }
          if (normalizedId.includes('/node_modules/axios/')) {
            return 'http-vendor'
          }
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    restoreMocks: true,
    clearMocks: true,
    pool: 'threads',
    maxWorkers: 1,
    fileParallelism: false,
  },
})
