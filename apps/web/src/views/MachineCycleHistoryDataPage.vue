<template>
  <div class="space-y-6">
    <div class="tech-card p-6">
      <el-form :model="searchForm" inline class="flex flex-wrap gap-4">
        <el-form-item label="机型" class="!mb-0">
          <el-input v-model="searchForm.machineModel" placeholder="请输入" clearable class="!w-32" />
        </el-form-item>
        <el-form-item label="产品系列" class="!mb-0">
          <el-input v-model="searchForm.productSeries" placeholder="请输入" clearable class="!w-36" />
        </el-form-item>
        <el-form-item label="合同号" class="!mb-0">
          <el-input v-model="searchForm.contractNo" placeholder="请输入" clearable class="!w-36" />
        </el-form-item>
        <el-form-item label="销售订单" class="!mb-0">
          <el-input v-model="searchForm.orderNo" placeholder="请输入" clearable class="!w-36" />
        </el-form-item>
        <el-form-item class="!mb-0 ml-auto">
          <el-button type="primary" @click="handleSearch" class="!px-6">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <div class="tech-card p-6">
      <el-table v-loading="loading" :data="tableData" style="width: 100%" @sort-change="handleTableSortChange" class="app-data-table" table-layout="fixed">
        <template #empty>
          <AppTableState
            :state="tableFeedbackState"
            error-action-text="重新加载"
            auth-action-text="前往登录"
            @action="handleTableStateAction"
          />
        </template>
        <el-table-column prop="machine_model" label="机型" width="128" v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="text-white font-medium">{{ row.machine_model }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="product_series" label="产品系列" width="120" v-bind="sortableColumnProps" />
        <el-table-column prop="order_qty" label="订单数量" width="108" align="center" v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="font-mono-num">{{ row.order_qty ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="cycle_days" label="周期天数" width="108" align="center" v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="font-mono-num text-brand">{{ row.cycle_days ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="order_type" label="订单类型" width="108" align="center" v-bind="sortableColumnProps" />
        <el-table-column prop="contract_no" label="合同号" width="136" show-overflow-tooltip v-bind="sortableColumnProps" />
        <el-table-column prop="order_no" label="销售订单" width="136" show-overflow-tooltip v-bind="sortableColumnProps" />
        <el-table-column prop="customer_name" label="客户名称" width="160" show-overflow-tooltip v-bind="sortableColumnProps" />
        <el-table-column prop="drawing_release_date" label="图纸下发日" width="132" v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="font-mono-num text-sm text-text-secondary">{{ formatDate(row.drawing_release_date) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="inspection_date" label="验收日期" width="132" v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="font-mono-num text-sm text-text-secondary">{{ formatDate(row.inspection_date) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="同步时间" width="176" v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="font-mono-num text-sm text-text-muted">{{ formatDateTime(row.created_at) }}</span>
          </template>
        </el-table-column>
      </el-table>

      <div class="flex justify-end mt-6">
        <el-pagination
          v-model:current-page="pageNo"
          v-model:page-size="pageSize"
          :page-sizes="pageSizes"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchData"
          @current-change="fetchData"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppTableState from '../components/AppTableState.vue'
import { useRemoteTableQuery } from '../composables/useServerTableQuery'
import { createTableStateActionHandler } from '../composables/useTableFeedbackState'
import request from '../utils/httpClient'
import { formatDate, formatDateTime } from '../utils/format'

interface MachineCycleHistoryItem {
  id: number
  detail_id: string
  machine_model: string
  product_series?: string
  order_qty?: number
  drawing_release_date?: string
  inspection_date?: string
  customer_name?: string
  contract_no?: string
  order_no?: string
  order_type?: string
  cycle_days?: number
  created_at?: string
}

interface PaginatedResponse {
  total: number
  page_no: number
  page_size: number
  items: MachineCycleHistoryItem[]
}

const router = useRouter()
const route = useRoute()

const createSearchForm = () => ({ machineModel: '', productSeries: '', contractNo: '', orderNo: '' })

const {
  sortableColumnProps,
  tableFeedbackState,
  loading,
  tableData,
  searchForm,
  pageNo,
  pageSize,
  pageSizes,
  total,
  fetchData,
  handleSearch,
  handleReset,
  handleTableSortChange,
} = useRemoteTableQuery({
  createSearchForm,
  perfScope: 'machineCycleHistory',
  perfLabel: 'fetchHistoryTable',
  buildPerfMeta: (params) => ({
    hasMachineModel: Boolean(params.machine_model),
    hasProductSeries: Boolean(params.product_series),
    hasContractNo: Boolean(params.contract_no),
    hasOrderNo: Boolean(params.order_no),
  }),

  searchParamKeyMap: {
    machineModel: 'machine_model',
    productSeries: 'product_series',
    contractNo: 'contract_no',
    orderNo: 'order_no',
  },
  sortFieldMap: {
    machine_model: 'machine_model',
    product_series: 'product_series',
    order_qty: 'order_qty',
    cycle_days: 'cycle_days',
    order_type: 'order_type',
    contract_no: 'contract_no',
    order_no: 'order_no',
    customer_name: 'customer_name',
    drawing_release_date: 'drawing_release_date',
    inspection_date: 'inspection_date',
    created_at: 'created_at',
  },
  request: (params) =>
    request.get<PaginatedResponse>('/api/data/machine-cycle-history', {
      params,
      silentError: true,
    }),
})

const handleTableStateAction = createTableStateActionHandler({
  tableFeedbackState,
  retry: fetchData,
  router,
  redirectPath: route.fullPath,
})

onMounted(() => {
  void fetchData()
})
</script>
