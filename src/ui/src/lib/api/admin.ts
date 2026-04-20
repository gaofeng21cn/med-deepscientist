import { apiRequestJson } from '@/lib/api/request'
import type {
  SystemChartCatalogResponse,
  SystemChartResponse,
  SystemFailureListResponse,
  SystemHardwareResponse,
  SystemLogSourceListResponse,
  SystemLogTailResponse,
  SystemOverviewResponse,
  SystemQuestListResponse,
  SystemQuestSummaryResponse,
  SystemRuntimeSessionListResponse,
  SystemRuntimeToolListResponse,
  SystemSearchResponse,
  SystemStatsSummaryResponse,
} from '@/lib/types/admin'

const ADMIN_REQUEST_OPTIONS = {
  toastOnError: true,
  errorTitle: 'Unable to load system visibility data',
}

function withQuery(path: string, query?: Record<string, string | number | null | undefined>) {
  const params = new URLSearchParams()
  Object.entries(query || {}).forEach(([key, value]) => {
    if (value === null || value === undefined || value === '') {
      return
    }
    params.set(key, String(value))
  })
  const suffix = params.toString()
  return suffix ? `${path}?${suffix}` : path
}

export const adminApi = {
  getOverview: () =>
    apiRequestJson<SystemOverviewResponse>('/api/system/overview', {}, ADMIN_REQUEST_OPTIONS),
  getQuests: () =>
    apiRequestJson<SystemQuestListResponse>('/api/system/quests', {}, ADMIN_REQUEST_OPTIONS),
  getQuestSummary: (questId: string) =>
    apiRequestJson<SystemQuestSummaryResponse>(
      `/api/system/quests/${encodeURIComponent(questId)}/summary`,
      {},
      ADMIN_REQUEST_OPTIONS
    ),
  getRuntimeSessions: () =>
    apiRequestJson<SystemRuntimeSessionListResponse>(
      '/api/system/runtime/sessions',
      {},
      ADMIN_REQUEST_OPTIONS
    ),
  getLogSources: () =>
    apiRequestJson<SystemLogSourceListResponse>(
      '/api/system/logs/sources',
      {},
      ADMIN_REQUEST_OPTIONS
    ),
  getLogTail: (sourceId: string, limit = 200) =>
    apiRequestJson<SystemLogTailResponse>(
      withQuery(`/api/system/logs/${encodeURIComponent(sourceId)}/tail`, { limit }),
      {},
      ADMIN_REQUEST_OPTIONS
    ),
  getFailures: () =>
    apiRequestJson<SystemFailureListResponse>('/api/system/failures', {}, ADMIN_REQUEST_OPTIONS),
  getRuntimeTools: () =>
    apiRequestJson<SystemRuntimeToolListResponse>(
      '/api/system/runtime-tools',
      {},
      ADMIN_REQUEST_OPTIONS
    ),
  getHardware: () =>
    apiRequestJson<SystemHardwareResponse>('/api/system/hardware', {}, ADMIN_REQUEST_OPTIONS),
  getCharts: () =>
    apiRequestJson<SystemChartCatalogResponse>('/api/system/charts', {}, ADMIN_REQUEST_OPTIONS),
  getChart: (chartId: string, query?: { window?: string; since?: string; until?: string }) =>
    apiRequestJson<SystemChartResponse>(
      withQuery(`/api/system/charts/${encodeURIComponent(chartId)}`, query),
      {},
      ADMIN_REQUEST_OPTIONS
    ),
  getStatsSummary: () =>
    apiRequestJson<SystemStatsSummaryResponse>(
      '/api/system/stats/summary',
      {},
      ADMIN_REQUEST_OPTIONS
    ),
  search: (query: string, options?: { limit?: number; scope?: string }) =>
    apiRequestJson<SystemSearchResponse>(
      withQuery('/api/system/search', {
        q: query,
        limit: options?.limit,
        scope: options?.scope,
      }),
      {},
      ADMIN_REQUEST_OPTIONS
    ),
}
