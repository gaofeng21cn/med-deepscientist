export interface SystemLogSource {
  source_id: string
  source_type: string
  label: string
  filename?: string
  exists?: boolean
  quest_id?: string
  bash_id?: string
}

export interface SystemChartEntry {
  chart_id: string
  title: string
  description?: string
  kind: string
}

export interface SystemChartPoint {
  label: string
  value: number
}

export interface SystemOverviewPayload {
  ok: boolean
  counts: Record<string, number>
  quest_status_counts?: Record<string, number>
  connectors?: Record<string, unknown>
  updated_at?: string
}

export interface SystemQuestListPayload {
  ok: boolean
  items: Array<Record<string, unknown>>
  total: number
  status_counts: Record<string, number>
  updated_at?: string
}

export interface SystemQuestSummaryPayload {
  ok: boolean
  quest: Record<string, unknown>
  runtime_audit: Record<string, unknown>
  bash_sessions: Array<Record<string, unknown>>
  updated_at?: string
}

export interface SystemRuntimeSessionsPayload {
  ok: boolean
  quest_sessions: Array<Record<string, unknown>>
  connector_sessions: Array<Record<string, unknown>>
  bash_sessions: Array<Record<string, unknown>>
  totals: Record<string, number>
  updated_at?: string
}

export interface SystemLogSourcesPayload {
  ok: boolean
  items: SystemLogSource[]
  total: number
  updated_at?: string
}

export interface SystemLogTailPayload {
  ok: boolean
  source_id: string
  filename: string
  lines: string[]
  truncated: boolean
  updated_at?: string | null
}

export interface SystemFailureListPayload {
  ok: boolean
  items: Array<Record<string, unknown>>
  total: number
  updated_at?: string
}

export interface SystemRuntimeToolsPayload {
  ok: boolean
  items: Array<Record<string, unknown>>
  total: number
  available_count?: number
  updated_at?: string
}

export interface SystemHardwarePayload extends Record<string, unknown> {
  ok: boolean
}

export interface SystemChartCatalogPayload {
  ok: boolean
  items: SystemChartEntry[]
  total: number
}

export interface SystemChartPayload {
  ok: boolean
  chart_id: string
  title: string
  description?: string
  kind: string
  series: SystemChartPoint[]
  updated_at?: string
}

export interface SystemStatsSummaryPayload {
  ok: boolean
  quest_status_counts: Record<string, number>
  connector_status_counts: Record<string, number>
  runtime_session_counts: Record<string, number>
  failure_counts: Record<string, number>
  runtime_tools_available?: number
  updated_at?: string
}

export interface SystemSearchPayload {
  ok: boolean
  items: Array<Record<string, unknown>>
  total: number
  query: string
  scope: string
}
