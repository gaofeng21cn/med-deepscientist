import { useEffect, useMemo, useState } from 'react'
import { ArrowUpRight, Search, Sparkles } from 'lucide-react'

import { OverlayDialog } from '@/components/home/OverlayDialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { getBenchStoreSetupPacket, listBenchStoreEntries } from '@/lib/api/benchstore'
import type { BenchEntry, BenchSetupPacket } from '@/lib/types/benchstore'

type BenchStoreDialogProps = {
  open: boolean
  locale: 'en' | 'zh'
  onClose: () => void
  setupQuestId?: string | null
  setupQuestCreating?: boolean
  onStartWithSetupPacket?: (setupPacket: BenchSetupPacket) => void | Promise<void>
  onRequestSetupAgent?: (payload: {
    message: string
    entry?: BenchEntry | null
    setupPacket?: BenchSetupPacket | null
  }) => void | Promise<void>
}

function copy(locale: 'en' | 'zh') {
  return locale === 'zh'
    ? {
        title: 'BenchStore',
        body: '先从 AISB / BenchStore 里挑一个值得做的 benchmark，再把它带进 Start Research 表单。',
        searchPlaceholder: '搜索 benchmark、论文、tag 或任务描述',
        empty: '当前没有可展示的 benchmark。',
        noResults: '没有匹配的 benchmark。',
        select: '带入 Start Research',
        direct: '直接启动 SetupAgent',
        working: '正在准备…',
        tags: '标签',
      }
    : {
        title: 'BenchStore',
        body: 'Pick a benchmark from AISB / BenchStore first, then send it into the Start Research form.',
        searchPlaceholder: 'Search benchmark, paper, tag, or task description',
        empty: 'No benchmarks are available right now.',
        noResults: 'No matching benchmarks found.',
        select: 'Use In Start Research',
        direct: 'Start SetupAgent',
        working: 'Preparing…',
        tags: 'Tags',
      }
}

function matchesQuery(entry: BenchEntry, query: string) {
  const normalized = query.trim().toLowerCase()
  if (!normalized) return true
  const haystack = [
    entry.id,
    entry.name,
    entry.one_line || '',
    entry.task_description || '',
    ...(entry.capability_tags || []),
    ...(entry.track_fit || []),
    entry.paper?.title || '',
  ]
    .join('\n')
    .toLowerCase()
  return haystack.includes(normalized)
}

export function BenchStoreDialog(props: BenchStoreDialogProps) {
  const t = copy(props.locale)
  const [entries, setEntries] = useState<BenchEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [activeEntryId, setActiveEntryId] = useState<string | null>(null)

  useEffect(() => {
    if (!props.open) return
    let active = true
    setLoading(true)
    setError(null)
    void listBenchStoreEntries()
      .then((payload) => {
        if (!active) return
        setEntries(payload.items || [])
      })
      .catch((caught) => {
        if (!active) return
        setError(caught instanceof Error ? caught.message : 'Failed to load BenchStore.')
      })
      .finally(() => {
        if (active) {
          setLoading(false)
        }
      })
    return () => {
      active = false
    }
  }, [props.open])

  const filteredEntries = useMemo(() => entries.filter((entry) => matchesQuery(entry, query)), [entries, query])

  const handleSelect = async (entry: BenchEntry) => {
    setActiveEntryId(entry.id)
    try {
      const payload = await getBenchStoreSetupPacket(entry.id)
      await props.onStartWithSetupPacket?.(payload.setup_packet)
      props.onClose()
    } finally {
      setActiveEntryId(null)
    }
  }

  const handleDirectAssist = async (entry: BenchEntry) => {
    setActiveEntryId(entry.id)
    try {
      const payload = await getBenchStoreSetupPacket(entry.id)
      await props.onRequestSetupAgent?.({
        message:
          props.locale === 'zh'
            ? `请先根据 BenchStore 条目 ${entry.name} 整理启动表单，能直接补齐的内容就直接回写。`
            : `Please refine the start form for BenchStore entry ${entry.name} and write back any fields that are already clear.`,
        entry,
        setupPacket: payload.setup_packet,
      })
      await props.onStartWithSetupPacket?.(payload.setup_packet)
      props.onClose()
    } finally {
      setActiveEntryId(null)
    }
  }

  return (
    <OverlayDialog
      open={props.open}
      title={t.title}
      description={t.body}
      onClose={props.onClose}
      className="h-[90svh] max-w-[96vw] rounded-[26px] sm:h-[88vh] sm:max-w-[78rem]"
    >
      <div className="flex h-full min-h-0 flex-col gap-4 p-3 sm:p-4">
        <div className="flex items-center gap-3 rounded-[18px] border border-[rgba(45,42,38,0.09)] bg-white/75 px-4 py-3">
          <Search className="h-4 w-4 text-[rgba(107,103,97,0.72)]" />
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={t.searchPlaceholder}
            className="border-0 bg-transparent px-0 shadow-none focus-visible:ring-0"
          />
        </div>

        {error ? <div className="text-sm text-[#9a1b1b]">{error}</div> : null}
        {loading ? <div className="text-sm text-[rgba(107,103,97,0.78)]">{t.working}</div> : null}

        <div className="feed-scrollbar min-h-0 flex-1 overflow-y-auto">
          <div className="grid gap-3 lg:grid-cols-2">
            {(query.trim() ? filteredEntries : entries).map((entry) => {
              const busy = activeEntryId === entry.id
              return (
                <div
                  key={entry.id}
                  className="rounded-[22px] border border-[rgba(45,42,38,0.09)] bg-[rgba(255,255,255,0.78)] p-4 shadow-[0_14px_40px_-26px_rgba(45,42,38,0.26)]"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="text-sm font-semibold text-[rgba(38,36,33,0.96)]">{entry.name}</div>
                      <div className="mt-1 text-xs text-[rgba(107,103,97,0.72)]">{entry.id}</div>
                    </div>
                    <Badge className="rounded-full px-2.5 py-1 text-[10px] uppercase tracking-wide">
                      {entry.requires_execution ? 'Execution' : 'Light'}
                    </Badge>
                  </div>
                  <div className="mt-3 text-sm leading-6 text-[rgba(56,52,47,0.9)]">
                    {entry.one_line || entry.task_description || ''}
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {(entry.capability_tags || []).slice(0, 4).map((tag) => (
                      <span
                        key={tag}
                        className="rounded-full bg-[rgba(244,239,233,0.86)] px-2.5 py-1 text-[11px] text-[rgba(86,82,77,0.88)]"
                      >
                        {tag}
                      </span>
                    ))}
                    {(entry.track_fit || []).slice(0, 2).map((tag) => (
                      <span
                        key={`track-${tag}`}
                        className="rounded-full bg-[rgba(215,198,174,0.32)] px-2.5 py-1 text-[11px] text-[rgba(86,82,77,0.88)]"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                  <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div className="text-xs text-[rgba(107,103,97,0.72)]">
                      {t.tags}: {(entry.capability_tags || []).length}
                    </div>
                    <div className="flex flex-col gap-2 sm:flex-row">
                      {props.onRequestSetupAgent ? (
                        <Button
                          variant="secondary"
                          className="rounded-full"
                          isLoading={busy && Boolean(props.setupQuestCreating)}
                          onClick={() => void handleDirectAssist(entry)}
                        >
                          <Sparkles className="h-4 w-4" />
                          {t.direct}
                        </Button>
                      ) : null}
                      <Button className="rounded-full" isLoading={busy} onClick={() => void handleSelect(entry)}>
                        <ArrowUpRight className="h-4 w-4" />
                        {t.select}
                      </Button>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
          {!loading && entries.length === 0 ? (
            <div className="py-10 text-center text-sm text-[rgba(107,103,97,0.78)]">{t.empty}</div>
          ) : null}
          {!loading && entries.length > 0 && filteredEntries.length === 0 && query.trim() ? (
            <div className="py-10 text-center text-sm text-[rgba(107,103,97,0.78)]">{t.noResults}</div>
          ) : null}
        </div>
      </div>
    </OverlayDialog>
  )
}

export default BenchStoreDialog
