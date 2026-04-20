import { api } from '@/lib/api'
import type {
  SystemChartCatalogPayload,
  SystemChartPayload,
  SystemFailureListPayload,
  SystemHardwarePayload,
  SystemLogSourcesPayload,
  SystemLogTailPayload,
  SystemOverviewPayload,
  SystemQuestListPayload,
  SystemQuestSummaryPayload,
  SystemRuntimeSessionsPayload,
  SystemRuntimeToolsPayload,
  SystemSearchPayload,
  SystemStatsSummaryPayload,
} from '@/lib/types/admin'

export const adminClient = {
  systemOverview: () => api<SystemOverviewPayload>('/api/system/overview'),
  systemQuests: (params?: { status?: string; q?: string; limit?: number }) => {
    const searchParams = new URLSearchParams()
    if (params?.status) searchParams.set('status', params.status)
    if (params?.q) searchParams.set('q', params.q)
    if (params?.limit) searchParams.set('limit', String(params.limit))
    const suffix = searchParams.toString()
    return api<SystemQuestListPayload>(`/api/system/quests${suffix ? `?${suffix}` : ''}`)
  },
  systemQuestSummary: (questId: string) =>
    api<SystemQuestSummaryPayload>(`/api/system/quests/${encodeURIComponent(questId)}/summary`),
  systemRuntimeSessions: (limit?: number) =>
    api<SystemRuntimeSessionsPayload>(`/api/system/runtime/sessions${limit ? `?limit=${limit}` : ''}`),
  systemLogSources: () => api<SystemLogSourcesPayload>('/api/system/logs/sources'),
  systemLogTail: (sourceId: string, limit = 200) =>
    api<SystemLogTailPayload>(`/api/system/logs/${encodeURIComponent(sourceId)}/tail?limit=${limit}`),
  systemFailures: (params?: { q?: string; severity?: string; limit?: number }) => {
    const searchParams = new URLSearchParams()
    if (params?.q) searchParams.set('q', params.q)
    if (params?.severity) searchParams.set('severity', params.severity)
    if (params?.limit) searchParams.set('limit', String(params.limit))
    const suffix = searchParams.toString()
    return api<SystemFailureListPayload>(`/api/system/failures${suffix ? `?${suffix}` : ''}`)
  },
  systemRuntimeTools: () => api<SystemRuntimeToolsPayload>('/api/system/runtime-tools'),
  systemHardware: () => api<SystemHardwarePayload>('/api/system/hardware'),
  systemCharts: () => api<SystemChartCatalogPayload>('/api/system/charts'),
  systemChart: (chartId: string) => api<SystemChartPayload>(`/api/system/charts/${encodeURIComponent(chartId)}`),
  systemStatsSummary: () => api<SystemStatsSummaryPayload>('/api/system/stats/summary'),
  systemSearch: (query: string, params?: { scope?: string; limit?: number }) => {
    const searchParams = new URLSearchParams()
    searchParams.set('q', query)
    if (params?.scope) searchParams.set('scope', params.scope)
    if (params?.limit) searchParams.set('limit', String(params.limit))
    return api<SystemSearchPayload>(`/api/system/search?${searchParams.toString()}`)
  },
}

export default adminClient
