'use client'

import * as React from 'react'
import {
  AlertCircle,
  BrainCircuit,
  CheckCircle2,
  ChevronDown,
  Database,
  GitBranch,
  Globe2,
  Loader2,
  Search,
  Square,
  TerminalSquare,
  Wrench,
} from 'lucide-react'

import { WebSearchQueryPills, WebSearchResults } from '@/components/chat/toolViews/WebSearchCards'
import { deriveMcpIdentity } from '@/lib/mcpIdentity'
import type { RenderOperationFeedItem } from '@/lib/feedOperations'
import { cn } from '@/lib/utils'
import {
  asRecord,
  asString,
  asStringArray,
  extractPathEntries,
  truncateText,
} from '@/components/chat/toolViews/mcp-view-utils'
import {
  normalizeWebSearchPayload,
  type NormalizedWebSearchPayload,
} from '@/components/chat/toolViews/web-search-view-utils'

function formatTime(value?: string) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function parseStructuredValue(value?: string) {
  if (!value) return null
  try {
    return JSON.parse(value) as Record<string, unknown>
  } catch {
    return null
  }
}

function unwrapToolResult(value: unknown): unknown {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return value
  const record = value as Record<string, unknown>
  if (record.structured_content && record.structured_content !== value) {
    return unwrapToolResult(record.structured_content)
  }
  if (record.structured_result && record.structured_result !== value) {
    return unwrapToolResult(record.structured_result)
  }
  if (record.result && record.result !== value) {
    return unwrapToolResult(record.result)
  }
  return value
}

function normalizeStatus(value?: string, active = false) {
  const raw = String(value || '').trim().toLowerCase()
  if (
    raw === 'failed' ||
    raw === 'error' ||
    raw === 'terminated' ||
    raw === 'cancelled'
  ) {
    return {
      label: raw || 'failed',
      Icon: AlertCircle,
      chipClassName:
        'border-rose-500/18 bg-rose-500/10 text-rose-700 dark:border-rose-300/18 dark:bg-rose-300/10 dark:text-rose-200',
      spinning: false,
    }
  }
  if (
    active ||
    raw === 'calling' ||
    raw === 'running' ||
    raw === 'pending' ||
    raw === 'queued' ||
    raw === 'starting'
  ) {
    return {
      label: raw || 'running',
      Icon: Loader2,
      chipClassName:
        'border-black/[0.08] bg-black/[0.04] text-foreground dark:border-white/[0.10] dark:bg-white/[0.06]',
      spinning: true,
    }
  }
  if (raw === 'stopped') {
    return {
      label: raw,
      Icon: Square,
      chipClassName:
        'border-amber-500/18 bg-amber-500/10 text-amber-700 dark:border-amber-300/18 dark:bg-amber-300/10 dark:text-amber-200',
      spinning: false,
    }
  }
  return {
    label: raw || 'completed',
    Icon: CheckCircle2,
    chipClassName:
      'border-emerald-500/18 bg-emerald-500/10 text-emerald-700 dark:border-emerald-300/18 dark:bg-emerald-300/10 dark:text-emerald-200',
    spinning: false,
  }
}

type StudioToolCardModel = {
  label: string
  tooltip: string
  title: string
  subtitle?: string | null
  Icon: React.ComponentType<{ className?: string }>
  accentClassName: string
  statusLabel: string
  statusChipClassName: string
  statusIcon: React.ComponentType<{ className?: string }>
  statusSpinning: boolean
  badges: string[]
  lines: string[]
  paths: Array<{ label: string; path: string }>
  rawArgs?: string
  rawOutput?: string
  webSearch?: NormalizedWebSearchPayload | null
}

function extractArtifactRecord(resultRecord: Record<string, unknown> | null) {
  const direct = asRecord(resultRecord?.record)
  if (direct) return direct
  const artifact = asRecord(resultRecord?.artifact)
  return asRecord(artifact?.record) ?? artifact
}

function summarizeMetricEntries(value: unknown) {
  const record = asRecord(value)
  if (!record) return []
  return Object.entries(record)
    .filter(([, metricValue]) => metricValue != null && metricValue !== '')
    .slice(0, 4)
    .map(([metricKey, metricValue]) => `${metricKey}: ${String(metricValue)}`)
}

function buildArtifactModel(item: RenderOperationFeedItem): StudioToolCardModel {
  const active = item.label === 'tool_call'
  const tool = item.mcpTool || deriveMcpIdentity(item.toolName, item.mcpServer, item.mcpTool).tool || 'artifact'
  const args = parseStructuredValue(item.args)
  const resultRecord = asRecord(unwrapToolResult(parseStructuredValue(item.output)))
  const artifactRecord = extractArtifactRecord(resultRecord)
  const titleMap: Record<string, string> = {
    record: active ? 'Recording artifact' : 'Recorded artifact',
    checkpoint: active ? 'Creating checkpoint' : 'Created checkpoint',
    prepare_branch: active ? 'Preparing branch' : 'Prepared branch',
    publish_baseline: active ? 'Publishing baseline' : 'Published baseline',
    attach_baseline: active ? 'Attaching baseline' : 'Attached baseline',
    confirm_baseline: active ? 'Confirming baseline' : 'Confirmed baseline',
    waive_baseline: active ? 'Waiving baseline' : 'Waived baseline',
    submit_idea: active ? 'Submitting idea' : 'Submitted idea',
    record_main_experiment: active ? 'Recording main experiment' : 'Recorded main experiment',
    create_analysis_campaign: active ? 'Creating analysis campaign' : 'Created analysis campaign',
    record_analysis_slice: active ? 'Recording analysis slice' : 'Recorded analysis slice',
    arxiv: active ? 'Reading arXiv paper' : 'Read arXiv paper',
    refresh_summary: active ? 'Refreshing summary' : 'Refreshed summary',
    render_git_graph: active ? 'Rendering git graph' : 'Rendered git graph',
    interact: active ? 'Sending interaction' : 'Sent interaction',
  }

  const paperTitle = asString(resultRecord?.title)
  const baselineId =
    asString(asRecord(resultRecord?.attachment)?.source_baseline_id) ||
    asString(asRecord(asRecord(resultRecord?.attachment)?.entry)?.baseline_id) ||
    asString(resultRecord?.baseline_id) ||
    asString(args?.baseline_id)
  const branch =
    asString(resultRecord?.branch) ||
    asString(asRecord(resultRecord?.graph)?.branch) ||
    asString(asRecord(resultRecord?.branch_record)?.branch) ||
    asString(args?.branch)
  const worktreeRoot = asString(resultRecord?.worktree_root)
  const title =
    paperTitle ||
    asString(resultRecord?.summary) ||
    asString(resultRecord?.guidance) ||
    asString(artifactRecord?.summary) ||
    asString(artifactRecord?.reason) ||
    asString(resultRecord?.agent_instruction) ||
    item.subject ||
    titleMap[tool] ||
    'Artifact update'
  const subtitle =
    tool === 'arxiv'
      ? [
          asString(resultRecord?.paper_id) || asString(args?.paper_id),
          asString(resultRecord?.content_mode),
          asString(resultRecord?.source),
        ]
          .filter(Boolean)
          .join(' · ')
      : tool === 'attach_baseline' || tool === 'confirm_baseline' || tool === 'waive_baseline'
        ? [baselineId, asString(resultRecord?.variant_id), asString(resultRecord?.status)]
            .filter(Boolean)
            .join(' · ')
        : tool === 'prepare_branch'
          ? [branch, worktreeRoot].filter(Boolean).join(' · ')
          : asString(resultRecord?.reason) ||
            asString(resultRecord?.summary) ||
            asString(resultRecord?.guidance) ||
            asString(artifactRecord?.summary) ||
            asString(artifactRecord?.guidance) ||
            null

  const lines = [
    ...summarizeMetricEntries(resultRecord?.metrics_summary),
    ...summarizeMetricEntries(artifactRecord?.metrics_summary),
    ...(tool === 'interact'
      ? [
          asString(resultRecord?.reply_mode)
            ? `reply mode: ${String(resultRecord?.reply_mode)}`
            : '',
          typeof resultRecord?.open_request_count === 'number'
            ? `open requests: ${String(resultRecord?.open_request_count)}`
            : '',
          ...asStringArray(resultRecord?.delivery_targets).slice(0, 2).map((target) => `delivered to: ${target}`),
        ]
      : []),
    ...(tool === 'arxiv' && asString(resultRecord?.content)
      ? [truncateText(String(resultRecord?.content), 220)]
      : []),
    ...(branch ? [`branch: ${branch}`] : []),
    ...(worktreeRoot ? [`worktree: ${worktreeRoot}`] : []),
    ...(baselineId ? [`baseline: ${baselineId}`] : []),
  ].filter(Boolean) as string[]

  const badges = [
    tool,
    asString(resultRecord?.status) || item.status || '',
    asString(artifactRecord?.kind) || '',
  ].filter(Boolean) as string[]

  return {
    label: 'artifact',
    tooltip: tool,
    title: truncateText(title, 180),
    subtitle: subtitle ? truncateText(subtitle, 200) : null,
    Icon: tool === 'arxiv' ? BrainCircuit : GitBranch,
    accentClassName: 'bg-[rgba(186,160,140,0.12)] text-[#8c7240] dark:bg-[rgba(186,160,140,0.14)]',
    statusLabel: normalizeStatus(item.status, active).label,
    statusChipClassName: normalizeStatus(item.status, active).chipClassName,
    statusIcon: normalizeStatus(item.status, active).Icon,
    statusSpinning: normalizeStatus(item.status, active).spinning,
    badges,
    lines,
    paths: extractPathEntries(resultRecord ?? artifactRecord ?? args),
    rawArgs: item.args,
    rawOutput: item.output,
    webSearch: null,
  }
}

function buildMemoryModel(item: RenderOperationFeedItem): StudioToolCardModel {
  const active = item.label === 'tool_call'
  const tool = item.mcpTool || deriveMcpIdentity(item.toolName, item.mcpServer, item.mcpTool).tool || 'memory'
  const args = parseStructuredValue(item.args)
  const resultRecord = asRecord(unwrapToolResult(parseStructuredValue(item.output)))
  const memoryCard = asRecord(resultRecord?.record) ?? resultRecord
  const items = Array.isArray(resultRecord?.items)
    ? resultRecord.items.map((entry) => asRecord(entry)).filter(Boolean)
    : []
  const count =
    typeof resultRecord?.count === 'number'
      ? resultRecord.count
      : items.length
  const query = asString(args?.query) || asString(resultRecord?.query)
  const titleMap: Record<string, string> = {
    write: active ? 'Saving memory' : 'Saved memory',
    read: active ? 'Reading memory' : 'Loaded memory',
    search: active ? 'Searching memory' : 'Searched memory',
    list_recent: active ? 'Loading recent memory' : 'Loaded recent memory',
    promote_to_global: active ? 'Promoting memory' : 'Promoted memory',
  }
  const title =
    query ||
    asString(memoryCard?.title) ||
    asString(args?.title) ||
    item.subject ||
    titleMap[tool] ||
    'Memory update'
  const subtitle =
    tool === 'search'
      ? [query, typeof count === 'number' ? `${count} results` : ''].filter(Boolean).join(' · ')
      : tool === 'list_recent'
        ? typeof count === 'number'
          ? `${count} recent cards`
          : 'Recent project memory'
        : [
            asString(memoryCard?.type) || asString(memoryCard?.kind) || asString(args?.kind),
            asString(memoryCard?.scope) || asString(args?.scope),
          ]
            .filter(Boolean)
            .join(' · ')
  const lines = (
    tool === 'search' || tool === 'list_recent'
      ? items.slice(0, 3).map((entry, index) => {
          const titleText =
            asString(entry?.title) ||
            asString(entry?.id) ||
            `Memory ${index + 1}`
          const excerpt = asString(entry?.excerpt)
          return excerpt ? `${titleText}: ${truncateText(excerpt, 120)}` : titleText
        })
      : [
          asString(memoryCard?.excerpt) || asString(memoryCard?.body) || '',
          ...asStringArray(asRecord(memoryCard?.metadata)?.tags)
            .slice(0, 3)
            .map((tag) => `#${tag}`),
        ]
  ).filter(Boolean) as string[]

  const badges = [
    tool,
    typeof count === 'number' && (tool === 'search' || tool === 'list_recent') ? `${count} results` : '',
    asString(memoryCard?.type) || asString(memoryCard?.kind) || '',
    asString(memoryCard?.scope) || '',
  ].filter(Boolean) as string[]

  return {
    label: 'memory',
    tooltip: tool,
    title: truncateText(title, 180),
    subtitle: subtitle ? truncateText(subtitle, 200) : null,
    Icon: tool === 'search' ? Search : Database,
    accentClassName: 'bg-[rgba(139,164,149,0.12)] text-[#66816f] dark:bg-[rgba(139,164,149,0.14)]',
    statusLabel: normalizeStatus(item.status, active).label,
    statusChipClassName: normalizeStatus(item.status, active).chipClassName,
    statusIcon: normalizeStatus(item.status, active).Icon,
    statusSpinning: normalizeStatus(item.status, active).spinning,
    badges,
    lines,
    paths: extractPathEntries(resultRecord ?? memoryCard ?? args),
    rawArgs: item.args,
    rawOutput: item.output,
    webSearch: null,
  }
}

function buildBashModel(item: RenderOperationFeedItem): StudioToolCardModel {
  const active = item.label === 'tool_call'
  const args = parseStructuredValue(item.args)
  const resultRecord = asRecord(unwrapToolResult(parseStructuredValue(item.output)))
  const command =
    asString(args?.command) ||
    asString(args?.cmd) ||
    asString(item.metadata?.command) ||
    item.subject ||
    'bash command'
  const workdir = asString(args?.workdir) || asString(item.metadata?.workdir)
  const bashId = asString(resultRecord?.bash_id) || asString(item.metadata?.bash_id)
  const logPath = asString(resultRecord?.log_path) || asString(item.metadata?.log_path)
  const lines = [
    workdir ? `workdir: ${workdir}` : '',
    bashId ? `bash id: ${bashId}` : '',
    typeof resultRecord?.exit_code === 'number' ? `exit code: ${String(resultRecord?.exit_code)}` : '',
    asString(resultRecord?.last_progress)
      ? truncateText(String(resultRecord?.last_progress), 160)
      : '',
    asString(resultRecord?.stop_reason) ? `stop: ${String(resultRecord?.stop_reason)}` : '',
  ].filter(Boolean) as string[]

  return {
    label: 'bash exec',
    tooltip: 'bash_exec',
    title: truncateText(command, 180),
    subtitle: workdir ? truncateText(workdir, 160) : null,
    Icon: TerminalSquare,
    accentClassName: 'bg-[rgba(151,164,179,0.14)] text-[var(--text-primary)] dark:bg-[rgba(231,223,210,0.08)]',
    statusLabel: normalizeStatus(
      asString(resultRecord?.status) || item.status,
      active
    ).label,
    statusChipClassName: normalizeStatus(
      asString(resultRecord?.status) || item.status,
      active
    ).chipClassName,
    statusIcon: normalizeStatus(
      asString(resultRecord?.status) || item.status,
      active
    ).Icon,
    statusSpinning: normalizeStatus(
      asString(resultRecord?.status) || item.status,
      active
    ).spinning,
    badges: ['bash_exec', asString(resultRecord?.mode) || asString(args?.mode) || ''].filter(Boolean) as string[],
    lines,
    paths: logPath ? [{ label: 'log', path: logPath }] : [],
    rawArgs: item.args,
    rawOutput: item.output,
    webSearch: null,
  }
}

function buildWebSearchModel(item: RenderOperationFeedItem): StudioToolCardModel {
  const active = item.label === 'tool_call'
  const payload = normalizeWebSearchPayload({
    args: parseStructuredValue(item.args),
    metadataSearch: item.metadata?.search,
    output: item.output,
    fallbackQuery: item.subject || '',
  })
  const query = payload.query || item.subject || 'web search'
  const countLabel = payload.results.length > 0 ? `${payload.results.length} results` : ''
  const queryCountLabel = payload.queries.length > 1 ? `${payload.queries.length} queries` : ''
  const subtitle = [payload.actionType, countLabel, queryCountLabel].filter(Boolean).join(' · ')

  return {
    label: 'web search',
    tooltip: 'web_search',
    title: truncateText(query, 180),
    subtitle: subtitle || null,
    Icon: Globe2,
    accentClassName: 'bg-[rgba(121,145,182,0.12)] text-[#58779f] dark:bg-[rgba(121,145,182,0.14)]',
    statusLabel: normalizeStatus(item.status, active).label,
    statusChipClassName: normalizeStatus(item.status, active).chipClassName,
    statusIcon: normalizeStatus(item.status, active).Icon,
    statusSpinning: normalizeStatus(item.status, active).spinning,
    badges: ['web_search', countLabel].filter(Boolean) as string[],
    lines: [
      payload.summary ? truncateText(payload.summary, 180) : '',
      ...payload.queries.slice(1, 3).map((entry) => truncateText(entry, 120)),
    ].filter(Boolean),
    paths: [],
    rawArgs: item.args,
    rawOutput: item.output,
    webSearch: payload,
  }
}

function buildGenericModel(item: RenderOperationFeedItem): StudioToolCardModel {
  const active = item.label === 'tool_call'
  return {
    label: item.toolName || 'tool',
    tooltip: item.toolName || 'tool',
    title: truncateText(item.subject || item.content || item.toolName || 'Tool call', 180),
    subtitle: item.toolName && item.subject ? truncateText(item.toolName, 120) : null,
    Icon: Wrench,
    accentClassName: 'bg-black/[0.05] text-foreground dark:bg-white/[0.06]',
    statusLabel: normalizeStatus(item.status, active).label,
    statusChipClassName: normalizeStatus(item.status, active).chipClassName,
    statusIcon: normalizeStatus(item.status, active).Icon,
    statusSpinning: normalizeStatus(item.status, active).spinning,
    badges: [item.toolName || 'tool'].filter(Boolean) as string[],
    lines: [
      item.content ? truncateText(item.content, 160) : '',
      item.subject ? truncateText(item.subject, 160) : '',
    ].filter(Boolean) as string[],
    paths: [],
    rawArgs: item.args,
    rawOutput: item.output,
    webSearch: null,
  }
}

function buildToolCardModel(item: RenderOperationFeedItem) {
  const resolvedIdentity = deriveMcpIdentity(item.toolName, item.mcpServer, item.mcpTool)
  if (resolvedIdentity.server === 'artifact') {
    return buildArtifactModel(item)
  }
  if (resolvedIdentity.server === 'memory') {
    return buildMemoryModel(item)
  }
  if (resolvedIdentity.server === 'bash_exec') {
    return buildBashModel(item)
  }
  if ((item.toolName || '').trim().toLowerCase() === 'web_search') {
    return buildWebSearchModel(item)
  }
  return buildGenericModel(item)
}

function InlinePathList({ paths }: { paths: Array<{ label: string; path: string }> }) {
  if (paths.length === 0) return null
  return (
    <div className="space-y-1.5 text-[11px] leading-5 text-muted-foreground">
      {paths.slice(0, 3).map((entry) => (
        <div key={`${entry.label}:${entry.path}`} className="break-all">
          <span className="font-medium text-foreground">{entry.label}:</span> {entry.path}
        </div>
      ))}
    </div>
  )
}

function FallbackOutput({ value }: { value?: string }) {
  if (!value?.trim()) return null
  return (
    <pre className="feed-scrollbar max-h-[240px] max-w-full overflow-x-hidden overflow-y-auto whitespace-pre-wrap break-words [overflow-wrap:anywhere] rounded-[16px] bg-black/[0.03] px-3 py-3 text-[11px] leading-6 text-muted-foreground dark:bg-white/[0.05]">
      {value}
    </pre>
  )
}

function StudioWebSearchPanel({
  payload,
  isSearching,
}: {
  payload: NormalizedWebSearchPayload
  isSearching: boolean
}) {
  return (
    <div className="space-y-2.5">
      {payload.queries.length > 0 ? (
        <div className="space-y-1.5">
          <div className="text-[10px] font-medium uppercase tracking-[0.08em] text-muted-foreground">
            Queries
          </div>
          <WebSearchQueryPills queries={payload.queries} activeQuery={payload.query} compact />
        </div>
      ) : null}

      {payload.summary ? (
        <div className="rounded-[14px] border border-black/[0.06] bg-white/[0.68] px-3 py-2.5 text-[12px] leading-5 text-muted-foreground dark:border-white/[0.08] dark:bg-white/[0.03]">
          {payload.summary}
        </div>
      ) : null}

      <WebSearchResults
        payload={payload}
        compact
        maxItems={5}
        emptyMessage={
          isSearching
            ? 'Searching the web...'
            : payload.queries.length > 0
              ? 'No structured result cards were returned for this search.'
              : 'No search results.'
        }
      />
    </div>
  )
}

export function StudioToolCard({
  item,
  isLatest = false,
}: {
  item: RenderOperationFeedItem
  isLatest?: boolean
}) {
  const model = React.useMemo(() => buildToolCardModel(item), [item])
  const [expanded, setExpanded] = React.useState(() => isLatest)
  const expandModeRef = React.useRef<'auto' | 'manual-open' | 'manual-close'>('auto')
  const StatusIcon = model.statusIcon
  const fallbackOutput = model.rawOutput?.trim() || ''
  const showSubtitle = Boolean(model.subtitle && model.subtitle !== model.title)
  const hasStructuredBody = Boolean(showSubtitle || model.webSearch || model.lines.length > 0 || model.paths.length > 0)

  React.useEffect(() => {
    if (isLatest) {
      if (expandModeRef.current !== 'manual-close') {
        setExpanded(true)
      }
      return
    }
    if (expandModeRef.current === 'auto') {
      setExpanded(false)
    }
  }, [isLatest])

  const handleToggle = React.useCallback(() => {
    setExpanded((current) => {
      const next = !current
      expandModeRef.current = next ? 'manual-open' : 'manual-close'
      return next
    })
  }, [])

  const summaryText = model.title || model.subtitle || model.lines[0] || model.label

  return (
    <div className="min-w-0 overflow-hidden rounded-[16px] border border-black/[0.04] bg-black/[0.02] px-3 py-2 dark:border-white/[0.06] dark:bg-white/[0.04]">
      <button
        type="button"
        className="flex w-full min-w-0 items-center gap-2.5 text-left"
        onClick={handleToggle}
      >
        <div
          title={model.tooltip}
          aria-label={model.tooltip}
          className={cn(
            'flex h-8 w-8 shrink-0 items-center justify-center rounded-[12px]',
            model.accentClassName
          )}
        >
          <model.Icon className="h-4 w-4" />
        </div>

        <div className="min-w-0 flex-1">
          <div
            className="truncate text-[13px] font-medium leading-5 text-foreground"
            title={summaryText}
          >
            {summaryText}
          </div>
        </div>

        <div className="ml-auto flex shrink-0 items-center gap-2 text-[11px] text-muted-foreground">
          <span
            className={cn(
              'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-medium',
              model.statusChipClassName
            )}
          >
            <StatusIcon className={cn('h-3.5 w-3.5', model.statusSpinning && 'animate-spin')} />
            {model.statusLabel}
          </span>
          {item.createdAt ? <span>{formatTime(item.createdAt)}</span> : null}
          <ChevronDown
            className={cn(
              'h-4 w-4 transition-transform',
              expanded && 'rotate-180'
            )}
          />
        </div>
      </button>

      {expanded ? (
        <div className="ml-[42px] mt-2.5 space-y-2.5 border-t border-black/[0.05] pt-2.5 dark:border-white/[0.06]">
          {showSubtitle ? (
            <div className="text-[11px] leading-5 text-muted-foreground">
              {model.subtitle}
            </div>
          ) : null}

          {model.webSearch ? (
            <StudioWebSearchPanel payload={model.webSearch} isSearching={item.label === 'tool_call'} />
          ) : model.lines.length > 0 ? (
            <div className="space-y-1.5 text-[12px] leading-6 text-muted-foreground">
              {model.lines.slice(0, 3).map((line, index) => (
                <div key={`${index}:${line}`} className="break-words [overflow-wrap:anywhere]">
                  {line}
                </div>
              ))}
            </div>
          ) : null}

          <InlinePathList paths={model.paths} />

          {!hasStructuredBody ? <FallbackOutput value={fallbackOutput || model.rawArgs} /> : null}
        </div>
      ) : null}
    </div>
  )
}

export default StudioToolCard
