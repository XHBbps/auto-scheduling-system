<template>
  <div class="tech-card p-6">
    <el-form :model="searchForm" inline class="flex flex-wrap gap-4">
      <el-form-item label="合同号" class="!mb-0">
        <el-input v-model="contractNoModel" placeholder="请输入" clearable class="!w-48" />
      </el-form-item>
      <el-form-item label="客户名称" class="!mb-0">
        <el-input v-model="customerNameModel" placeholder="请输入" clearable class="!w-48" />
      </el-form-item>
      <el-form-item label="产品系列" class="!mb-0">
        <el-select v-model="productSeriesModel" placeholder="请选择" clearable class="!w-32">
          <el-option v-for="item in productSeriesOptions" :key="item" :label="item" :value="item" />
        </el-select>
      </el-form-item>
      <el-form-item label="产品型号" class="!mb-0">
        <el-input v-model="productModelModel" placeholder="请输入" clearable class="!w-32" />
      </el-form-item>
      <el-form-item label="销售订单" class="!mb-0">
        <el-input v-model="orderNoModel" placeholder="请输入" clearable class="!w-48" />
      </el-form-item>
      <el-form-item label="排产状态" class="!mb-0">
        <el-select v-model="scheduleStatusModel" placeholder="请选择" clearable class="!w-32">
          <el-option v-for="(val, key) in SCHEDULE_STATUS_MAP" :key="key" :label="val.label" :value="key" />
        </el-select>
      </el-form-item>
      <el-form-item label="异常标识" class="!mb-0">
        <el-select v-model="warningLevelModel" placeholder="请选择" clearable class="!w-32">
          <el-option v-for="(val, key) in WARNING_LEVEL_MAP" :key="key" :label="val.label" :value="key" />
        </el-select>
      </el-form-item>
      <el-form-item label="日期范围" class="!mb-0">
        <el-date-picker
          v-model="dateRangeModel"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          clearable
          class="!w-64"
        />
      </el-form-item>
      <el-form-item class="!mb-0 ml-auto">
        <el-button type="primary" class="!px-6" @click="$emit('search')">搜索</el-button>
        <el-button @click="$emit('reset')">重置</el-button>
        <el-button type="success" plain :loading="exporting" @click="$emit('export')">
          {{ exporting ? '导出中...' : '导出 Excel' }}
        </el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { computed, type PropType } from 'vue'
import { SCHEDULE_STATUS_MAP, WARNING_LEVEL_MAP } from '../../constants/enums'
import type { MachineScheduleSearchForm } from '../../composables/useMachineScheduleListPage'

const props = defineProps({
  dateRange: {
    type: Array as unknown as PropType<[string, string] | null>,
    default: null,
  },
  exporting: {
    type: Boolean,
    required: true,
  },
  productSeriesOptions: {
    type: Array as PropType<string[]>,
    required: true,
  },
  searchForm: {
    type: Object as PropType<MachineScheduleSearchForm>,
    required: true,
  },
})

const emit = defineEmits<{
  (event: 'update:dateRange', value: [string, string] | null): void
  (event: 'update:searchForm', value: MachineScheduleSearchForm): void
  (event: 'search'): void
  (event: 'reset'): void
  (event: 'export'): void
}>()

const updateSearchForm = (field: keyof MachineScheduleSearchForm, value: string) => {
  emit('update:searchForm', {
    ...props.searchForm,
    [field]: value,
  })
}

const createFieldModel = (field: keyof MachineScheduleSearchForm) =>
  computed({
    get: () => props.searchForm[field],
    set: (value: string) => updateSearchForm(field, value),
  })

const contractNoModel = createFieldModel('contractNo')
const customerNameModel = createFieldModel('customerName')
const productSeriesModel = createFieldModel('productSeries')
const productModelModel = createFieldModel('productModel')
const orderNoModel = createFieldModel('orderNo')
const scheduleStatusModel = createFieldModel('scheduleStatus')
const warningLevelModel = createFieldModel('warningLevel')

const dateRangeModel = computed({
  get: () => props.dateRange,
  set: (value) => emit('update:dateRange', value),
})
</script>
