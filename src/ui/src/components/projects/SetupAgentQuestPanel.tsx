import * as React from 'react'
import { Sparkles } from 'lucide-react'

import { QuestCopilotDockPanel } from '@/components/workspace/QuestCopilotDockPanel'
import { useQuestWorkspace } from '@/lib/acp'

function resolveSetupAgentBadge(args: {
  locale: 'en' | 'zh'
  loading: boolean
  hasLiveRun: boolean
  streaming: boolean
  activeToolCount: number
  runtimeStatus?: string | null
}) {
  const { locale, loading, hasLiveRun, streaming, activeToolCount, runtimeStatus } = args
  const normalizedStatus = String(runtimeStatus || '').trim().toLowerCase()
  if (loading) return locale === 'zh' ? '加载中' : 'Loading'
  if (hasLiveRun || streaming || activeToolCount > 0 || normalizedStatus === 'running' || normalizedStatus === 'retrying') {
    return locale === 'zh' ? '运行中' : 'Running'
  }
  if (normalizedStatus === 'waiting_for_user' || normalizedStatus === 'waiting' || normalizedStatus === 'paused') {
    return locale === 'zh' ? '等待确认' : 'Waiting'
  }
  return locale === 'zh' ? '已停驻' : 'Idle'
}

export function SetupAgentQuestPanel({
  questId,
  locale,
}: {
  questId: string
  locale: 'en' | 'zh'
}) {
  const workspace = useQuestWorkspace(questId)
  const badge = resolveSetupAgentBadge({
    locale,
    loading: workspace.loading,
    hasLiveRun: workspace.hasLiveRun,
    streaming: workspace.streaming,
    activeToolCount: workspace.activeToolCount,
    runtimeStatus: String(workspace.snapshot?.runtime_status || workspace.snapshot?.status || ''),
  })

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-[24px] border border-[rgba(45,42,38,0.09)] bg-[rgba(255,255,255,0.78)] shadow-[0_24px_70px_-54px_rgba(45,42,38,0.34)] backdrop-blur-xl">
      <div className="flex shrink-0 items-center justify-between gap-3 border-b border-[rgba(45,42,38,0.09)] px-4 py-3">
        <div>
          <div className="text-sm font-semibold text-[rgba(38,36,33,0.95)]">SetupAgent</div>
          <div className="mt-1 text-xs text-[rgba(107,103,97,0.78)]">
            {locale === 'zh' ? '实时后端协助' : 'Realtime backend assist'}
          </div>
        </div>
        <div className="inline-flex items-center gap-2 rounded-full border border-[rgba(45,42,38,0.09)] bg-[rgba(244,239,233,0.7)] px-3 py-1 text-[11px] text-[rgba(86,82,77,0.88)]">
          <Sparkles className="h-3.5 w-3.5" />
          {badge}
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-hidden">
        <QuestCopilotDockPanel questId={questId} title="SetupAgent" workspace={workspace} />
      </div>
    </div>
  )
}

export default SetupAgentQuestPanel
