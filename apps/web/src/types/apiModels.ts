/** 通用分页响应 */
export interface PaginatedResponse<T> {
  total: number
  page_no: number
  page_size: number
  items: T[]
}

export type ApiSortOrder = 'asc' | 'desc' | undefined

export interface TableSortState {
  sortField?: string
  sortOrder?: ApiSortOrder
}

/** 整机排产列表项 */
export interface MachineScheduleItem {
  order_line_id: number
  contract_no?: string
  customer_name?: string
  product_series?: string
  product_model?: string
  material_no?: string
  product_name?: string
  quantity?: number
  order_type?: string
  line_total_amount?: number | string
  order_date?: string
  business_group?: string
  custom_no?: string
  sales_person_name?: string
  sales_branch_company?: string
  sales_sub_branch?: string
  order_no?: string
  sap_code?: string
  sap_line_no?: string
  confirmed_delivery_date?: string
  drawing_released?: boolean
  drawing_release_date?: string
  custom_requirement?: string
  review_comment?: string
  trigger_date?: string
  planned_start_date?: string
  planned_end_date?: string
  warning_level?: string
  schedule_status?: string
  default_flags?: Record<string, any>
  machine_cycle_days?: number
  machine_assembly_days?: number
}

/** 零件排产列表项 */
export interface PartScheduleItem {
  id: number
  order_line_id: number
  contract_no?: string
  customer_name?: string
  product_series?: string
  product_model?: string
  product_name?: string
  material_no?: string
  quantity?: number
  order_type?: string
  custom_no?: string
  business_group?: string
  sales_person_name?: string
  sales_branch_company?: string
  sales_sub_branch?: string
  order_no?: string
  assembly_name: string
  production_sequence: number
  assembly_time_days?: number
  parent_material_no?: string
  parent_name?: string
  node_level?: number
  bom_path?: string
  bom_path_key?: string
  part_material_no?: string
  part_name?: string
  part_raw_material_desc?: string
  is_key_part?: boolean
  part_cycle_days?: number
  part_cycle_is_default?: boolean
  part_cycle_match_rule?: string
  key_part_material_no?: string
  key_part_name?: string
  key_part_raw_material_desc?: string
  key_part_cycle_days?: number
  planned_start_date?: string
  planned_end_date?: string
  order_date?: string
  confirmed_delivery_date?: string
  line_total_amount?: number | string
  warning_level?: string
  default_flags?: Record<string, any>
}

/** 异常记录 */
export interface IssueItem {
  id: number
  issue_type: string
  issue_level?: string
  source_system?: string
  biz_key?: string
  material_no?: string
  custom_no?: string
  order_no?: string
  contract_no?: string
  issue_title: string
  issue_detail?: string
  status: string
  created_at?: string
}

/** 排产详情 */
export interface ScheduleDetailResponse {
  machine_schedule: MachineScheduleItem
  part_schedules: PartScheduleItem[]
  issues: IssueItem[]
}

export interface DashboardSummaryCountItem {
  key: string
  count: number
}

export interface DashboardMonthCountItem {
  key: string
  count: number
}

export interface DashboardTopAssemblyItem {
  assembly_name: string
  count: number
}

export interface DashboardMachineSummary {
  total_orders: number
  scheduled_orders: number
  unscheduled_orders: number
  abnormal_orders: number
  status_counts: DashboardSummaryCountItem[]
  planned_end_month_counts: DashboardMonthCountItem[]
  planned_end_day_counts?: DashboardSummaryCountItem[]
  warning_orders: MachineScheduleItem[]
}

export interface DashboardPartSummary {
  total_parts: number
  abnormal_parts: number
  warning_counts: DashboardSummaryCountItem[]
  top_assemblies: DashboardTopAssemblyItem[]
}

export interface DashboardTimeSummary {
  delivery_count: number
  unscheduled_count: number
  abnormal_count: number
}

export interface DashboardTrendPoint {
  key: string
  label: string
  scheduled_count: number
  delivery_count: number
}

export interface DashboardDeliveryTrendSummary {
  day: DashboardTrendPoint[]
  week: DashboardTrendPoint[]
  month: DashboardTrendPoint[]
}

export interface DashboardBusinessGroupSummaryItem {
  business_group: string
  order_count: number
  total_amount: number | string
}

export interface DashboardOverviewResponse {
  machine_summary: DashboardMachineSummary
  part_summary: DashboardPartSummary
  today_summary: DashboardTimeSummary
  week_summary: DashboardTimeSummary
  month_summary: DashboardTimeSummary
  delivery_trends: DashboardDeliveryTrendSummary
  business_group_summary: DashboardBusinessGroupSummaryItem[]
  abnormal_machine_orders: MachineScheduleItem[]
  delivery_risk_orders: MachineScheduleItem[]
}

/** 排产运行结果 */
export interface ScheduleRunResponse {
  total: number
  success_count: number
  fail_count: number
  message?: string
}

export interface ScheduleValidationItem {
  code: string
  label: string
  message: string
  level: 'blocking' | 'warning' | string
}

export interface PartScheduleRunOneResponse {
  order_line_id: number
  success: boolean
  precheck_passed: boolean
  status: string
  message: string
  validation_items: ScheduleValidationItem[]
  machine_schedule_built: boolean
  part_schedule_built: boolean
  warning_summary?: string | null
}

/** 同步执行结果 */
export interface SyncOperationResult {
  success_count: number
  fail_count: number
  insert_count?: number
  update_count?: number
  issue_count?: number
  drawing_updated_count?: number
  message?: string
}

export interface SyncTriggerResponse {
  job_id?: number | null
  status?: string
  message?: string
}

export interface SyncLogProgress {
  kind?: string
  summary?: string
  batch_current?: number
  batch_total?: number
  candidate_orders?: number
  candidate_items?: number
  enqueued_items?: number
  reactivated_items?: number
  already_tracked_items?: number
  processed_items?: number
  deferred_items?: number
  success_count?: number
  fail_count?: number
  retry_wait_items?: number
  failed_items?: number
  drawing_updated_count?: number
  baseline_groups_processed?: number
  refreshed_order_count?: number
  closed_issue_count?: number
}

export interface SyncLogItem {
  id: number
  job_type: string
  source_system: string
  start_time?: string
  end_time?: string
  status: string
  success_count: number
  fail_count: number
  message?: string
  created_at?: string
  progress?: SyncLogProgress | null
}

export interface BomBackfillQueueItem {
  id: number
  material_no: string
  plant: string
  source: string
  trigger_reason?: string
  status: string
  priority: number
  fail_count: number
  failure_kind?: string | null
  last_error?: string | null
  next_retry_at?: string | null
  first_detected_at?: string | null
  last_attempt_at?: string | null
  resolved_at?: string | null
  last_job_id?: number | null
  updated_at?: string | null
}

export interface BomBackfillQueueSummary {
  pending: number
  processing: number
  retry_wait: number
  success: number
  failed: number
  paused: number
  retry_wait_due: number
  failure_kind_counts: Record<string, number>
  oldest_pending_age_minutes?: number | null
  latest_failed_items: BomBackfillQueueItem[]
}

export interface SyncObservabilityResponse {
  snapshot_total: number
  missing_bom_snapshot_count: number
  open_missing_bom_issue_count: number
  distinct_machine_bom_count: number
  running_job_count: number
  bom_backfill_queue: BomBackfillQueueSummary
  latest_sales_plan_job?: SyncLogItem | null
  latest_research_job?: SyncLogItem | null
  latest_auto_bom_job?: SyncLogItem | null
}

export interface RetryQueueResponse {
  updated_count: number
  message: string
}

/** 定时同步任务状态 */
export interface SyncSchedulerJobItem {
  id: string
  name: string
  next_run_time?: string | null
}

/** 定时同步总状态 */
export interface SyncSchedulerStatus {
  enabled: boolean
  state: 'running' | 'paused' | 'stopped' | string
  timezone: string
  jobs: SyncSchedulerJobItem[]
}

/** 装配时长配置项 */
export interface AssemblyTimeItem {
  id: number
  machine_model: string
  product_series: string
  assembly_name: string
  production_sequence: number
  assembly_time_days: number
  is_final_assembly?: boolean
  is_default?: boolean
  remark?: string
  key_part_material_no?: string
  key_part_name?: string
  key_part_cycle_days?: number
  updated_at?: string
}

/** 工作日历项 */
export interface WorkCalendarItem {
  id: number
  calendar_date: string
  is_workday: boolean
  remark?: string
}

export interface ScheduleCalendarDaySummary {
  calendar_date: string
  delivery_order_count: number
  delivery_quantity_sum: string | number
  trigger_order_count: number
  trigger_quantity_sum: string | number
  planned_start_order_count: number
  planned_start_quantity_sum: string | number
}

export interface ScheduleCalendarOrderItem {
  order_line_id: number
  contract_no?: string
  order_no?: string
  product_model?: string
  material_no?: string
  quantity?: string | number | null
  schedule_status?: string
  confirmed_delivery_date?: string
  trigger_date?: string
  planned_start_date?: string
}

export interface ScheduleCalendarDayDetailResponse {
  summary: ScheduleCalendarDaySummary
  delivery_orders: ScheduleCalendarOrderItem[]
  trigger_orders: ScheduleCalendarOrderItem[]
  planned_start_orders: ScheduleCalendarOrderItem[]
}


export interface RoleInfo {
  code: string
  name: string
}

export interface AuthenticatedUser {
  id: number
  username: string
  display_name: string
  is_active: boolean
  last_login_at?: string | null
  created_at?: string | null
  updated_at?: string | null
  roles: RoleInfo[]
  permission_codes?: string[]
}

export interface AuthSessionInfo {
  authenticated: boolean
  user?: AuthenticatedUser | null
  expires_at?: string | null
}

export interface AdminUserItem extends AuthenticatedUser {
  session_source?: string | null
}

export interface AdminUserDetail extends AdminUserItem {}

export interface AdminUserListPageResponse {
  total: number
  page_no: number
  page_size: number
  items: AdminUserItem[]
}

export interface AdminPermissionItem {
  id: number
  code: string
  name: string
  module_name: string
  description?: string | null
  sort_order: number
  is_active: boolean
  is_system: boolean
  created_at?: string | null
  updated_at?: string | null
}

export interface AdminPermissionListResponse {
  items: AdminPermissionItem[]
}

export interface AdminRoleItem {
  id: number
  code: string
  name: string
  description?: string | null
  is_active: boolean
  is_system: boolean
  assigned_user_count: number
  permission_count: number
  created_at?: string | null
  updated_at?: string | null
}

export interface AdminRoleDetail extends AdminRoleItem {
  permissions: AdminPermissionItem[]
}

export interface AdminRoleListResponse {
  items: AdminRoleItem[]
}

export interface AdminRolePermissionListResponse {
  role_id: number
  role_code: string
  role_name: string
  items: AdminPermissionItem[]
}
