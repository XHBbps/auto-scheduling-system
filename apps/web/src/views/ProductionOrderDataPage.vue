<template>
  <div class="space-y-6">
    <div class="tech-card p-6">
      <el-form :model="searchForm" inline class="flex flex-wrap gap-4">
        <el-form-item label="生产订单" class="!mb-0">
          <el-input v-model="searchForm.productionOrderNo" placeholder="请输入" clearable class="!w-40" />
        </el-form-item>
        <el-form-item label="物料编号" class="!mb-0">
          <el-input v-model="searchForm.materialNo" placeholder="请输入" clearable class="!w-36" />
        </el-form-item>
        <el-form-item label="机型" class="!mb-0">
          <el-input v-model="searchForm.machineModel" placeholder="请输入" clearable class="!w-32" />
        </el-form-item>
        <el-form-item label="订单状态" class="!mb-0">
          <el-input v-model="searchForm.orderStatus" placeholder="请输入" clearable class="!w-32" />
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
        <el-table-column prop="production_order_no" label="生产订单" width="144" show-overflow-tooltip v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="text-white font-medium">{{ row.production_order_no }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="material_no" label="物料编号" width="136" show-overflow-tooltip v-bind="sortableColumnProps" />
        <el-table-column prop="material_desc" label="物料描述" width="180" show-overflow-tooltip v-bind="sortableColumnProps" />
        <el-table-column prop="machine_model" label="机型" width="120" v-bind="sortableColumnProps" />
        <el-table-column prop="plant" label="工厂" width="80" align="center" v-bind="sortableColumnProps" />
        <el-table-column prop="processing_dept" label="加工部门" width="120" v-bind="sortableColumnProps" />
        <el-table-column prop="production_qty" label="生产数量" width="108" align="center" v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="font-mono-num">{{ row.production_qty ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="order_status" label="订单状态" width="108" align="center" v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="text-text-secondary">{{ row.order_status || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="start_time_actual" label="实际开始" width="176" v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="font-mono-num text-sm text-text-secondary">{{ formatDate(row.start_time_actual) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="finish_time_actual" label="实际完成" width="176" v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="font-mono-num text-sm text-text-secondary">{{ formatDate(row.finish_time_actual) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="sales_order_no" label="销售订单" width="144" show-overflow-tooltip v-bind="sortableColumnProps" />
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

interface ProductionOrderItem {
  id: number
  production_order_no: string
  material_no?: string
  material_desc?: string
  machine_model?: string
  plant?: string
  processing_dept?: string
  start_time_actual?: string
  finish_time_actual?: string
  production_qty?: number
  order_status?: string
  sales_order_no?: string
  created_at?: string
}

interface PaginatedResponse {
  total: number
  page_no: number
  page_size: number
  items: ProductionOrderItem[]
}

const router = useRouter()
const route = useRoute()

const createSearchForm = () => ({ productionOrderNo: '', materialNo: '', machineModel: '', orderStatus: '' })

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
  perfScope: 'productionOrderData',
  perfLabel: 'fetchProductionOrderTable',
  buildPerfMeta: (params) => ({
    hasProductionOrderNo: Boolean(params.production_order_no),
    hasMaterialNo: Boolean(params.material_no),
    hasMachineModel: Boolean(params.machine_model),
    hasOrderStatus: Boolean(params.order_status),
  }),

  searchParamKeyMap: {
    productionOrderNo: 'production_order_no',
    materialNo: 'material_no',
    machineModel: 'machine_model',
    orderStatus: 'order_status',
  },
  sortFieldMap: {
    production_order_no: 'production_order_no',
    material_no: 'material_no',
    material_desc: 'material_desc',
    machine_model: 'machine_model',
    plant: 'plant',
    processing_dept: 'processing_dept',
    production_qty: 'production_qty',
    order_status: 'order_status',
    start_time_actual: 'start_time_actual',
    finish_time_actual: 'finish_time_actual',
    sales_order_no: 'sales_order_no',
    created_at: 'created_at',
  },
  request: (params) =>
    request.get<PaginatedResponse>('/api/data/production-orders', {
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
