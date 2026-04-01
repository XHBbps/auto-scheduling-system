<template>
  <div class="tech-card p-6 relative overflow-hidden group hover:border-brand/50 transition-colors duration-300">
    <div class="flex items-start justify-between gap-6 flex-wrap relative">
      <div>
        <div class="flex items-center gap-4 mb-3">
          <div class="w-12 h-12 rounded-xl bg-[#242827] flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
            <el-icon size="24" class="text-brand">
              <Timer />
            </el-icon>
          </div>
          <div>
            <div class="text-white text-lg font-semibold tracking-wider">自动同步调度器</div>
            <div class="text-[#717a82] text-sm mt-1">查看调度器启停状态、时区和下次计划执行时间。</div>
          </div>
        </div>
        <div class="flex items-center gap-3 flex-wrap mt-4">
          <AppStatusBadge v-bind="props.schedulerStateBadgeMeta" size="md" />
          <span class="text-xs text-[#717a82] bg-[#121413] px-2 py-1 rounded-md border border-[#2a2e2d]">
            时区：{{ props.schedulerStatus.timezone || '--' }}
          </span>
          <span class="text-xs text-[#717a82] bg-[#121413] px-2 py-1 rounded-md border border-[#2a2e2d]">
            最近刷新：{{ props.schedulerLastUpdatedAt }}
          </span>
        </div>
      </div>

      <div class="flex items-center gap-4 ml-auto bg-[#121413] p-3 rounded-xl border border-[#2a2e2d]">
        <div class="text-right mr-2">
          <div class="text-[10px] uppercase tracking-widest text-[#717a82] mb-1">AUTO SYNC</div>
          <div class="text-sm font-medium" :class="schedulerEnabled ? 'text-brand' : 'text-[#a0aab2]'">
            {{ schedulerEnabled ? '已启用' : '已暂停' }}
          </div>
        </div>

        <el-switch
          v-model="schedulerEnabled"
          size="large"
          inline-prompt
          active-text="ON"
          inactive-text="OFF"
          :loading="props.schedulerLoading"
          :style="{
            '--el-switch-on-color': '#82d695',
            '--el-switch-off-color': '#2a2e2d',
          }"
          @change="props.onHandleSchedulerToggle"
        />

        <div class="w-[1px] h-8 bg-[#2a2e2d] mx-2" />

        <el-button
          plain
          class="!bg-transparent !border-[#2a2e2d] !text-[#a0aab2] hover:!text-brand hover:!border-brand"
          :loading="props.schedulerRefreshing"
          @click="props.onLoadSchedulerStatus"
        >
          刷新状态
        </el-button>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mt-6 relative">
      <div
        v-for="job in props.schedulerStatus.jobs"
        :key="job.id"
        class="rounded-xl border border-[#2a2e2d] bg-[#121413] p-4 hover:border-brand/30 transition-colors"
      >
        <div class="flex items-center justify-between gap-3 mb-4">
          <div class="text-sm font-medium text-[#a0aab2]">
            {{ props.schedulerJobNameMap[job.id] || job.name }}
          </div>
          <div class="flex items-center justify-center w-6 h-6 rounded-full bg-[#1a1d1c]">
            <span
              class="w-2 h-2 rounded-full"
              :class="schedulerEnabled ? 'bg-brand shadow-[0_0_8px_rgba(130,214,149,0.8)]' : 'bg-[#717a82]'"
            />
          </div>
        </div>
        <div class="text-[10px] uppercase tracking-widest text-[#717a82] mb-1">NEXT RUN</div>
        <div class="text-sm text-white font-mono-num">{{ props.formatRunTime(job.next_run_time) }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Timer } from '@element-plus/icons-vue'
import AppStatusBadge from '../AppStatusBadge.vue'
import type { SyncSchedulerStatus } from '../../types/apiModels'
import type { StatusBadgeMeta } from '../../utils/statusPresentation'

const props = defineProps<{
  schedulerJobNameMap: Record<string, string>
  schedulerLastUpdatedAt: string
  schedulerLoading: boolean
  schedulerRefreshing: boolean
  schedulerStateBadgeMeta: StatusBadgeMeta
  schedulerStatus: SyncSchedulerStatus
  formatRunTime: (value?: string | null) => string
  onHandleSchedulerToggle: (value: string | number | boolean) => void | Promise<void>
  onLoadSchedulerStatus: () => void | Promise<void>
}>()

const schedulerEnabled = defineModel<boolean>('schedulerEnabled', { required: true })
</script>
