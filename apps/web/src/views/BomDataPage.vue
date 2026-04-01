<template>
  <div class="space-y-6">
    <div class="tech-card p-6">
      <div class="flex flex-wrap items-center gap-3">
        <el-button :type="activeTab === 'tree' ? 'primary' : 'default'" @click="activeTab = 'tree'">树状结构</el-button>
        <el-button :type="activeTab === 'list' ? 'primary' : 'default'" @click="activeTab = 'list'">平铺列表</el-button>
      </div>

      <el-form
        v-if="activeTab === 'tree'"
        :model="treeForm"
        inline
        class="mt-6 flex flex-wrap gap-4"
      >
        <el-form-item label="整机物料号" class="!mb-0">
          <el-input
            v-model="treeForm.machine_material_no"
            placeholder=""
            clearable
            class="!w-80"
            @keyup.enter="handleTreeSearch"
          />
        </el-form-item>
        <el-form-item class="!mb-0 ml-auto">
          <el-button type="primary" @click="handleTreeSearch" class="!px-6">搜索</el-button>
          <el-button @click="handleTreeReset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-form
        v-else
        :model="listForm"
        inline
        class="mt-6 flex flex-wrap gap-4"
      >
        <el-form-item label="整机物料号" class="!mb-0">
          <el-input v-model="listForm.machine_material_no" placeholder="请输入" clearable class="!w-40" />
        </el-form-item>
        <el-form-item label="物料编号" class="!mb-0">
          <el-input v-model="listForm.material_no" placeholder="请输入" clearable class="!w-36" />
        </el-form-item>
        <el-form-item label="BOM组件号" class="!mb-0">
          <el-input v-model="listForm.bom_component_no" placeholder="请输入" clearable class="!w-36" />
        </el-form-item>
        <el-form-item label="类型" class="!mb-0">
          <el-input v-model="listForm.part_type" placeholder="请输入" clearable class="!w-32" />
        </el-form-item>
        <el-form-item class="!mb-0 ml-auto">
          <el-button type="primary" @click="handleListSearch" class="!px-6">搜索</el-button>
          <el-button @click="handleListReset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <BomTreeSection
      v-if="activeTab === 'tree'"
      v-model:current-page="treePageNo"
      v-model:page-size="treePageSize"
      :loading="treeLoading"
      :data="pagedTreeTableData"
      :machine-material-no="treeForm.machine_material_no"
      :page-sizes="treePageSizes"
      :total="treeTotal"
      :sortable-column-props="sortableColumnProps"
      :load-tree-node="loadTreeNode"
      :handle-load-more="handleLoadMore"
      :handle-sort-change="handleTreeSortChange"
    />

    <BomListSection
      v-else
      v-model:current-page="pageNo"
      v-model:page-size="pageSize"
      :loading="listLoading"
      :data="listTableData"
      :total="total"
      :sortable-column-props="sortableColumnProps"
      @refresh="fetchListData"
      @sort-change="handleListSortChange"
    />
  </div>
</template>

<script setup lang="ts">
import BomListSection from '../components/bom-data/BomListSection.vue'
import BomTreeSection from '../components/bom-data/BomTreeSection.vue'
import { useBomDataPage } from '../composables/useBomDataPage'
import { getTableSortColumnProps } from '../composables/useTableSort'

const sortableColumnProps = getTableSortColumnProps()
const {
  activeTab,
  treeForm,
  treeLoading,
  treePageNo,
  treePageSize,
  treePageSizes,
  treeTotal,
  pagedTreeTableData,
  listForm,
  listLoading,
  listTableData,
  pageNo,
  pageSize,
  total,
  loadTreeNode,
  handleLoadMore,
  fetchListData,
  handleTreeSearch,
  handleTreeReset,
  handleListSearch,
  handleListReset,
  handleListSortChange,
  handleTreeSortChange,
} = useBomDataPage()
</script>
