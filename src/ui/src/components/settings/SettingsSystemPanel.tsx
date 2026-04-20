import { Loader2, RefreshCw, Search } from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { adminApi } from '@/lib/api/admin'
import { cn } from '@/lib/utils'
import type {
  AdminJsonObject,
  AdminJsonValue,
  SystemChartCatalogItem,
  SystemChartCatalogResponse,
  SystemChartResponse,
  SystemFailureItem,
  SystemFailureListResponse,
  SystemHardwareResponse,
  SystemLogSource,
  SystemLogSourceListResponse,
  SystemLogTailResponse,
  SystemOverviewResponse,
  SystemQuestItem,
  SystemQuestListResponse,
  SystemQuestSummaryResponse,
  SystemRuntimeSession,
  SystemRuntimeSessionListResponse,
  SystemRuntimeTool,
  SystemRuntimeToolListResponse,
  SystemSearchResponse,
  SystemSearchResultItem,
  SystemStatsSummaryResponse,
} from '@/lib/types/admin'
import type { Locale } from '@/types'

type ResourceState<T> = {
  data: T | null
  loading: boolean
  error: string
}

export type SettingsSystemPanelViewProps = {
  locale: Locale
  refreshing: boolean
  overview: ResourceState<SystemOverviewResponse>
  quests: ResourceState<SystemQuestListResponse>
  questSummary: ResourceState<SystemQuestSummaryResponse>
  runtimeSessions: ResourceState<SystemRuntimeSessionListResponse>
  logSources: ResourceState<SystemLogSourceListResponse>
  logTail: ResourceState<SystemLogTailResponse>
  failures: ResourceState<SystemFailureListResponse>
  runtimeTools: ResourceState<SystemRuntimeToolListResponse>
  hardware: ResourceState<SystemHardwareResponse>
  charts: ResourceState<SystemChartCatalogResponse>
  chartDetail: ResourceState<SystemChartResponse>
  statsSummary: ResourceState<SystemStatsSummaryResponse>
  searchResults: ResourceState<SystemSearchResponse>
  selectedQuestId: string
  selectedLogSourceId: string
  selectedChartId: string
  chartWindow: string
  searchQuery: string
  onRefresh: () => void
  onSelectQuest: (questId: string) => void
  onSelectLogSource: (sourceId: string) => void
  onSelectChart: (chartId: string) => void
  onChartWindowChange: (value: string) => void
  onSearchQueryChange: (value: string) => void
  onSearch: () => void
}

const copy = {
  en: {
    title: 'System visibility',
    hint: 'Read-only operator visibility powered by /api/system/*.',
    refresh: 'Refresh all',
    overview: 'System overview',
    quests: 'Quests',
    questSummary: 'Quest summary',
    runtimeSessions: 'Runtime sessions',
    logSources: 'Log sources',
    logTail: 'Log tail',
    failures: 'Failures',
    runtimeTools: 'Runtime tools',
    hardware: 'Hardware',
    charts: 'Chart catalog',
    chartQuery: 'Chart query',
    statsSummary: 'Stats summary',
    search: 'Search',
    empty: 'No data available.',
    searchPlaceholder: 'Search system state',
    searchAction: 'Search system',
    searchInput: 'System search input',
    chartWindow: 'Chart window',
    endpoint: '/api/system/*',
    questPicker: 'Quest picker',
    logPicker: 'Log source picker',
    chartPicker: 'Chart picker',
    id: 'ID',
    titleLabel: 'Title',
    status: 'Status',
    state: 'State',
    severity: 'Severity',
    summary: 'Summary',
    value: 'Value',
    tailLines: 'Tail lines',
    raw: 'Raw payload',
  },
  zh: {
    title: '系统可见性',
    hint: '只读 operator 可见性，优先走 /api/system/*。',
    refresh: '刷新全部',
    overview: '系统总览',
    quests: 'Quest 列表',
    questSummary: 'Quest 摘要',
    runtimeSessions: '运行态会话',
    logSources: '日志源',
    logTail: '日志尾部',
    failures: '故障列表',
    runtimeTools: '运行态工具',
    hardware: '硬件',
    charts: '图表目录',
    chartQuery: '图表查询',
    statsSummary: '统计摘要',
    search: '搜索',
    empty: '暂无数据。',
    searchPlaceholder: '搜索系统状态',
    searchAction: '搜索系统',
    searchInput: '系统搜索输入',
    chartWindow: '图表时间窗',
    endpoint: '/api/system/*',
    questPicker: 'Quest 选择',
    logPicker: '日志源选择',
    chartPicker: '图表选择',
    id: '标识',
    titleLabel: '标题',
    status: '状态',
    state: '运行态',
    severity: '级别',
    summary: '摘要',
    value: '值',
    tailLines: '尾部日志',
    raw: '原始载荷',
  },
} satisfies Record<Locale, Record<string, string>>

function createEmptyState<T>(): ResourceState<T> {
  return { data: null, loading: false, error: '' }
}

function formatError(error: unknown) {
  return error instanceof Error ? error.message : String(error || 'Unknown error')
}

function isRecord(value: unknown): value is AdminJsonObject {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function isScalar(value: AdminJsonValue | undefined): value is string | number | boolean | null {
  return value === null || ['string', 'number', 'boolean'].includes(typeof value)
}

function getItems<T extends AdminJsonObject>(payload: { items?: T[] } | T[] | null | undefined) {
  if (Array.isArray(payload)) {
    return payload
  }
  return Array.isArray(payload?.items) ? payload.items : []
}

function getRecordItems<T extends AdminJsonObject>(payload: AdminJsonObject | null | undefined, key: string) {
  const value = payload?.[key]
  return Array.isArray(value) ? (value as T[]) : []
}

function stringifyValue(value: AdminJsonValue | undefined) {
  if (value === null) return 'null'
  if (value === undefined) return '—'
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  if (typeof value === 'string') return value || '—'
  if (typeof value === 'number') return String(value)
  if (Array.isArray(value)) {
    return value.length ? `${value.length} items` : '[]'
  }
  return '{…}'
}

function formatTimestamp(value: string | null | undefined) {
  const normalized = String(value || '').trim()
  if (!normalized) return '—'
  const parsed = new Date(normalized)
  if (Number.isNaN(parsed.getTime())) return normalized
  return parsed.toLocaleString()
}

function scalarEntries(payload: AdminJsonObject | null | undefined) {
  return Object.entries(payload || {}).filter(([, value]) => isScalar(value))
}

function nonScalarEntries(payload: AdminJsonObject | null | undefined) {
  return Object.entries(payload || {}).filter(([, value]) => !isScalar(value))
}

function statusVariant(value: unknown) {
  const normalized = String(value || '').trim().toLowerCase()
  if (!normalized) return 'secondary' as const
  if (['ok', 'healthy', 'ready', 'running', 'success', 'active'].includes(normalized)) return 'success' as const
  if (['warning', 'degraded', 'stale'].includes(normalized)) return 'warning' as const
  if (['error', 'failed', 'fatal'].includes(normalized)) return 'destructive' as const
  return 'secondary' as const
}

function SectionCard({
  title,
  subtitle,
  badge,
  actions,
  children,
}: {
  title: string
  subtitle?: string
  badge?: string | number | null
  actions?: ReactNode
  children: ReactNode
}) {
  return (
    <section className="rounded-[28px] border border-black/[0.08] bg-white/[0.5] p-5 shadow-[0_20px_70px_-50px_rgba(15,23,42,0.45)] dark:border-white/[0.08] dark:bg-white/[0.03] sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
          {subtitle ? <div className="mt-2 text-sm text-muted-foreground">{subtitle}</div> : null}
        </div>
        <div className="flex items-center gap-2">
          {badge !== null && badge !== undefined ? <Badge variant="secondary">{badge}</Badge> : null}
          {actions}
        </div>
      </div>
      <div className="mt-5">{children}</div>
    </section>
  )
}

function SectionBody({
  state,
  empty,
  children,
}: {
  state: ResourceState<unknown>
  empty: string
  children: ReactNode
}) {
  if (state.loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading...
      </div>
    )
  }
  if (state.error) {
    return <div className="rounded-[18px] border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">{state.error}</div>
  }
  return <>{children || <div className="text-sm text-muted-foreground">{empty}</div>}</>
}

function ScalarGrid({ payload, empty }: { payload: AdminJsonObject | null | undefined; empty: string }) {
  const entries = scalarEntries(payload)
  if (!entries.length) {
    return <div className="text-sm text-muted-foreground">{empty}</div>
  }
  return (
    <dl className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {entries.map(([key, value]) => (
        <div key={key} className="rounded-[18px] border border-black/[0.06] bg-white/[0.65] px-4 py-3 dark:border-white/[0.08] dark:bg-white/[0.04]">
          <dt className="text-xs uppercase tracking-[0.14em] text-muted-foreground">{key.replace(/_/g, ' ')}</dt>
          <dd className="mt-2 break-words text-sm font-medium text-foreground">
            {key.endsWith('_at') ? formatTimestamp(typeof value === 'string' ? value : null) : stringifyValue(value)}
          </dd>
        </div>
      ))}
    </dl>
  )
}

function RawPayload({ payload, title }: { payload: AdminJsonObject | null | undefined; title: string }) {
  const entries = nonScalarEntries(payload)
  if (!entries.length) {
    return null
  }
  return (
    <details className="mt-4 rounded-[18px] border border-black/[0.06] bg-white/[0.4] p-4 dark:border-white/[0.08] dark:bg-white/[0.02]">
      <summary className="cursor-pointer text-sm font-medium text-foreground">{title}</summary>
      <pre className="mt-3 overflow-x-auto whitespace-pre-wrap break-words text-xs leading-6 text-muted-foreground">
        {JSON.stringify(Object.fromEntries(entries), null, 2)}
      </pre>
    </details>
  )
}

export function SettingsSystemPanelView({
  locale,
  refreshing,
  overview,
  quests,
  questSummary,
  runtimeSessions,
  logSources,
  logTail,
  failures,
  runtimeTools,
  hardware,
  charts,
  chartDetail,
  statsSummary,
  searchResults,
  selectedQuestId,
  selectedLogSourceId,
  selectedChartId,
  chartWindow,
  searchQuery,
  onRefresh,
  onSelectQuest,
  onSelectLogSource,
  onSelectChart,
  onChartWindowChange,
  onSearchQueryChange,
  onSearch,
}: SettingsSystemPanelViewProps) {
  const t = copy[locale]
  const questItems = getItems<SystemQuestItem>(quests.data)
  const runtimeSessionRecord = isRecord(runtimeSessions.data) ? runtimeSessions.data : null
  const sessionItems: SystemRuntimeSession[] = [
    ...getRecordItems<SystemRuntimeSession>(runtimeSessionRecord, 'quest_sessions').map((item) => ({
      ...item,
      session_id: String(item.active_run_id || item.quest_id || '').trim() || undefined,
      state: String(item.status || item.runtime_status || item.worker_running || '').trim() || 'unknown',
      source_kind: 'quest',
    })),
    ...getRecordItems<SystemRuntimeSession>(runtimeSessionRecord, 'connector_sessions').map((item) => ({
      ...item,
      session_id:
        (Array.isArray(item.bound_sources) ? item.bound_sources.map((value) => String(value)).join(', ') : '') ||
        String(item.quest_id || '').trim() ||
        undefined,
      state: String(item.status || 'bound').trim() || 'bound',
      source_kind: 'connector',
    })),
    ...getRecordItems<SystemRuntimeSession>(runtimeSessionRecord, 'bash_sessions').map((item) => ({
      ...item,
      session_id: String(item.bash_id || item.session_id || '').trim() || undefined,
      state: String(item.status || '').trim() || 'unknown',
      source_kind: 'bash',
    })),
  ]
  const logSourceItems = getItems<SystemLogSource>(logSources.data)
  const failureItems = getItems<SystemFailureItem>(failures.data)
  const runtimeToolItems = getItems<SystemRuntimeTool>(runtimeTools.data)
  const chartItems = getItems<SystemChartCatalogItem>(charts.data)
  const searchItems = getItems<SystemSearchResultItem>(searchResults.data)
  const summaryRecord = isRecord(questSummary.data) ? questSummary.data : null
  const summaryQuestRecord = isRecord(summaryRecord?.quest as AdminJsonValue) ? (summaryRecord?.quest as AdminJsonObject) : summaryRecord
  const chartRecord = isRecord(chartDetail.data) ? chartDetail.data : null
  const tailLines = Array.isArray(logTail.data?.lines) ? logTail.data.lines : []

  return (
    <div className="grid gap-6 pt-6">
      <SectionCard
        title={t.title}
        subtitle={t.hint}
        badge={t.endpoint}
        actions={
          <Button variant="outline" size="sm" onClick={onRefresh} isLoading={refreshing}>
            <RefreshCw className="mr-2 h-3.5 w-3.5" />
            {t.refresh}
          </Button>
        }
      >
        <div className="grid gap-6 xl:grid-cols-2">
          <SectionCard title={t.overview}>
            <SectionBody state={overview} empty={t.empty}>
              <ScalarGrid payload={overview.data} empty={t.empty} />
              <RawPayload payload={overview.data} title={t.raw} />
            </SectionBody>
          </SectionCard>

          <SectionCard title={t.statsSummary}>
            <SectionBody state={statsSummary} empty={t.empty}>
              <ScalarGrid payload={statsSummary.data} empty={t.empty} />
              <RawPayload payload={statsSummary.data} title={t.raw} />
            </SectionBody>
          </SectionCard>
        </div>
      </SectionCard>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
        <SectionCard title={t.quests} badge={questItems.length}>
          <SectionBody state={quests} empty={t.empty}>
            {questItems.length ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t.id}</TableHead>
                    <TableHead>{t.titleLabel}</TableHead>
                    <TableHead>{t.status}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {questItems.map((item) => {
                    const questId = String(item.quest_id || '').trim()
                    return (
                      <TableRow
                        key={questId || JSON.stringify(item)}
                        className={cn(selectedQuestId === questId && 'bg-soft-bg-elevated/60')}
                        onClick={() => questId && onSelectQuest(questId)}
                      >
                        <TableCell className="font-medium">{questId || '—'}</TableCell>
                        <TableCell>{String(item.title || '—')}</TableCell>
                        <TableCell>
                          <Badge variant={statusVariant(item.runtime_status || item.status)}>
                            {String(item.runtime_status || item.status || 'unknown')}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            ) : (
              <div className="text-sm text-muted-foreground">{t.empty}</div>
            )}
          </SectionBody>
        </SectionCard>

        <SectionCard title={t.questSummary}>
          <div className="mb-4">
            <label className="mb-2 block text-xs uppercase tracking-[0.14em] text-muted-foreground" htmlFor="system-quest-picker">
              {t.questPicker}
            </label>
            <select
              id="system-quest-picker"
              className="h-10 w-full rounded-[16px] border border-black/[0.08] bg-white/[0.7] px-3 text-sm dark:border-white/[0.1] dark:bg-white/[0.04]"
              value={selectedQuestId}
              onChange={(event) => onSelectQuest(event.target.value)}
            >
              <option value="">{t.empty}</option>
              {questItems.map((item) => {
                const questId = String(item.quest_id || '').trim()
                return (
                  <option key={questId || JSON.stringify(item)} value={questId}>
                    {questId || String(item.title || '—')}
                  </option>
                )
              })}
            </select>
          </div>
          <SectionBody state={questSummary} empty={t.empty}>
            {typeof summaryRecord?.summary === 'string' ? (
              <div className="rounded-[18px] border border-black/[0.06] bg-white/[0.65] px-4 py-3 text-sm leading-7 dark:border-white/[0.08] dark:bg-white/[0.04]">
                {summaryRecord.summary}
              </div>
            ) : null}
            <ScalarGrid payload={summaryQuestRecord} empty={t.empty} />
            <RawPayload payload={summaryRecord} title={t.raw} />
          </SectionBody>
        </SectionCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <SectionCard title={t.runtimeSessions} badge={sessionItems.length}>
          <SectionBody state={runtimeSessions} empty={t.empty}>
            {sessionItems.length ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t.id}</TableHead>
                    <TableHead>Quest</TableHead>
                    <TableHead>{t.state}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sessionItems.map((item) => (
                    <TableRow key={String(item.session_id || JSON.stringify(item))}>
                      <TableCell className="font-medium">{String(item.session_id || '—')}</TableCell>
                      <TableCell>{String(item.quest_id || '—')}</TableCell>
                      <TableCell>
                        <Badge variant={statusVariant(item.state)}>{String(item.state || 'unknown')}</Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-sm text-muted-foreground">{t.empty}</div>
            )}
          </SectionBody>
        </SectionCard>

        <SectionCard title={t.hardware}>
          <SectionBody state={hardware} empty={t.empty}>
            <ScalarGrid payload={hardware.data} empty={t.empty} />
            <RawPayload payload={hardware.data} title={t.raw} />
          </SectionBody>
        </SectionCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <SectionCard title={t.logSources} badge={logSourceItems.length}>
          <div className="mb-4">
            <label className="mb-2 block text-xs uppercase tracking-[0.14em] text-muted-foreground" htmlFor="system-log-picker">
              {t.logPicker}
            </label>
            <select
              id="system-log-picker"
              className="h-10 w-full rounded-[16px] border border-black/[0.08] bg-white/[0.7] px-3 text-sm dark:border-white/[0.1] dark:bg-white/[0.04]"
              value={selectedLogSourceId}
              onChange={(event) => onSelectLogSource(event.target.value)}
            >
              <option value="">{t.empty}</option>
              {logSourceItems.map((item) => {
                const sourceId = String(item.source_id || '').trim()
                return (
                  <option key={sourceId || JSON.stringify(item)} value={sourceId}>
                    {String(item.label || sourceId || '—')}
                  </option>
                )
              })}
            </select>
          </div>
          <SectionBody state={logSources} empty={t.empty}>
            {logSourceItems.length ? (
              <div className="space-y-2">
                {logSourceItems.map((item) => {
                  const sourceId = String(item.source_id || '').trim()
                  return (
                    <div key={sourceId || JSON.stringify(item)} className="rounded-[16px] border border-black/[0.06] bg-white/[0.65] px-4 py-3 dark:border-white/[0.08] dark:bg-white/[0.04]">
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <div className="font-medium text-foreground">{String(item.label || sourceId || '—')}</div>
                          <div className="mt-1 break-all text-xs text-muted-foreground">{sourceId || '—'}</div>
                        </div>
                        {item.source_type || item.kind ? (
                          <Badge variant="secondary">{String(item.source_type || item.kind)}</Badge>
                        ) : null}
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="text-sm text-muted-foreground">{t.empty}</div>
            )}
          </SectionBody>
        </SectionCard>

        <SectionCard title={t.logTail} subtitle={t.tailLines}>
          <SectionBody state={logTail} empty={t.empty}>
            <div className="rounded-[18px] border border-black/[0.06] bg-[#111827] px-4 py-4 text-xs leading-6 text-slate-100 dark:border-white/[0.08]">
              <pre className="overflow-x-auto whitespace-pre-wrap break-words">{tailLines.length ? tailLines.join('\n') : t.empty}</pre>
            </div>
            <RawPayload payload={logTail.data} title={t.raw} />
          </SectionBody>
        </SectionCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <SectionCard title={t.failures} badge={failureItems.length}>
          <SectionBody state={failures} empty={t.empty}>
            {failureItems.length ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t.id}</TableHead>
                    <TableHead>{t.severity}</TableHead>
                    <TableHead>{t.summary}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {failureItems.map((item) => (
                    <TableRow key={String(item.id || item.failure_id || JSON.stringify(item))}>
                      <TableCell className="font-medium">{String(item.id || item.failure_id || '—')}</TableCell>
                      <TableCell>
                        <Badge variant={statusVariant(item.severity || item.status)}>
                          {String(item.severity || item.status || 'unknown')}
                        </Badge>
                      </TableCell>
                      <TableCell>{String(item.summary || '—')}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-sm text-muted-foreground">{t.empty}</div>
            )}
          </SectionBody>
        </SectionCard>

        <SectionCard title={t.runtimeTools} badge={runtimeToolItems.length}>
          <SectionBody state={runtimeTools} empty={t.empty}>
            {runtimeToolItems.length ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t.titleLabel}</TableHead>
                    <TableHead>{t.status}</TableHead>
                    <TableHead>{t.summary}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {runtimeToolItems.map((item) => (
                    <TableRow key={String(item.tool_name || JSON.stringify(item))}>
                      <TableCell className="font-medium">{String(item.tool_name || '—')}</TableCell>
                      <TableCell>
                        <Badge variant={statusVariant(item.status || (item.available ? 'available' : 'missing'))}>
                          {String(item.status || (item.available ? 'available' : 'missing'))}
                        </Badge>
                      </TableCell>
                      <TableCell>{String(item.summary || '—')}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-sm text-muted-foreground">{t.empty}</div>
            )}
          </SectionBody>
        </SectionCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <SectionCard title={t.charts} badge={chartItems.length}>
          <div className="mb-4 grid gap-3 md:grid-cols-[minmax(0,1fr)_180px]">
            <div>
              <label className="mb-2 block text-xs uppercase tracking-[0.14em] text-muted-foreground" htmlFor="system-chart-picker">
                {t.chartPicker}
              </label>
              <select
                id="system-chart-picker"
                className="h-10 w-full rounded-[16px] border border-black/[0.08] bg-white/[0.7] px-3 text-sm dark:border-white/[0.1] dark:bg-white/[0.04]"
                value={selectedChartId}
                onChange={(event) => onSelectChart(event.target.value)}
              >
                <option value="">{t.empty}</option>
                {chartItems.map((item) => {
                  const chartId = String(item.chart_id || '').trim()
                  return (
                    <option key={chartId || JSON.stringify(item)} value={chartId}>
                      {String(item.title || chartId || '—')}
                    </option>
                  )
                })}
              </select>
            </div>
            <div>
              <label className="mb-2 block text-xs uppercase tracking-[0.14em] text-muted-foreground" htmlFor="system-chart-window">
                {t.chartWindow}
              </label>
              <Input id="system-chart-window" value={chartWindow} onChange={(event) => onChartWindowChange(event.target.value)} />
            </div>
          </div>
          <SectionBody state={charts} empty={t.empty}>
            {chartItems.length ? (
              <div className="space-y-2">
                {chartItems.map((item) => (
                  <div key={String(item.chart_id || JSON.stringify(item))} className="rounded-[16px] border border-black/[0.06] bg-white/[0.65] px-4 py-3 dark:border-white/[0.08] dark:bg-white/[0.04]">
                    <div className="font-medium text-foreground">{String(item.title || item.chart_id || '—')}</div>
                    {item.description ? <div className="mt-1 text-sm text-muted-foreground">{String(item.description)}</div> : null}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-muted-foreground">{t.empty}</div>
            )}
          </SectionBody>
        </SectionCard>

        <SectionCard title={t.chartQuery}>
          <SectionBody state={chartDetail} empty={t.empty}>
            <ScalarGrid payload={chartRecord} empty={t.empty} />
            <RawPayload payload={chartRecord} title={t.raw} />
          </SectionBody>
        </SectionCard>
      </div>

      <SectionCard title={t.search}>
        <div className="flex flex-col gap-3 md:flex-row">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              aria-label={t.searchInput}
              value={searchQuery}
              onChange={(event) => onSearchQueryChange(event.target.value)}
              placeholder={t.searchPlaceholder}
              className="pl-10"
            />
          </div>
          <Button onClick={onSearch}>{t.searchAction}</Button>
        </div>
        <div className="mt-5">
          <SectionBody state={searchResults} empty={t.empty}>
            {searchItems.length ? (
              <div className="space-y-3">
                {searchItems.map((item) => (
                  <article key={String(item.result_id || JSON.stringify(item))} className="rounded-[18px] border border-black/[0.06] bg-white/[0.65] px-4 py-4 dark:border-white/[0.08] dark:bg-white/[0.04]">
                    <div className="flex items-center justify-between gap-3">
                      <div className="font-medium text-foreground">{String(item.title || item.label || item.result_id || '—')}</div>
                      {item.kind || item.result_type ? (
                        <Badge variant="secondary">{String(item.kind || item.result_type)}</Badge>
                      ) : null}
                    </div>
                    {item.snippet || item.description ? (
                      <div className="mt-2 text-sm text-muted-foreground">{String(item.snippet || item.description)}</div>
                    ) : null}
                  </article>
                ))}
              </div>
            ) : (
              <div className="text-sm text-muted-foreground">{t.empty}</div>
            )}
          </SectionBody>
        </div>
      </SectionCard>
    </div>
  )
}

export function SettingsSystemPanel({ locale }: { locale: Locale }) {
  const [refreshNonce, setRefreshNonce] = useState(0)
  const [refreshing, setRefreshing] = useState(false)
  const [overview, setOverview] = useState<ResourceState<SystemOverviewResponse>>(createEmptyState())
  const [quests, setQuests] = useState<ResourceState<SystemQuestListResponse>>(createEmptyState())
  const [questSummary, setQuestSummary] = useState<ResourceState<SystemQuestSummaryResponse>>(createEmptyState())
  const [runtimeSessions, setRuntimeSessions] = useState<ResourceState<SystemRuntimeSessionListResponse>>(createEmptyState())
  const [logSources, setLogSources] = useState<ResourceState<SystemLogSourceListResponse>>(createEmptyState())
  const [logTail, setLogTail] = useState<ResourceState<SystemLogTailResponse>>(createEmptyState())
  const [failures, setFailures] = useState<ResourceState<SystemFailureListResponse>>(createEmptyState())
  const [runtimeTools, setRuntimeTools] = useState<ResourceState<SystemRuntimeToolListResponse>>(createEmptyState())
  const [hardware, setHardware] = useState<ResourceState<SystemHardwareResponse>>(createEmptyState())
  const [charts, setCharts] = useState<ResourceState<SystemChartCatalogResponse>>(createEmptyState())
  const [chartDetail, setChartDetail] = useState<ResourceState<SystemChartResponse>>(createEmptyState())
  const [statsSummary, setStatsSummary] = useState<ResourceState<SystemStatsSummaryResponse>>(createEmptyState())
  const [searchResults, setSearchResults] = useState<ResourceState<SystemSearchResponse>>(createEmptyState())
  const [selectedQuestId, setSelectedQuestId] = useState('')
  const [selectedLogSourceId, setSelectedLogSourceId] = useState('')
  const [selectedChartId, setSelectedChartId] = useState('')
  const [chartWindow, setChartWindow] = useState('1h')
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setRefreshing(true)
      setOverview((current) => ({ ...current, loading: true, error: '' }))
      setQuests((current) => ({ ...current, loading: true, error: '' }))
      setRuntimeSessions((current) => ({ ...current, loading: true, error: '' }))
      setLogSources((current) => ({ ...current, loading: true, error: '' }))
      setFailures((current) => ({ ...current, loading: true, error: '' }))
      setRuntimeTools((current) => ({ ...current, loading: true, error: '' }))
      setHardware((current) => ({ ...current, loading: true, error: '' }))
      setCharts((current) => ({ ...current, loading: true, error: '' }))
      setStatsSummary((current) => ({ ...current, loading: true, error: '' }))

      const results = await Promise.allSettled([
        adminApi.getOverview(),
        adminApi.getQuests(),
        adminApi.getRuntimeSessions(),
        adminApi.getLogSources(),
        adminApi.getFailures(),
        adminApi.getRuntimeTools(),
        adminApi.getHardware(),
        adminApi.getCharts(),
        adminApi.getStatsSummary(),
      ])

      if (cancelled) {
        return
      }

      const [
        overviewResult,
        questsResult,
        runtimeSessionsResult,
        logSourcesResult,
        failuresResult,
        runtimeToolsResult,
        hardwareResult,
        chartsResult,
        statsSummaryResult,
      ] = results

      if (overviewResult.status === 'fulfilled') {
        setOverview({ data: overviewResult.value, loading: false, error: '' })
      } else {
        setOverview({ data: null, loading: false, error: formatError(overviewResult.reason) })
      }

      if (questsResult.status === 'fulfilled') {
        const next = questsResult.value
        const items = getItems<SystemQuestItem>(next)
        setQuests({ data: next, loading: false, error: '' })
        setSelectedQuestId((current) => current || String(items[0]?.quest_id || '').trim())
      } else {
        setQuests({ data: null, loading: false, error: formatError(questsResult.reason) })
      }

      if (runtimeSessionsResult.status === 'fulfilled') {
        setRuntimeSessions({ data: runtimeSessionsResult.value, loading: false, error: '' })
      } else {
        setRuntimeSessions({ data: null, loading: false, error: formatError(runtimeSessionsResult.reason) })
      }

      if (logSourcesResult.status === 'fulfilled') {
        const next = logSourcesResult.value
        const items = getItems<SystemLogSource>(next)
        setLogSources({ data: next, loading: false, error: '' })
        setSelectedLogSourceId((current) => current || String(items[0]?.source_id || '').trim())
      } else {
        setLogSources({ data: null, loading: false, error: formatError(logSourcesResult.reason) })
      }

      if (failuresResult.status === 'fulfilled') {
        setFailures({ data: failuresResult.value, loading: false, error: '' })
      } else {
        setFailures({ data: null, loading: false, error: formatError(failuresResult.reason) })
      }

      if (runtimeToolsResult.status === 'fulfilled') {
        setRuntimeTools({ data: runtimeToolsResult.value, loading: false, error: '' })
      } else {
        setRuntimeTools({ data: null, loading: false, error: formatError(runtimeToolsResult.reason) })
      }

      if (hardwareResult.status === 'fulfilled') {
        setHardware({ data: hardwareResult.value, loading: false, error: '' })
      } else {
        setHardware({ data: null, loading: false, error: formatError(hardwareResult.reason) })
      }

      if (chartsResult.status === 'fulfilled') {
        const next = chartsResult.value
        const items = getItems<SystemChartCatalogItem>(next)
        setCharts({ data: next, loading: false, error: '' })
        setSelectedChartId((current) => current || String(items[0]?.chart_id || '').trim())
      } else {
        setCharts({ data: null, loading: false, error: formatError(chartsResult.reason) })
      }

      if (statsSummaryResult.status === 'fulfilled') {
        setStatsSummary({ data: statsSummaryResult.value, loading: false, error: '' })
      } else {
        setStatsSummary({ data: null, loading: false, error: formatError(statsSummaryResult.reason) })
      }

      setRefreshing(false)
    }

    void load()
    return () => {
      cancelled = true
    }
  }, [refreshNonce])

  useEffect(() => {
    if (!selectedQuestId) {
      setQuestSummary(createEmptyState())
      return
    }
    let cancelled = false
    setQuestSummary((current) => ({ ...current, loading: true, error: '' }))
    const load = async () => {
      try {
        const next = await adminApi.getQuestSummary(selectedQuestId)
        if (!cancelled) {
          setQuestSummary({ data: next, loading: false, error: '' })
        }
      } catch (error) {
        if (!cancelled) {
          setQuestSummary({ data: null, loading: false, error: formatError(error) })
        }
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [selectedQuestId])

  useEffect(() => {
    if (!selectedLogSourceId) {
      setLogTail(createEmptyState())
      return
    }
    let cancelled = false
    setLogTail((current) => ({ ...current, loading: true, error: '' }))
    const load = async () => {
      try {
        const next = await adminApi.getLogTail(selectedLogSourceId, 200)
        if (!cancelled) {
          setLogTail({ data: next, loading: false, error: '' })
        }
      } catch (error) {
        if (!cancelled) {
          setLogTail({ data: null, loading: false, error: formatError(error) })
        }
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [selectedLogSourceId])

  useEffect(() => {
    if (!selectedChartId) {
      setChartDetail(createEmptyState())
      return
    }
    let cancelled = false
    setChartDetail((current) => ({ ...current, loading: true, error: '' }))
    const load = async () => {
      try {
        const next = await adminApi.getChart(selectedChartId, { window: chartWindow })
        if (!cancelled) {
          setChartDetail({ data: next, loading: false, error: '' })
        }
      } catch (error) {
        if (!cancelled) {
          setChartDetail({ data: null, loading: false, error: formatError(error) })
        }
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [chartWindow, selectedChartId])

  const refreshAll = () => {
    setRefreshNonce((value) => value + 1)
  }

  const runSearch = async () => {
    const normalized = searchQuery.trim()
    if (!normalized) {
      setSearchResults(createEmptyState())
      return
    }
    setSearchResults((current) => ({ ...current, loading: true, error: '' }))
    try {
      const next = await adminApi.search(normalized, { limit: 20 })
      setSearchResults({ data: next, loading: false, error: '' })
    } catch (error) {
      setSearchResults({ data: null, loading: false, error: formatError(error) })
    }
  }

  return (
    <SettingsSystemPanelView
      locale={locale}
      refreshing={refreshing}
      overview={overview}
      quests={quests}
      questSummary={questSummary}
      runtimeSessions={runtimeSessions}
      logSources={logSources}
      logTail={logTail}
      failures={failures}
      runtimeTools={runtimeTools}
      hardware={hardware}
      charts={charts}
      chartDetail={chartDetail}
      statsSummary={statsSummary}
      searchResults={searchResults}
      selectedQuestId={selectedQuestId}
      selectedLogSourceId={selectedLogSourceId}
      selectedChartId={selectedChartId}
      chartWindow={chartWindow}
      searchQuery={searchQuery}
      onRefresh={refreshAll}
      onSelectQuest={setSelectedQuestId}
      onSelectLogSource={setSelectedLogSourceId}
      onSelectChart={setSelectedChartId}
      onChartWindowChange={setChartWindow}
      onSearchQueryChange={setSearchQuery}
      onSearch={() => void runSearch()}
    />
  )
}
