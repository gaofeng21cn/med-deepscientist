'use client'

import * as React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  Brain,
  ChevronDown,
  Sparkles,
  User2,
} from 'lucide-react'

import { AgentCommentBlock } from '@/components/feed/AgentCommentBlock'
import { Badge } from '@/components/ui/badge'
import { LogoIcon } from '@/components/ui/workspace-icons'
import { findLatestRenderedOperationId, mergeFeedItemsForRender } from '@/lib/feedOperations'
import { deriveMcpIdentity } from '@/lib/mcpIdentity'
import OrbitLogoStatus from '@/lib/plugins/ai-manus/components/OrbitLogoStatus'
import { ThinkingIndicator } from '@/lib/plugins/ai-manus/components/ThinkingIndicator'
import { useTokenStream } from '@/lib/plugins/ai-manus/hooks/useTokenStream'
import { ChatScrollProvider } from '@/lib/plugins/ai-manus/lib/chat-scroll-context'
import { buildStudioTurns, type StudioTurn, type StudioTurnBlock } from '@/lib/studioTurns'
import { useAutoFollowScroll } from '@/lib/useAutoFollowScroll'
import type { FeedItem, QuestSummary } from '@/types'
import { QuestBashExecOperation } from './QuestBashExecOperation'
import { StudioToolCard } from './StudioToolCards'

type QuestStudioDirectTimelineProps = {
  questId: string
  feed: FeedItem[]
  loading: boolean
  restoring: boolean
  streaming: boolean
  activeToolCount: number
  connectionState: 'connecting' | 'connected' | 'reconnecting' | 'error'
  error?: string | null
  snapshot?: QuestSummary | null
  hasOlderHistory?: boolean
  loadingOlderHistory?: boolean
  onLoadOlderHistory?: () => Promise<void>
  emptyLabel?: string
  bottomInset?: number
}

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

function EmptyState({
  loading,
  restoring,
  connectionState,
  emptyLabel,
}: {
  loading: boolean
  restoring: boolean
  connectionState: QuestStudioDirectTimelineProps['connectionState']
  emptyLabel: string
}) {
  const statusLabel =
    restoring || loading
      ? 'Restoring recent Studio trace…'
      : connectionState === 'reconnecting'
        ? 'Studio trace reconnecting…'
        : connectionState === 'connecting'
          ? 'Connecting to Studio trace…'
          : connectionState === 'error'
            ? 'Studio trace is temporarily unavailable.'
            : emptyLabel

  return (
    <div className="flex min-h-[280px] items-center justify-center rounded-[28px] border border-dashed border-black/[0.08] px-6 py-10 dark:border-white/[0.10]">
      <div className="max-w-sm text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-[20px] border border-black/10 bg-white/[0.85] dark:border-white/[0.12] dark:bg-white/[0.05]">
          <OrbitLogoStatus compact sizePx={28} toolCount={0} resetKey={statusLabel} />
        </div>
        <div className="text-sm font-medium text-foreground">{statusLabel}</div>
        {loading || restoring || connectionState === 'connecting' || connectionState === 'reconnecting' ? (
          <div className="mt-3 flex justify-center">
            <ThinkingIndicator compact />
          </div>
        ) : (
          <div className="mt-2 text-xs text-muted-foreground">
            Assistant text, tool calls, and durable artifacts will appear here as a conversation timeline.
          </div>
        )}
      </div>
    </div>
  )
}

function StreamMarkdownBlock({
  content,
  contentKey,
  animateText,
  mode = 'assistant',
  className,
}: {
  content: string
  contentKey: string
  animateText: boolean
  mode?: 'assistant' | 'reasoning'
  className: string
}) {
  const contentRef = React.useRef<HTMLDivElement | null>(null)

  useTokenStream({
    ref: contentRef,
    active: animateText,
    contentKey,
    mode,
  })

  return (
    <div ref={contentRef} className={className}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  )
}

function StudioMessageBlock({
  block,
  animateText,
}: {
  block: Extract<StudioTurnBlock, { kind: 'message' }>
  animateText: boolean
}) {
  return (
    <div className="min-w-0 overflow-hidden rounded-[24px] border border-black/[0.06] bg-white/[0.90] px-4 py-3 shadow-[0_16px_36px_-34px_rgba(17,24,39,0.18)] dark:border-white/[0.08] dark:bg-white/[0.05]">
      <StreamMarkdownBlock
        content={block.item.content || ''}
        contentKey={`${block.id}:${block.item.content || ''}`}
        animateText={animateText}
        className="ds-copilot-markdown prose prose-sm max-w-none break-words [overflow-wrap:anywhere] leading-7 text-foreground dark:prose-invert"
      />
    </div>
  )
}

function StudioReasoningBlock({
  block,
  animateText,
}: {
  block: Extract<StudioTurnBlock, { kind: 'reasoning' }>
  animateText: boolean
}) {
  if (!block.item.content.trim()) {
    return null
  }
  return (
    <details
      className="group min-w-0 overflow-hidden rounded-[24px] border border-black/[0.06] bg-[linear-gradient(180deg,rgba(251,249,244,0.88),rgba(244,239,233,0.94))] dark:border-white/[0.08] dark:bg-[linear-gradient(180deg,rgba(40,42,48,0.84),rgba(30,33,39,0.92))]"
      open={Boolean(block.item.stream)}
    >
      <summary className="flex cursor-pointer list-none items-center gap-3 px-4 py-3 text-sm font-medium text-foreground [&::-webkit-details-marker]:hidden">
        <div className="flex h-8 w-8 items-center justify-center rounded-[14px] border border-black/10 bg-[rgba(183,165,154,0.12)] dark:border-white/[0.12] dark:bg-[rgba(183,165,154,0.16)]">
          <Brain className="h-4 w-4" />
        </div>
        <div className="min-w-0 flex-1">
          <div>Thinking</div>
          <div className="text-xs font-normal text-muted-foreground">
            {block.item.stream ? 'Streaming reasoning' : 'Reasoning trace'}
          </div>
        </div>
        <ChevronDown className="h-4 w-4 transition-transform group-open:rotate-180" />
      </summary>
      <div className="border-t border-black/[0.05] px-4 py-3 dark:border-white/[0.06]">
        <StreamMarkdownBlock
          content={block.item.content}
          contentKey={`${block.id}:${block.item.content}`}
          animateText={animateText}
          mode="reasoning"
          className="ds-copilot-markdown prose prose-sm max-w-none break-words [overflow-wrap:anywhere] leading-7 text-foreground dark:prose-invert"
        />
      </div>
    </details>
  )
}

function isBashExecOperation(block: Extract<StudioTurnBlock, { kind: 'operation' }>) {
  const identity = deriveMcpIdentity(
    block.item.toolName,
    block.item.mcpServer,
    block.item.mcpTool
  )
  return identity.server === 'bash_exec'
}

function StudioOperationBlock({
  questId,
  block,
  isLatestOperation,
}: {
  questId: string
  block: Extract<StudioTurnBlock, { kind: 'operation' }>
  isLatestOperation: boolean
}) {
  if (isBashExecOperation(block)) {
    return (
      <QuestBashExecOperation
        questId={questId}
        itemId={block.item.id}
        toolCallId={block.item.toolCallId}
        toolName={block.item.toolName}
        label={block.item.label}
        status={block.item.status}
        args={block.item.args}
        output={block.item.output}
        createdAt={block.item.createdAt}
        metadata={block.item.metadata}
        comment={block.item.comment}
        monitorPlanSeconds={block.item.monitorPlanSeconds}
        monitorStepIndex={block.item.monitorStepIndex}
        nextCheckAfterSeconds={block.item.nextCheckAfterSeconds}
        isLatest={isLatestOperation}
        expandBehavior="latest_only"
      />
    )
  }
  return <StudioToolCard item={block.item} isLatest={isLatestOperation} />
}

function StudioArtifactBlock({ block }: { block: Extract<StudioTurnBlock, { kind: 'artifact' }> }) {
  const item = block.item
  const detailEntries = Object.entries(item.details ?? {}).filter(([, value]) => value != null && value !== '')

  return (
    <div className="min-w-0 overflow-hidden rounded-[24px] border border-black/[0.06] bg-[rgba(159,177,194,0.14)] px-4 py-3 dark:border-white/[0.08] dark:bg-white/[0.05]">
      <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
        <span className="font-medium text-foreground">{item.kind}</span>
        {item.status ? <Badge>{item.status}</Badge> : null}
        {item.flowType ? <Badge>{item.flowType}</Badge> : null}
        {item.createdAt ? <span className="ml-auto">{formatTime(item.createdAt)}</span> : null}
      </div>

      <div className="mt-2 break-words text-sm leading-7 text-foreground [overflow-wrap:anywhere]">
        {item.content}
      </div>

      {item.reason ? (
        <div className="mt-2 break-words text-xs leading-6 text-muted-foreground [overflow-wrap:anywhere]">
          <span className="font-medium text-foreground">Reason.</span> {item.reason}
        </div>
      ) : null}

      {item.guidance ? (
        <div className="mt-1 break-words text-xs leading-6 text-muted-foreground [overflow-wrap:anywhere]">
          <span className="font-medium text-foreground">Next.</span> {item.guidance}
        </div>
      ) : null}

      {item.comment ? <AgentCommentBlock comment={item.comment} className="mt-3" /> : null}

      {detailEntries.length > 0 ? (
        <div className="mt-3 rounded-[18px] border border-black/[0.05] bg-white/[0.70] px-3 py-3 text-xs leading-6 text-muted-foreground dark:border-white/[0.06] dark:bg-white/[0.03]">
          <div className="font-medium text-foreground">Details</div>
          <div className="mt-1 space-y-1">
            {detailEntries.slice(0, 8).map(([key, value]) => (
              <div key={key} className="break-words [overflow-wrap:anywhere]">
                <span className="font-medium text-foreground">{key}:</span>{' '}
                {typeof value === 'string' ? value : JSON.stringify(value)}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}

function StudioEventBlock({ block }: { block: Extract<StudioTurnBlock, { kind: 'event' }> }) {
  const item = block.item
  return (
    <div className="mx-auto inline-flex max-w-full flex-wrap items-center gap-2 rounded-full border border-black/[0.06] bg-white/[0.82] px-3 py-1.5 text-xs text-muted-foreground dark:border-white/[0.08] dark:bg-white/[0.05]">
      <Sparkles className="h-3.5 w-3.5" />
      <span className="font-medium text-foreground">{item.label}</span>
      {item.content ? (
        <span className="min-w-0 break-words [overflow-wrap:anywhere]">{item.content}</span>
      ) : null}
    </div>
  )
}

function AssistantTurn({
  questId,
  turn,
  latestOperationId,
  latestAnimatedBlockId,
  streaming,
}: {
  questId: string
  turn: StudioTurn
  latestOperationId: string | null
  latestAnimatedBlockId: string | null
  streaming: boolean
}) {
  const hasStreamingMessage = turn.blocks.some(
    (block) =>
      (block.kind === 'message' || block.kind === 'reasoning') &&
      Boolean(block.item.stream)
  )

  return (
    <div className="flex min-w-0 items-start gap-3">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[18px] border border-black/10 bg-white/[0.90] dark:border-white/[0.12] dark:bg-white/[0.05]">
        <LogoIcon size={24} />
      </div>

      <div className="min-w-0 flex-1 space-y-3">
        <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
          <span className="font-medium text-foreground">@DeepScientist</span>
          {turn.skillId ? <Badge className="bg-black/[0.03] dark:bg-white/[0.04]">{turn.skillId}</Badge> : null}
          {hasStreamingMessage ? (
            <span className="inline-flex h-2 w-2 rounded-full bg-[#2F3437] animate-caret dark:bg-[#E7DFD2]" />
          ) : null}
          {turn.createdAt ? <span className="ml-auto">{formatTime(turn.createdAt)}</span> : null}
        </div>

        {turn.blocks.map((block) => {
          if (block.kind === 'message') {
            return (
              <StudioMessageBlock
                key={block.id}
                block={block}
                animateText={latestAnimatedBlockId === block.id && Boolean(streaming || block.item.stream)}
              />
            )
          }
          if (block.kind === 'reasoning') {
            return (
              <StudioReasoningBlock
                key={block.id}
                block={block}
                animateText={latestAnimatedBlockId === block.id && Boolean(streaming || block.item.stream)}
              />
            )
          }
          if (block.kind === 'operation') {
            return (
              <StudioOperationBlock
                key={block.id}
                questId={questId}
                block={block}
                isLatestOperation={Boolean(
                  latestOperationId &&
                    (block.item.toolCallId || block.item.renderId) === latestOperationId
                )}
              />
            )
          }
          if (block.kind === 'artifact') {
            return <StudioArtifactBlock key={block.id} block={block} />
          }
          return <StudioEventBlock key={block.id} block={block} />
        })}
      </div>
    </div>
  )
}

function UserTurn({ turn }: { turn: StudioTurn }) {
  const messageBlock = turn.blocks.find((block) => block.kind === 'message')
  if (!messageBlock || messageBlock.kind !== 'message') {
    return null
  }

  return (
    <div className="flex justify-end">
      <div className="flex min-w-0 max-w-[92%] items-start gap-3">
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex items-center justify-end gap-2 text-[11px] text-muted-foreground">
            {turn.createdAt ? <span>{formatTime(turn.createdAt)}</span> : null}
            <span className="font-medium text-foreground">You</span>
          </div>
          <div className="min-w-0 overflow-hidden rounded-[24px] bg-[#2F3437] px-4 py-3 text-sm leading-7 text-white shadow-[0_18px_42px_-34px_rgba(17,24,39,0.3)]">
            <div className="ds-copilot-markdown prose prose-sm max-w-none whitespace-pre-wrap break-words [overflow-wrap:anywhere] leading-7 text-white prose-invert">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{messageBlock.item.content || ''}</ReactMarkdown>
            </div>
          </div>
        </div>

        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[18px] border border-black/10 bg-white/[0.90] dark:border-white/[0.12] dark:bg-white/[0.05]">
          <User2 className="h-4 w-4" />
        </div>
      </div>
    </div>
  )
}

function SystemTurn({ turn }: { turn: StudioTurn }) {
  return (
    <div className="flex justify-center">
      <div className="space-y-2">
        {turn.blocks.map((block) => (
          <StudioEventBlock key={block.id} block={block as Extract<StudioTurnBlock, { kind: 'event' }>} />
        ))}
      </div>
    </div>
  )
}

export function QuestStudioDirectTimeline({
  questId,
  feed,
  loading,
  restoring,
  streaming,
  activeToolCount,
  connectionState,
  error,
  snapshot,
  hasOlderHistory = false,
  loadingOlderHistory = false,
  onLoadOlderHistory,
  emptyLabel = 'Copilot trace appears here.',
  bottomInset = 28,
}: QuestStudioDirectTimelineProps) {
  const turns = React.useMemo(() => buildStudioTurns(feed), [feed])
  const latestOperationId = React.useMemo(
    () => findLatestRenderedOperationId(mergeFeedItemsForRender(feed)),
    [feed]
  )
  const listRef = React.useRef<HTMLDivElement | null>(null)
  const contentRef = React.useRef<HTMLDivElement | null>(null)
  const prependAnchorRef = React.useRef<{ active: boolean; scrollHeight: number; scrollTop: number }>({
    active: false,
    scrollHeight: 0,
    scrollTop: 0,
  })
  const latestAnimatedBlockId = React.useMemo(() => {
    for (let turnIndex = turns.length - 1; turnIndex >= 0; turnIndex -= 1) {
      const turn = turns[turnIndex]
      if (turn.role !== 'assistant') continue
      for (let blockIndex = turn.blocks.length - 1; blockIndex >= 0; blockIndex -= 1) {
        const block = turn.blocks[blockIndex]
        if (
          (block.kind === 'message' || block.kind === 'reasoning') &&
          block.item.content.trim()
        ) {
          return block.id
        }
      }
    }
    return null
  }, [turns])
  const { isNearBottom } = useAutoFollowScroll({
    scrollRef: listRef,
    contentRef,
    deps: [turns.length, streaming, activeToolCount, latestOperationId],
  })

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
  }, [loadingOlderHistory, turns.length])

  return (
    <div className="flex min-h-0 flex-1 flex-col px-4 pt-4">
      <ChatScrollProvider value={{ isNearBottom }}>
        <div
          ref={listRef}
          className="feed-scrollbar flex min-h-0 flex-1 flex-col gap-4 overflow-x-hidden overflow-y-auto pr-1"
          style={{ paddingBottom: bottomInset }}
          onWheel={(event) => {
            const root = listRef.current
            if (!root || event.deltaY >= 0 || root.scrollTop > 24) {
              return
            }
            void handleLoadOlderHistory()
          }}
        >
          <div ref={contentRef} className="flex min-w-0 flex-col gap-4">
            {hasOlderHistory ? (
              <div className="flex justify-center">
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
            {turns.length === 0 ? (
              <EmptyState
                loading={loading}
                restoring={restoring}
                connectionState={connectionState}
                emptyLabel={emptyLabel}
              />
            ) : (
              turns.map((turn) => {
                if (turn.role === 'user') {
                  return <UserTurn key={turn.id} turn={turn} />
                }
                if (turn.role === 'system') {
                  return <SystemTurn key={turn.id} turn={turn} />
                }
                return (
                  <AssistantTurn
                    key={turn.id}
                    questId={questId}
                    turn={turn}
                    latestOperationId={latestOperationId}
                    latestAnimatedBlockId={latestAnimatedBlockId}
                    streaming={streaming}
                  />
                )
              })
            )}
          </div>
        </div>
      </ChatScrollProvider>
    </div>
  )
}

export default QuestStudioDirectTimeline
