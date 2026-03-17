'use client'

import { useEffect, useMemo, useRef, useState } from 'react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { client } from '@/lib/api'
import { useI18n } from '@/lib/i18n'
import type { SystemUpdateStatus } from '@/types'

const COPY = {
  zh: {
    title: '发现新版本',
    body: 'DeepScientist 检测到新的 npm 版本。你可以现在更新，或稍后再提醒。',
    current: '当前版本',
    latest: '最新版本',
    auto: '自动更新',
    supported: '可用',
    manualOnly: '需要手动更新',
    updateNow: '立即更新',
    later: '稍后提醒',
    skip: '跳过此版本',
    updating: '正在更新 DeepScientist，并准备重启本地 daemon。',
    updated: '更新已经完成。',
    reload: '刷新页面',
    close: '关闭',
    manual: '手动更新命令',
    checkError: '更新检查失败',
  },
  en: {
    title: 'Update Available',
    body: 'DeepScientist found a newer npm release. You can update now or be reminded later.',
    current: 'Current version',
    latest: 'Latest version',
    auto: 'Self-update',
    supported: 'Available',
    manualOnly: 'Manual only',
    updateNow: 'Update now',
    later: 'Later',
    skip: 'Skip this version',
    updating: 'DeepScientist is updating and preparing to restart the local daemon.',
    updated: 'The update has completed.',
    reload: 'Reload page',
    close: 'Close',
    manual: 'Manual update command',
    checkError: 'Update check failed',
  },
} as const

export function UpdateReminderDialog() {
  const { locale } = useI18n()
  const t = COPY[locale]
  const [status, setStatus] = useState<SystemUpdateStatus | null>(null)
  const [open, setOpen] = useState(false)
  const [loadingAction, setLoadingAction] = useState<'install' | 'later' | 'skip' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [trackUpdateFlow, setTrackUpdateFlow] = useState(false)
  const reloadTimerRef = useRef<number | null>(null)

  const showResult = useMemo(() => {
    if (!status || status.busy) {
      return false
    }
    return trackUpdateFlow && Boolean(status.last_update_result)
  }, [status, trackUpdateFlow])

  const loadStatus = async (initial = false) => {
    try {
      const payload = await client.systemUpdateStatus()
      setStatus(payload)
      setError(null)
      if (payload.busy) {
        setTrackUpdateFlow(true)
        setOpen(true)
        return
      }
      if (payload.prompt_recommended) {
        setOpen(true)
        return
      }
      if (initial && !trackUpdateFlow) {
        setOpen(false)
      }
    } catch (caught) {
      if (initial) {
        setOpen(false)
      }
      setError(caught instanceof Error ? caught.message : 'Failed to load update status.')
    }
  }

  useEffect(() => {
    void loadStatus(true)
    return () => {
      if (reloadTimerRef.current !== null) {
        window.clearTimeout(reloadTimerRef.current)
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!trackUpdateFlow || !status?.busy) {
      return
    }
    const timer = window.setInterval(() => {
      void loadStatus()
    }, 3000)
    return () => window.clearInterval(timer)
  }, [status?.busy, trackUpdateFlow])

  useEffect(() => {
    if (!showResult || !status?.last_update_result?.ok || status.current_version !== status.latest_version) {
      return
    }
    reloadTimerRef.current = window.setTimeout(() => {
      window.location.reload()
    }, 1800)
    return () => {
      if (reloadTimerRef.current !== null) {
        window.clearTimeout(reloadTimerRef.current)
      }
    }
  }, [showResult, status])

  const handleAction = async (action: 'install_latest' | 'remind_later' | 'skip_version') => {
    setLoadingAction(action === 'install_latest' ? 'install' : action === 'remind_later' ? 'later' : 'skip')
    setError(null)
    try {
      await client.systemUpdateAction(action)
      if (action === 'install_latest') {
        setTrackUpdateFlow(true)
        setOpen(true)
        await loadStatus()
      } else {
        setOpen(false)
        await loadStatus()
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Update request failed.')
    } finally {
      setLoadingAction(null)
    }
  }

  const message = status?.last_update_result?.message || null
  const updateSucceeded = Boolean(status?.last_update_result?.ok)

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-lg border-black/10 bg-[#F6F1E8] text-[#2D2A26]">
        <DialogHeader className="space-y-3 text-left">
          <DialogTitle className="text-[20px] font-semibold text-[#2D2A26]">{t.title}</DialogTitle>
          <DialogDescription className="text-sm leading-6 text-[#5D5A55]">
            {status?.busy ? t.updating : showResult ? message || t.updated : t.body}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 rounded-[22px] border border-black/8 bg-white/75 p-4">
          <div className="flex items-center justify-between text-sm">
            <span className="text-[#7E8B97]">{t.current}</span>
            <span className="font-medium text-[#2D2A26]">{status?.current_version || '...'}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-[#7E8B97]">{t.latest}</span>
            <span className="font-medium text-[#2D2A26]">{status?.latest_version || '...'}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-[#7E8B97]">{t.auto}</span>
            <span className="font-medium text-[#2D2A26]">
              {status?.can_self_update ? t.supported : t.manualOnly}
            </span>
          </div>
          {status?.can_self_update === false && status?.manual_update_command ? (
            <div className="space-y-1 pt-1">
              <div className="text-xs uppercase tracking-[0.18em] text-[#9AA5AF]">{t.manual}</div>
              <div className="rounded-2xl bg-[#201A16] px-3 py-2 font-mono text-xs text-[#F8F4EE]">
                {status.manual_update_command}
              </div>
            </div>
          ) : null}
          {status?.last_check_error ? (
            <div className="rounded-2xl border border-[#D8B9AE] bg-[#FFF3EF] px-3 py-2 text-sm text-[#8A4B37]">
              {t.checkError}: {status.last_check_error}
            </div>
          ) : null}
          {error ? (
            <div className="rounded-2xl border border-[#D8B9AE] bg-[#FFF3EF] px-3 py-2 text-sm text-[#8A4B37]">
              {error}
            </div>
          ) : null}
        </div>

        <DialogFooter className="mt-2 gap-2 sm:justify-end">
          {showResult ? (
            <>
              <Button variant="outline" className="border-black/12 bg-white/70 text-[#2D2A26]" onClick={() => setOpen(false)}>
                {t.close}
              </Button>
              {updateSucceeded ? (
                <Button className="bg-[#C7AD96] text-[#2D2A26] hover:bg-[#D7C6AE]" onClick={() => window.location.reload()}>
                  {t.reload}
                </Button>
              ) : null}
            </>
          ) : status?.busy ? (
            <Button className="bg-[#C7AD96] text-[#2D2A26] hover:bg-[#D7C6AE]" disabled>
              {t.updating}
            </Button>
          ) : (
            <>
              <Button
                variant="outline"
                className="border-black/12 bg-white/70 text-[#2D2A26]"
                onClick={() => void handleAction('remind_later')}
                disabled={loadingAction !== null}
              >
                {t.later}
              </Button>
              <Button
                variant="outline"
                className="border-black/12 bg-white/70 text-[#2D2A26]"
                onClick={() => void handleAction('skip_version')}
                disabled={loadingAction !== null}
              >
                {t.skip}
              </Button>
              <Button
                className="bg-[#C7AD96] text-[#2D2A26] hover:bg-[#D7C6AE]"
                onClick={() => void handleAction('install_latest')}
                disabled={loadingAction !== null}
              >
                {t.updateNow}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
