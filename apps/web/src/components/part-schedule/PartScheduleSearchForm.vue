<template>
  <div class="tech-card p-6">
    <el-form :model="searchForm" inline class="flex flex-wrap gap-4">
      <el-form-item label="销售订单" class="!mb-0">
        <el-input v-model="orderNoModel" placeholder="请输入" clearable class="!w-40" />
      </el-form-item>
      <el-form-item label="合同号" class="!mb-0">
        <el-input v-model="contractNoModel" placeholder="请输入" clearable class="!w-40" />
      </el-form-item>
      <el-form-item label="装配名称" class="!mb-0">
        <el-select v-model="assemblyNameModel" placeholder="请选择" clearable filterable class="!w-48">
          <el-option v-for="item in assemblyOptions" :key="item" :label="item" :value="item" />
        </el-select>
      </el-form-item>
      <el-form-item label="零件料号" class="!mb-0">
        <el-input v-model="partMaterialNoModel" placeholder="请输入" clearable class="!w-44" />
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
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { computed, type PropType } from 'vue'
import { WARNING_LEVEL_MAP } from '../../constants/enums'
import type { PartScheduleSearchForm } from '../../composables/usePartScheduleListPage'

const props = defineProps({
  exporting: {
    type: Boolean,
    required: true,
  },
  assemblyOptions: {
    type: Array as PropType<string[]>,
    required: true,
  },
  dateRange: {
    type: Array as unknown as PropType<[string, string] | null>,
    default: null,
  },
  searchForm: {
    type: Object as PropType<PartScheduleSearchForm>,
    required: true,
  },
})

const emit = defineEmits<{
  (event: 'update:dateRange', value: [string, string] | null): void
  (event: 'update:searchForm', value: PartScheduleSearchForm): void
  (event: 'search'): void
  (event: 'reset'): void
  (event: 'export'): void
}>()

const updateSearchForm = (field: keyof PartScheduleSearchForm, value: string) => {
  emit('update:searchForm', {
    ...props.searchForm,
    [field]: value,
  })
}

const createFieldModel = (field: keyof PartScheduleSearchForm) =>
  computed({
    get: () => props.searchForm[field],
    set: (value: string) => updateSearchForm(field, value),
  })

const orderNoModel = createFieldModel('orderNo')
const contractNoModel = createFieldModel('contractNo')
const assemblyNameModel = createFieldModel('assemblyName')
const partMaterialNoModel = createFieldModel('partMaterialNo')
const warningLevelModel = createFieldModel('warningLevel')

const dateRangeModel = computed({
  get: () => props.dateRange,
  set: (value) => emit('update:dateRange', value),
})
</script>
