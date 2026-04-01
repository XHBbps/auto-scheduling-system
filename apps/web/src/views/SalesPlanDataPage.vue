<template>
  <div class="space-y-6">
    <div class="tech-card p-6">
      <el-form :model="searchForm" inline class="flex flex-wrap gap-4">
        <el-form-item :label="labels.contractNo" class="!mb-0">
          <el-input v-model="searchForm.contractNo" :placeholder="labels.inputPlaceholder" clearable class="!w-36" />
        </el-form-item>
        <el-form-item :label="labels.customerName" class="!mb-0">
          <el-input v-model="searchForm.customerName" :placeholder="labels.inputPlaceholder" clearable class="!w-36" />
        </el-form-item>
        <el-form-item :label="labels.productSeries" class="!mb-0">
          <el-input v-model="searchForm.productSeries" :placeholder="labels.inputPlaceholder" clearable class="!w-36" />
        </el-form-item>
        <el-form-item :label="labels.productModel" class="!mb-0">
          <el-input v-model="searchForm.productModel" :placeholder="labels.inputPlaceholder" clearable class="!w-36" />
        </el-form-item>
        <el-form-item :label="labels.materialNo" class="!mb-0">
          <el-input v-model="searchForm.materialNo" :placeholder="labels.inputPlaceholder" clearable class="!w-36" />
        </el-form-item>
        <el-form-item :label="labels.businessGroup" class="!mb-0">
          <el-select v-model="searchForm.businessGroup" :placeholder="labels.selectPlaceholder" clearable filterable class="!w-40">
            <el-option v-for="item in businessGroupOptions" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item :label="labels.salesBranchCompany" class="!mb-0">
          <el-select v-model="searchForm.salesBranchCompany" :placeholder="labels.selectPlaceholder" clearable filterable class="!w-40">
            <el-option v-for="item in salesBranchCompanyOptions" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item :label="labels.salesSubBranch" class="!mb-0">
          <el-select v-model="searchForm.salesSubBranch" :placeholder="labels.selectPlaceholder" clearable filterable class="!w-40">
            <el-option v-for="item in salesSubBranchOptions" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item class="!mb-0 ml-auto">
          <el-button type="primary" @click="handleSearch" class="!px-6">{{ labels.search }}</el-button>
          <el-button @click="handleReset">{{ labels.reset }}</el-button>
        </el-form-item>
      </el-form>
    </div>

    <div class="tech-card p-6">
      <el-table v-loading="loading" :data="tableData" style="width: 100%" class="sales-plan-table app-data-table" @sort-change="handleTableSortChange" table-layout="fixed">
        <template #empty>
          <AppTableState
            :state="tableFeedbackState"
            :empty-text="labels.empty"
            error-action-text="重新加载"
            auth-action-text="前往登录"
            @action="handleTableStateAction"
          />
        </template>
        <el-table-column prop="contract_no" :label="labels.contractNo" width="144" show-overflow-tooltip v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="text-white font-medium">{{ row.contract_no || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="customer_name" :label="labels.customerName" width="180" show-overflow-tooltip v-bind="sortableColumnProps" />
        <el-table-column prop="product_series" :label="labels.productSeries" width="120" v-bind="sortableColumnProps" />
        <el-table-column prop="product_model" :label="labels.productModel" width="120" show-overflow-tooltip v-bind="sortableColumnProps" />
        <el-table-column prop="product_name" :label="labels.productName" width="200" show-overflow-tooltip v-bind="sortableColumnProps" />
        <el-table-column prop="material_no" :label="labels.materialNo" width="136" show-overflow-tooltip v-bind="sortableColumnProps" />
        <el-table-column prop="quantity" :label="labels.quantity" width="88" align="center" v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="font-mono-num">{{ row.quantity ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="order_type" :label="labels.orderType" width="108" align="center" v-bind="sortableColumnProps">
          <template #default="{ row }">
            <AppStatusBadge v-bind="getOrderTypeBadgeMeta(row.order_type)" />
          </template>
        </el-table-column>
        <el-table-column prop="drawing_released" :label="labels.drawingReleased" width="108" align="center" v-bind="sortableColumnProps">
          <template #default="{ row }">
            <AppStatusBadge v-bind="getDrawingReleasedBadgeMeta(row.drawing_released, labels.drawingReleasedYes, labels.drawingReleasedNo)" />
          </template>
        </el-table-column>
        <el-table-column prop="confirmed_delivery_date" :label="labels.confirmedDeliveryDate" width="144" v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="font-mono-num text-sm text-text-secondary">{{ formatDate(row.confirmed_delivery_date) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="order_date" :label="labels.orderDate" width="144" v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="font-mono-num text-sm text-text-secondary">{{ formatDate(row.order_date) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="line_total_amount" :label="labels.contractAmount" width="128" align="right" v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="font-mono-num text-text-secondary">{{ formatAmount(row.line_total_amount) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="business_group" :label="labels.businessGroup" width="120" align="center" show-overflow-tooltip v-bind="sortableColumnProps">
          <template #default="{ row }">
            <AppStatusBadge v-bind="getBusinessGroupBadgeMeta(row.business_group)" />
          </template>
        </el-table-column>
        <el-table-column prop="custom_no" :label="labels.customNo" width="120" show-overflow-tooltip v-bind="sortableColumnProps" />
        <el-table-column prop="sales_person_name" :label="labels.salesPersonName" width="120" show-overflow-tooltip v-bind="sortableColumnProps" />
        <el-table-column prop="sales_branch_company" :label="labels.salesBranchCompany" width="128" align="center" show-overflow-tooltip v-bind="sortableColumnProps">
          <template #default="{ row }">
            <AppStatusBadge v-bind="getSalesBranchCompanyBadgeMeta(row.sales_branch_company)" />
          </template>
        </el-table-column>
        <el-table-column prop="sales_sub_branch" :label="labels.salesSubBranch" width="128" align="center" show-overflow-tooltip v-bind="sortableColumnProps">
          <template #default="{ row }">
            <AppStatusBadge v-bind="getSalesSubBranchBadgeMeta(row.sales_sub_branch)" />
          </template>
        </el-table-column>
        <el-table-column prop="order_no" :label="labels.orderNo" width="128" show-overflow-tooltip v-bind="sortableColumnProps" />
        <el-table-column prop="sap_code" :label="labels.sapCode" width="128" show-overflow-tooltip v-bind="sortableColumnProps" />
        <el-table-column prop="sap_line_no" :label="labels.sapLineNo" width="112" show-overflow-tooltip v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="font-mono-num text-text-secondary">{{ row.sap_line_no || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="custom_requirement" :label="labels.customRequirement" width="220" show-overflow-tooltip v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="text-text-secondary">{{ row.custom_requirement || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="review_comment" :label="labels.reviewComment" width="220" show-overflow-tooltip v-bind="sortableColumnProps">
          <template #default="{ row }">
            <span class="text-text-secondary">{{ row.review_comment || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" :label="labels.syncTime" width="176" v-bind="sortableColumnProps">
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
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppTableState from '../components/AppTableState.vue'
import AppStatusBadge from '../components/AppStatusBadge.vue'
import { BUSINESS_TERMS } from '../constants/terminology'
import { useRemoteTableQuery } from '../composables/useServerTableQuery'
import { createTableStateActionHandler } from '../composables/useTableFeedbackState'
import request from '../utils/httpClient'
import { formatDate, formatDateTime } from '../utils/format'
import {
  getBusinessGroupBadgeMeta,
  getDrawingReleasedBadgeMeta,
  getOrderTypeBadgeMeta,
  getSalesBranchCompanyBadgeMeta,
  getSalesSubBranchBadgeMeta,
} from '../utils/statusPresentation'

const router = useRouter()
const route = useRoute()

const labels = {
  contractNo: BUSINESS_TERMS.contractNo,
  customerName: '客户名称',
  productSeries: '产品系列',
  productModel: '产品型号',
  productName: '产品名称',
  materialNo: '物料编号',
  quantity: '数量',
  orderType: '订单类型',
  drawingReleased: BUSINESS_TERMS.drawingReleased,
  drawingReleasedYes: BUSINESS_TERMS.drawingReleasedYes,
  drawingReleasedNo: BUSINESS_TERMS.drawingReleasedNo,
  confirmedDeliveryDate: BUSINESS_TERMS.confirmedDeliveryDate,
  orderDate: '订单日期',
  contractAmount: '合同金额',
  businessGroup: '事业群',
  customNo: '定制号',
  salesPersonName: '销售人员',
  salesBranchCompany: '分公司',
  salesSubBranch: '支公司',
  orderNo: BUSINESS_TERMS.salesOrderNo,
  sapCode: 'SAP编码',
  sapLineNo: 'SAP行号',
  customRequirement: '定制要求',
  reviewComment: '评审意见',
  syncTime: BUSINESS_TERMS.syncTime,
  inputPlaceholder: '请输入',
  selectPlaceholder: '请选择',
  search: '搜索',
  reset: '重置',
  empty: '暂无数据',
}

interface SalesPlanItem {
  id: number
  contract_no?: string
  customer_name?: string
  product_series?: string
  product_model?: string
  product_name?: string
  material_no?: string
  quantity?: number
  line_total_amount?: number
  confirmed_delivery_date?: string
  delivery_date?: string
  order_type?: string
  business_group?: string
  custom_no?: string
  sales_person_name?: string
  order_date?: string
  sales_branch_company?: string
  sales_sub_branch?: string
  drawing_released: boolean
  drawing_release_date?: string
  order_no?: string
  sap_code?: string
  sap_line_no?: string
  custom_requirement?: string
  review_comment?: string
  created_at?: string
}

interface PaginatedResponse {
  total: number
  page_no: number
  page_size: number
  items: SalesPlanItem[]
}

interface SalesPlanOrgFilterOptions {
  business_groups: string[]
  sales_branch_companies: string[]
  sales_sub_branches: string[]
}

const createSearchForm = () => ({
  contractNo: '',
  customerName: '',
  productSeries: '',
  productModel: '',
  materialNo: '',
  businessGroup: '',
  salesBranchCompany: '',
  salesSubBranch: '',
})

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
  perfScope: 'salesPlanData',
  perfLabel: 'fetchSalesPlanTable',
  buildPerfMeta: (params) => ({
    hasContractNo: Boolean(params.contract_no),
    hasCustomerName: Boolean(params.customer_name),
    hasProductSeries: Boolean(params.product_series),
    hasProductModel: Boolean(params.product_model),
    hasMaterialNo: Boolean(params.material_no),
  }),

  searchParamKeyMap: {
    contractNo: 'contract_no',
    customerName: 'customer_name',
    productSeries: 'product_series',
    productModel: 'product_model',
    materialNo: 'material_no',
    businessGroup: 'business_group',
    salesBranchCompany: 'sales_branch_company',
    salesSubBranch: 'sales_sub_branch',
  },
  sortFieldMap: {
    contract_no: 'contract_no',
    customer_name: 'customer_name',
    product_series: 'product_series',
    product_model: 'product_model',
    product_name: 'product_name',
    material_no: 'material_no',
    quantity: 'quantity',
    order_type: 'order_type',
    drawing_released: 'drawing_released',
    confirmed_delivery_date: 'confirmed_delivery_date',
    order_date: 'order_date',
    line_total_amount: 'line_total_amount',
    business_group: 'business_group',
    custom_no: 'custom_no',
    sales_person_name: 'sales_person_name',
    sales_branch_company: 'sales_branch_company',
    sales_sub_branch: 'sales_sub_branch',
    order_no: 'order_no',
    sap_code: 'sap_code',
    sap_line_no: 'sap_line_no',
    custom_requirement: 'custom_requirement',
    review_comment: 'review_comment',
    created_at: 'created_at',
  },
  request: (params) =>
    request.get<PaginatedResponse>('/api/data/sales-plan-orders', {
      params,
      silentError: true,
    }),
})

const businessGroupOptions = ref<string[]>([])
const salesBranchCompanyOptions = ref<string[]>([])
const salesSubBranchOptions = ref<string[]>([])

const handleTableStateAction = createTableStateActionHandler({
  tableFeedbackState,
  retry: fetchData,
  router,
  redirectPath: route.fullPath,
})

const formatAmount = (value?: number | null) => {
  if (value === null || value === undefined) return '-'
  return new Intl.NumberFormat('zh-CN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(value)
}

const fetchOrgFilterOptions = async () => {
  try {
    const res = await request.get<SalesPlanOrgFilterOptions>('/api/data/sales-plan-orders/options/org-filters')
    businessGroupOptions.value = res.business_groups || []
    salesBranchCompanyOptions.value = res.sales_branch_companies || []
    salesSubBranchOptions.value = res.sales_sub_branches || []
  } catch (error) {
    console.error(error)
  }
}

onMounted(() => {
  void fetchOrgFilterOptions()
  void fetchData()
})
</script>

