import type { QuestSummary } from '@/types'

export type AdminScalar = string | number | boolean | null
export type AdminJsonValue = AdminScalar | AdminJsonObject | AdminJsonValue[]

export interface AdminJsonObject {
  [key: string]: AdminJsonValue | undefined
}

export interface SystemCollectionResponse<T extends AdminJsonObject = AdminJsonObject> extends AdminJsonObject {
  items?: T[]
}

export interface SystemOverviewResponse extends AdminJsonObject {
  ok?: boolean
  generated_at?: string | null
  status?: string | null
  updated_at?: string | null
  counts?: AdminJsonObject | null
  quest_status_counts?: AdminJsonObject | null
  connectors?: AdminJsonObject | null
  daemon?: AdminJsonObject | null
}

export interface SystemQuestItem extends AdminJsonObject, Partial<QuestSummary> {
  quest_id?: string
  title?: string
  status?: string
  runtime_status?: string
}

export interface SystemQuestListResponse extends SystemCollectionResponse<SystemQuestItem> {}

export interface SystemQuestSummaryResponse extends AdminJsonObject {
  ok?: boolean
  quest_id?: string
  summary?: string | AdminJsonObject | AdminJsonValue[] | null
  status_line?: string | null
  snapshot?: AdminJsonObject | null
  quest?: AdminJsonObject | null
  runtime_audit?: AdminJsonObject | null
  bash_sessions?: AdminJsonObject[]
  updated_at?: string | null
}

export interface SystemRuntimeSession extends AdminJsonObject {
  session_id?: string
  quest_id?: string
  state?: string
  status?: string
  source_kind?: string
  title?: string
}

export interface SystemRuntimeSessionListResponse extends AdminJsonObject {
  ok?: boolean
  quest_sessions?: AdminJsonObject[]
  connector_sessions?: AdminJsonObject[]
  bash_sessions?: AdminJsonObject[]
  totals?: AdminJsonObject | null
  updated_at?: string | null
}

export interface SystemLogSource extends AdminJsonObject {
  source_id?: string
  label?: string
  kind?: string
  source_type?: string
  filename?: string
  exists?: boolean
}

export interface SystemLogSourceListResponse extends SystemCollectionResponse<SystemLogSource> {}

export interface SystemLogTailResponse extends AdminJsonObject {
  ok?: boolean
  source_id?: string
  lines?: string[]
  filename?: string
  truncated?: boolean
  updated_at?: string | null
}

export interface SystemFailureItem extends AdminJsonObject {
  id?: string
  failure_id?: string
  severity?: string
  summary?: string
  status?: string
  source?: string
  event_type?: string
  quest_id?: string
  created_at?: string | null
}

export interface SystemFailureListResponse extends SystemCollectionResponse<SystemFailureItem> {}

export interface SystemRuntimeTool extends AdminJsonObject {
  tool_name?: string
  kind?: string
  available?: boolean
  status?: string
  summary?: string
}

export interface SystemRuntimeToolListResponse extends SystemCollectionResponse<SystemRuntimeTool> {
  ok?: boolean
  total?: number
  available_count?: number
  updated_at?: string | null
}

export interface SystemHardwareResponse extends AdminJsonObject {}

export interface SystemChartCatalogItem extends AdminJsonObject {
  chart_id?: string
  title?: string
  description?: string
}

export interface SystemChartCatalogResponse extends SystemCollectionResponse<SystemChartCatalogItem> {}

export interface SystemChartResponse extends AdminJsonObject {
  ok?: boolean
  chart_id?: string
  title?: string
  description?: string
  kind?: string
  updated_at?: string | null
}

export interface SystemStatsSummaryResponse extends AdminJsonObject {
  ok?: boolean
  updated_at?: string | null
  quest_status_counts?: AdminJsonObject | null
  connector_status_counts?: AdminJsonObject | null
  runtime_session_counts?: AdminJsonObject | null
  failure_counts?: AdminJsonObject | null
  runtime_tools_available?: number
}

export interface SystemSearchResultItem extends AdminJsonObject {
  result_id?: string
  title?: string
  snippet?: string
  kind?: string
  label?: string
  description?: string
  result_type?: string
}

export interface SystemSearchResponse extends SystemCollectionResponse<SystemSearchResultItem> {
  ok?: boolean
  total?: number
  query?: string
  scope?: string
}
