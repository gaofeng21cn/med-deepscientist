import * as React from 'react'
import { ArrowUpRight, Sparkles } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import type { BenchSetupPacket } from '@/lib/types/benchstore'

type SetupAgentRailProps = {
  locale: 'en' | 'zh'
  setupPacket?: BenchSetupPacket | null
  loading?: boolean
  error?: string | null
  assistantLabel?: string | null
  onStartAssist: (message: string) => Promise<void> | void
}

function copy(locale: 'en' | 'zh') {
  return locale === 'zh'
    ? {
        title: 'SetupAgent',
        intro:
          '你可以直接编辑左侧表单并创建项目。如果你想让我继续帮你整理，我会启动真实后端助手，把建议直接写回左侧表单。',
        benchmarkIntro:
          '这个 benchmark 已经带来了一版草案。你可以继续启动后端 SetupAgent，让它结合 benchmark 信息和当前设备继续整理表单。',
        placeholder: '请先按当前 benchmark 和机器条件，帮我把启动表单整理完整。',
        cta: '启动协助',
        note: '启动后，右侧会切到实时后端协助视图，表单 patch 会自动回写到左侧。',
      }
    : {
        title: 'SetupAgent',
        intro:
          'You can edit the form on the left and create the project directly. If you want help, I can start a real backend assistant and write its suggestions back into the form.',
        benchmarkIntro:
          'This benchmark already comes with a draft. Start the backend SetupAgent to keep refining the launch form from the benchmark context and this machine.',
        placeholder: 'Please refine this launch form based on the selected benchmark and this machine.',
        cta: 'Start Assist',
        note: 'Once started, the right side switches to a live backend assistant and form patches flow back into the left form.',
      }
}

export function SetupAgentRail(props: SetupAgentRailProps) {
  const t = copy(props.locale)
  const [input, setInput] = React.useState('')

  const handleStart = React.useCallback(async () => {
    const fallback =
      props.locale === 'zh'
        ? '请根据当前 benchmark 和左侧表单，帮我整理并补齐最关键的启动信息。'
        : 'Please use the current benchmark and form to complete the most important launch details.'
    await props.onStartAssist(input.trim() || fallback)
  }, [input, props])

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-[24px] border border-[rgba(45,42,38,0.09)] bg-[rgba(255,255,255,0.78)] shadow-[0_24px_70px_-54px_rgba(45,42,38,0.34)] backdrop-blur-xl">
      <div className="flex shrink-0 items-center justify-between gap-3 border-b border-[rgba(45,42,38,0.09)] px-4 py-3">
        <div>
          <div className="text-sm font-semibold text-[rgba(38,36,33,0.95)]">{t.title}</div>
          <div className="mt-1 text-xs text-[rgba(107,103,97,0.78)]">
            {props.setupPacket?.assistant_label || props.assistantLabel || t.title}
          </div>
        </div>
        <div className="inline-flex items-center gap-2 rounded-full border border-[rgba(45,42,38,0.09)] bg-[rgba(244,239,233,0.7)] px-3 py-1 text-[11px] text-[rgba(86,82,77,0.88)]">
          <Sparkles className="h-3.5 w-3.5" />
          {props.locale === 'zh' ? '待命中' : 'Standby'}
        </div>
      </div>

      <div className="feed-scrollbar min-h-0 flex-1 overflow-y-auto px-4 py-4">
        <div className="space-y-4 pr-1">
          <div className="rounded-[18px] border border-[rgba(45,42,38,0.09)] bg-[rgba(244,239,233,0.62)] px-4 py-3 text-sm leading-7 text-[rgba(56,52,47,0.92)]">
            {props.setupPacket ? t.benchmarkIntro : t.intro}
          </div>
        </div>
      </div>

      <div className="shrink-0 border-t border-[rgba(45,42,38,0.09)] px-4 py-4">
        <div className="space-y-3">
          <Textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder={t.placeholder}
            className="min-h-[140px] rounded-[16px] border-[rgba(45,42,38,0.09)] bg-white/82 text-sm leading-6 text-[rgba(38,36,33,0.95)]"
          />
          <div className="text-xs text-[rgba(107,103,97,0.78)]">{t.note}</div>
          {props.error ? <div className="text-sm text-[#9a1b1b]">{props.error}</div> : null}
        </div>
        <div className="mt-3 flex justify-end">
          <Button onClick={() => void handleStart()} isLoading={props.loading} className="rounded-full">
            <ArrowUpRight className="h-4 w-4" />
            {t.cta}
          </Button>
        </div>
      </div>
    </div>
  )
}

export default SetupAgentRail
