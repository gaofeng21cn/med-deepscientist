'use client'

import * as React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ArrowUp, Check, CheckCheck, Loader2, Slash, Square, TriangleAlert } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { useToast } from '@/components/ui/toast'
import { useI18n } from '@/lib/i18n/useI18n'
import { useTokenStream } from '@/lib/plugins/ai-manus/hooks/useTokenStream'
import { ChatScrollProvider } from '@/lib/plugins/ai-manus/lib/chat-scroll-context'
import { buildQuestTranscriptMessages } from '@/lib/questTranscript'
import { useAutoFollowScroll } from '@/lib/useAutoFollowScroll'
import { cn } from '@/lib/utils'
import type { FeedItem } from '@/types'
import { QuestCopilotPaneLayout } from './QuestCopilotPaneLayout'

type ConnectorCommand = {
  name: string
  description?: string
}

type QuestConnectorChatViewProps = {
  feed: FeedItem[]
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

type ConnectorMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  createdAt?: string
  streaming?: boolean
  badge?: string | null
  emphasis?: 'message' | 'artifact'
  deliveryState?: string | null
}

function formatTime(value?: string) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return new Intl.DateTimeFormat(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    month: 'short',
    day: 'numeric',
  }).format(date)
}

export function buildQuestConnectorMessages(feed: FeedItem[]): ConnectorMessage[] {
  return buildQuestTranscriptMessages(feed)
}

function DeliveryIndicator({ state }: { state?: string | null }) {
  if (!state) return null
  const normalized = state.trim().toLowerCase()
  if (!normalized) return null
  if (normalized === 'sending') {
    return <Loader2 className="h-3 w-3 animate-spin text-white/70" />
  }
  if (normalized === 'sent') {
    return <Check className="h-3 w-3 text-white/70" />
  }
  if (normalized === 'delivered') {
    return <CheckCheck className="h-3 w-3 text-white/70" />
  }
  if (normalized === 'failed') {
    return <TriangleAlert className="h-3 w-3 text-rose-300" />
  }
  return (
    <span className="text-[10px] leading-none text-white/60">{normalized}</span>
  )
}

function MessageBubble({
  item,
  animateText,
}: {
  item: ConnectorMessage
  animateText: boolean
}) {
  const isUser = item.role === 'user'
  const isAssistant = item.role === 'assistant'
  const contentRef = React.useRef<HTMLDivElement | null>(null)

  useTokenStream({
    ref: contentRef,
    active: animateText,
    contentKey: `${item.id}:${item.content}`,
    mode: item.emphasis === 'artifact' ? 'status' : 'assistant',
  })

  return (
    <div
      className={cn(
        'flex w-full flex-col gap-1',
        isUser ? 'items-end' : 'items-start'
      )}
    >
      <div
        className={cn(
          'min-w-0 max-w-[92%] overflow-hidden rounded-2xl px-3.5 py-2.5 text-sm leading-6',
          isUser
            ? 'bg-[#2F3437] text-white'
            : item.emphasis === 'artifact'
              ? 'bg-[rgba(159,177,194,0.16)] text-foreground dark:bg-white/[0.06] dark:text-white/90'
              : 'bg-white/[0.88] text-foreground dark:bg-white/[0.06] dark:text-white/90'
        )}
      >
        {item.badge && isAssistant ? (
          <div className="mb-1 text-[11px] font-medium text-muted-foreground dark:text-white/60">
            {item.badge}
          </div>
        ) : null}
        <div
          ref={contentRef}
          className={cn(
            'ds-copilot-markdown prose prose-sm max-w-none whitespace-pre-wrap break-words [overflow-wrap:anywhere] leading-6',
            isUser ? 'prose-invert text-white' : 'text-foreground dark:prose-invert'
          )}
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{item.content}</ReactMarkdown>
        </div>
      </div>
      {(item.createdAt || (isUser && item.deliveryState)) ? (
        <div className={cn('flex items-center gap-2 text-[10px]', isUser ? 'text-white/55' : 'text-muted-foreground')}>
          {isUser ? <DeliveryIndicator state={item.deliveryState} /> : null}
          {item.createdAt ? <span>{formatTime(item.createdAt)}</span> : null}
        </div>
      ) : null}
    </div>
  )
}

export function QuestConnectorChatView({
  feed,
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
}: QuestConnectorChatViewProps) {
  const { t } = useI18n('workspace')
  const { addToast } = useToast()
  const [input, setInput] = React.useState('')
  const [submitting, setSubmitting] = React.useState(false)
  const composerRef = React.useRef<HTMLTextAreaElement | null>(null)
  const listRef = React.useRef<HTMLDivElement | null>(null)
  const contentRef = React.useRef<HTMLDivElement | null>(null)
  const chatMessages = React.useMemo(() => buildQuestConnectorMessages(feed), [feed])
  const latestAnimatedMessageId = React.useMemo(() => {
    for (let index = chatMessages.length - 1; index >= 0; index -= 1) {
      const item = chatMessages[index]
      if (item.role === 'assistant' && item.content.trim()) {
        return item.id
      }
    }
    return null
  }, [chatMessages])
  const { isNearBottom } = useAutoFollowScroll({
    scrollRef: listRef,
    contentRef,
    deps: [chatMessages.length, streaming, activeToolCount],
  })
  const prependAnchorRef = React.useRef<{ active: boolean; scrollHeight: number; scrollTop: number }>({
    active: false,
    scrollHeight: 0,
    scrollTop: 0,
  })

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
      .slice(0, 6)
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

  const handleLoadOlderHistory = React.useCallback(async () => {
    if (!hasOlderHistory || loadingOlderHistory || !onLoadOlderHistory) return
    const root = listRef.current
    if (root) {
      prependAnchorRef.current = {
        active: true,
        scrollHeight: root.scrollHeight,
        scrollTop: root.scrollTop,
      }
    }
    await onLoadOlderHistory()
  }, [hasOlderHistory, loadingOlderHistory, onLoadOlderHistory])

  React.useEffect(() => {
    if (!prependAnchorRef.current.active || loadingOlderHistory) {
      return
    }
    const root = listRef.current
    if (!root) {
      prependAnchorRef.current.active = false
      return
    }
    const delta = root.scrollHeight - prependAnchorRef.current.scrollHeight
    root.scrollTop = prependAnchorRef.current.scrollTop + Math.max(delta, 0)
    prependAnchorRef.current.active = false
  }, [chatMessages.length, loadingOlderHistory])

  return (
    <QuestCopilotPaneLayout
      statusLine={connectionState !== 'connected' || error ? error || connectionState : undefined}
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
              if ((event.nativeEvent as any)?.isComposing) {
                return
              }
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
        <ChatScrollProvider value={{ isNearBottom }}>
          <div
            ref={listRef}
            className="feed-scrollbar flex-1 min-h-0 overflow-x-hidden overflow-y-auto px-4 pt-4"
            style={{
              paddingBottom: bottomInset,
              scrollPaddingBottom: bottomInset,
            }}
            onWheel={(event) => {
              const root = listRef.current
              if (!root || event.deltaY >= 0 || root.scrollTop > 24) {
                return
              }
              void handleLoadOlderHistory()
            }}
          >
            <div ref={contentRef} className="flex min-w-0 flex-col gap-3">
              {hasOlderHistory ? (
                <div className="flex justify-center pb-1">
                  <button
                    type="button"
                    className="rounded-full border border-black/[0.08] bg-white/[0.88] px-3 py-1 text-[11px] text-muted-foreground transition hover:bg-white dark:border-white/[0.10] dark:bg-white/[0.05] dark:hover:bg-white/[0.08]"
                    disabled={loadingOlderHistory}
                    onClick={() => void handleLoadOlderHistory()}
                  >
                    {loadingOlderHistory ? 'Loading older updates...' : 'Load older updates'}
                  </button>
                </div>
              ) : null}
              {chatMessages.length === 0 ? (
                <div className="flex min-h-full items-center justify-center text-sm text-muted-foreground">
                  {restoring || loading ? t('copilot_connector_restoring') : t('copilot_connector_ready')}
                </div>
              ) : (
                chatMessages.map((item) => (
                  <MessageBubble
                    key={item.id}
                    item={item}
                    animateText={
                      item.role === 'assistant' &&
                      latestAnimatedMessageId === item.id &&
                      Boolean(item.streaming || streaming)
                    }
                  />
                ))
              )}

              {(loading || restoring) && chatMessages.length === 0 ? (
                <div className="flex justify-center py-4">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                </div>
              ) : null}
            </div>
          </div>
        </ChatScrollProvider>
      )}
    </QuestCopilotPaneLayout>
  )
}

export default QuestConnectorChatView
