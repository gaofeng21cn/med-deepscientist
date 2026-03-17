'use client'

import * as React from 'react'
import { ArrowUp, Loader2, Slash, Square } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { useToast } from '@/components/ui/toast'
import { useI18n } from '@/lib/i18n/useI18n'
import type { FeedItem, QuestSummary } from '@/types'
import { QuestCopilotPaneLayout } from './QuestCopilotPaneLayout'
import { QuestStudioDirectTimeline } from './QuestStudioDirectTimeline'

type ConnectorCommand = {
  name: string
  description?: string
}

type QuestStudioTraceViewProps = {
  questId: string
  feed: FeedItem[]
  snapshot?: QuestSummary | null
  loading: boolean
  restoring: boolean
  streaming: boolean
  activeToolCount: number
  connectionState: 'connecting' | 'connected' | 'reconnecting' | 'error'
  error?: string | null
  stopping?: boolean
  showStopButton?: boolean
  slashCommands?: ConnectorCommand[]
  hasOlderHistory?: boolean
  loadingOlderHistory?: boolean
  onLoadOlderHistory?: () => Promise<void>
  onSubmit: (message: string) => Promise<void>
  onStopRun: () => Promise<void>
}

export function QuestStudioTraceView({
  questId,
  feed,
  snapshot,
  loading,
  restoring,
  streaming,
  activeToolCount,
  connectionState,
  error,
  stopping = false,
  showStopButton = false,
  slashCommands = [],
  hasOlderHistory = false,
  loadingOlderHistory = false,
  onLoadOlderHistory,
  onSubmit,
  onStopRun,
}: QuestStudioTraceViewProps) {
  const { t } = useI18n('workspace')
  const { addToast } = useToast()
  const [input, setInput] = React.useState('')
  const [submitting, setSubmitting] = React.useState(false)
  const composerRef = React.useRef<HTMLTextAreaElement | null>(null)

  const filteredCommands = React.useMemo(() => {
    const raw = input.trimStart()
    if (!raw.startsWith('/')) return []
    const query = raw.slice(1).toLowerCase()
    return slashCommands
      .filter((item) => {
        if (!query) return true
        return (
          item.name.toLowerCase().includes(query) ||
          (item.description || '').toLowerCase().includes(query)
        )
      })
      .slice(0, 8)
  }, [input, slashCommands])

  const handleSubmit = React.useCallback(async () => {
    const trimmed = input.trim()
    if (!trimmed || submitting) return
    setSubmitting(true)
    try {
      await onSubmit(trimmed)
      setInput('')
      composerRef.current?.focus()
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : String(caught)
      addToast({
        title: t('copilot_send_failed_title', undefined, 'Send failed'),
        message,
        variant: 'error',
      })
    } finally {
      setSubmitting(false)
    }
  }, [addToast, input, onSubmit, submitting, t])

  const handleStop = React.useCallback(async () => {
    if (stopping) return
    try {
      await onStopRun()
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : String(caught)
      addToast({
        title: t('copilot_stop', undefined, 'Stop'),
        message,
        variant: 'error',
      })
    }
  }, [addToast, onStopRun, stopping, t])

  return (
    <QuestCopilotPaneLayout
      footer={
        <div className="relative">
          {filteredCommands.length > 0 ? (
            <div className="absolute bottom-full left-0 right-0 mb-2 overflow-hidden rounded-2xl border border-black/[0.08] bg-white/[0.92] shadow-[0_18px_42px_-34px_rgba(17,24,39,0.22)] dark:border-white/[0.10] dark:bg-[rgba(34,37,44,0.92)]">
              {filteredCommands.map((item) => (
                <button
                  key={item.name}
                  type="button"
                  className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm transition hover:bg-black/[0.03] dark:hover:bg-white/[0.05]"
                  onClick={() => {
                    setInput(`/${item.name} `)
                    composerRef.current?.focus()
                  }}
                >
                  <Slash className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="font-medium">/{item.name}</span>
                  {item.description ? (
                    <span className="ml-auto line-clamp-1 text-xs text-muted-foreground">
                      {item.description}
                    </span>
                  ) : null}
                </button>
              ))}
            </div>
          ) : null}

          <Textarea
            ref={composerRef}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if ((event.nativeEvent as any)?.isComposing) return
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                void handleSubmit()
              }
            }}
            rows={2}
            className="min-h-[56px] resize-none rounded-2xl border border-black/[0.08] bg-white/[0.9] px-4 py-3 shadow-sm focus-visible:ring-0 dark:border-white/[0.10] dark:bg-white/[0.05]"
            placeholder={t('copilot_connector_placeholder')}
          />

          <div className="mt-2 flex items-center justify-between gap-3">
            <div className="text-[11px] text-muted-foreground">{t('copilot_connector_enter_hint')}</div>
            <div className="flex items-center gap-2">
              {showStopButton || stopping ? (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-8 rounded-full"
                  disabled={stopping}
                  onClick={() => void handleStop()}
                >
                  {stopping ? (
                    <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Square className="mr-2 h-3.5 w-3.5" />
                  )}
                  {t('copilot_stop')}
                </Button>
              ) : null}
              <Button
                type="button"
                size="sm"
                className="h-8 rounded-full"
                disabled={!input.trim() || submitting}
                onClick={() => void handleSubmit()}
              >
                {submitting ? (
                  <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                ) : (
                  <ArrowUp className="mr-2 h-3.5 w-3.5" />
                )}
                {t('copilot_send')}
              </Button>
            </div>
          </div>
        </div>
      }
    >
      {({ bottomInset }) => (
        <QuestStudioDirectTimeline
          questId={questId}
          feed={feed}
          loading={loading}
          restoring={restoring}
          streaming={streaming}
          activeToolCount={activeToolCount}
          connectionState={connectionState}
          error={error}
          snapshot={snapshot}
          hasOlderHistory={hasOlderHistory}
          loadingOlderHistory={loadingOlderHistory}
          onLoadOlderHistory={onLoadOlderHistory}
          emptyLabel={t('copilot_studio_empty', undefined, 'Copilot trace appears here.')}
          bottomInset={bottomInset}
        />
      )}
    </QuestCopilotPaneLayout>
  )
}

export default QuestStudioTraceView
