import { ArrowUpRight, CheckCircle2, Loader2, Search, Sparkles } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Modal, ModalFooter } from '@/components/ui/modal'
import { client } from '@/lib/api'
import { cn } from '@/lib/utils'
import type { Locale, OpenDocumentPayload } from '@/types'

const REGISTER_URL = 'https://data.rag.ac.cn/register'

type DeepXivDraft = {
  base_url: string
  token: string
  token_env: string
  default_result_size: string
  preview_characters: string
  request_timeout_seconds: string
}

type DeepXivTestResult = {
  ok?: boolean
  summary?: string
  warnings?: string[]
  errors?: string[]
  details?: Record<string, unknown>
  results?: Array<Record<string, unknown>>
  preview?: string
}

const DEFAULT_DRAFT: DeepXivDraft = {
  base_url: 'https://data.rag.ac.cn',
  token: '',
  token_env: 'DEEPXIV_TOKEN',
  default_result_size: '20',
  preview_characters: '5000',
  request_timeout_seconds: '90',
}

const copy = {
  en: {
    title: 'DeepXiv setup',
    description:
      'Register, set the DeepXiv base URL, direct token, or env-only token lookup, then preview a live `transformers` retrieval.',
    eyebrow: 'Literature provider',
    stepLabel: 'Step',
    step1Title: 'Configure access',
    step1Body: 'Open the official register page, then configure the DeepXiv base URL and credential path.',
    step2Title: 'Confirm the defaults',
    step2Body: 'Saving this form will automatically enable DeepXiv. No extra toggle is required.',
    step3Title: 'Test and preview',
    step3Body:
      'Run a live DeepXiv search for `transformers`. The preview panel on the right shows the returned content from the configured base URL and credential path before you save.',
    baseUrlLabel: 'Base URL',
    baseUrlPlaceholder: 'https://data.rag.ac.cn',
    tokenLabel: 'Direct token',
    tokenPlaceholder: 'Paste the DeepXiv token',
    tokenEnvLabel: 'Token env var',
    tokenEnvPlaceholder: 'DEEPXIV_TOKEN',
    credentialHint: 'Use a direct token or provide an env var name for env-only auth.',
    openRegister: 'Open register page',
    next: 'Next',
    back: 'Back',
    close: 'Close',
    save: 'Save config',
    saving: 'Saving…',
    test: 'Test `transformers`',
    testing: 'Testing…',
    defaultsHint: 'DeepXiv will be enabled automatically after saving.',
    resultSize: 'Retrieve size',
    previewChars: 'Preview characters',
    timeout: 'Timeout (s)',
    previewTitle: 'Preview',
    previewEmpty: 'The preview panel will show the DeepXiv response after you run the Step 3 test.',
    tokenOrEnvRequired: 'Fill in a DeepXiv token or token environment variable before continuing.',
    searchKeyword: 'Search keyword',
    searchKeywordValue: 'transformers',
    saveHint: 'The setup flow writes directly into `config.literature.deepxiv`. Direct token and `token_env` are both supported.',
    loading: 'Loading DeepXiv config...',
  },
  zh: {
    title: 'DeepXiv 配置',
    description: '完成注册后，可以显式设置 base_url、直接 token 或 env-only token lookup，然后预览一次 `transformers` 的实时检索结果。',
    eyebrow: '文献能力提供方',
    stepLabel: 'Step',
    step1Title: '配置访问方式',
    step1Body: '先打开官方注册页，然后在这里设置 DeepXiv 的 base_url 和凭据来源。',
    step2Title: '确认默认值',
    step2Body: '保存后会自动启用 DeepXiv，这里只确认默认参数。',
    step3Title: '测试与预览',
    step3Body: '这里会用 `transformers` 做一次真实 DeepXiv 检索，右侧预览框会显示当前 base_url 和凭据路径返回的内容，然后再决定是否保存。',
    baseUrlLabel: 'Base URL',
    baseUrlPlaceholder: 'https://data.rag.ac.cn',
    tokenLabel: '直接 Token',
    tokenPlaceholder: '填写 DeepXiv token',
    tokenEnvLabel: 'Token 环境变量',
    tokenEnvPlaceholder: 'DEEPXIV_TOKEN',
    credentialHint: '可以直接填写 token，也可以只填写环境变量名走 env-only 鉴权。',
    openRegister: '打开注册页',
    next: '下一步',
    back: '上一步',
    close: '关闭',
    save: '保存配置',
    saving: '保存中…',
    test: '测试 `transformers`',
    testing: '测试中…',
    defaultsHint: '保存后会自动启用 DeepXiv。',
    resultSize: '检索数量',
    previewChars: '预览字符',
    timeout: '超时（秒）',
    previewTitle: '预览',
    previewEmpty: '执行第三步测试后，这里会显示 DeepXiv 返回的内容。',
    tokenOrEnvRequired: '请填写 DeepXiv token 或 token_env 环境变量名。',
    searchKeyword: '检索关键词',
    searchKeywordValue: 'transformers',
    saveHint: '这个向导会直接写入 `config.literature.deepxiv`，同时支持直接 token 和 `token_env`。',
    loading: '正在加载 DeepXiv 配置...',
  },
} satisfies Record<Locale, Record<string, string>>

function asObject(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function normalizePositiveInteger(value: string, fallback: number) {
  const parsed = Number.parseInt(value, 10)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback
}

function buildDraft(document: OpenDocumentPayload | null): DeepXivDraft {
  const structured =
    document?.meta?.structured_config && typeof document.meta.structured_config === 'object'
      ? (document.meta.structured_config as Record<string, unknown>)
      : {}
  const literature = asObject(structured.literature)
  const deepxiv = asObject(literature.deepxiv)
  return {
    base_url: typeof deepxiv.base_url === 'string' && deepxiv.base_url.trim() ? deepxiv.base_url : DEFAULT_DRAFT.base_url,
    token: typeof deepxiv.token === 'string' ? deepxiv.token : DEFAULT_DRAFT.token,
    token_env: Object.prototype.hasOwnProperty.call(deepxiv, 'token_env')
      ? typeof deepxiv.token_env === 'string'
        ? deepxiv.token_env
        : ''
      : DEFAULT_DRAFT.token_env,
    default_result_size: String(deepxiv.default_result_size ?? DEFAULT_DRAFT.default_result_size),
    preview_characters: String(deepxiv.preview_characters ?? DEFAULT_DRAFT.preview_characters),
    request_timeout_seconds: String(deepxiv.request_timeout_seconds ?? DEFAULT_DRAFT.request_timeout_seconds),
  }
}

function mergeDraft(document: OpenDocumentPayload | null, draft: DeepXivDraft) {
  const structured =
    document?.meta?.structured_config && typeof document.meta.structured_config === 'object'
      ? ({ ...(document.meta.structured_config as Record<string, unknown>) })
      : {}
  const literature = { ...asObject(structured.literature) }
  const previous = asObject(literature.deepxiv)
  literature.deepxiv = {
    ...previous,
    enabled: true,
    base_url: draft.base_url.trim() || DEFAULT_DRAFT.base_url,
    token: draft.token.trim() || null,
    token_env: draft.token_env.trim() || null,
    default_result_size: normalizePositiveInteger(draft.default_result_size, 20),
    preview_characters: normalizePositiveInteger(draft.preview_characters, 5000),
    request_timeout_seconds: normalizePositiveInteger(draft.request_timeout_seconds, 90),
  }
  structured.literature = literature
  return structured
}

function buildPreviewText(result: DeepXivTestResult | null, empty: string) {
  if (!result) {
    return empty
  }
  if (typeof result.preview === 'string' && result.preview.trim()) {
    return result.preview.trim()
  }
  if (Array.isArray(result.results) && result.results.length > 0) {
    return JSON.stringify(result.results, null, 2)
  }
  if (result.details && Object.keys(result.details).length > 0) {
    return JSON.stringify(result.details, null, 2)
  }
  const lines = [result.summary || '', ...(result.errors || []), ...(result.warnings || [])].filter(Boolean)
  return lines.join('\n') || empty
}

function StepBadge({ active, done, label }: { active: boolean; done: boolean; label: string }) {
  return (
    <div
      className={cn(
        'inline-flex items-center rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em]',
        active ? 'bg-[#2f2b27] text-white' : done ? 'bg-emerald-100 text-emerald-700' : 'bg-[#f1ece5] text-[#8a8176]'
      )}
    >
      {label}
    </div>
  )
}

export function DeepXivSetupDialog({
  open,
  onClose,
  onSaved,
  locale,
}: {
  open: boolean
  onClose: () => void
  onSaved?: (payload: { structured: Record<string, unknown>; revision?: string }) => void
  locale: Locale
}) {
  const t = copy[locale]
  const [document, setDocument] = useState<OpenDocumentPayload | null>(null)
  const [draft, setDraft] = useState<DeepXivDraft>(DEFAULT_DRAFT)
  const [step, setStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const [testing, setTesting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [testResult, setTestResult] = useState<DeepXivTestResult | null>(null)

  useEffect(() => {
    if (!open) {
      return
    }
    let active = true
    const load = async () => {
      setLoading(true)
      setError('')
      setTestResult(null)
      setStep(0)
      try {
        const next = await client.configDocument('config')
        if (!active) {
          return
        }
        setDocument(next)
        setDraft(buildDraft(next))
      } catch (loadError) {
        if (!active) {
          return
        }
        setError(loadError instanceof Error ? loadError.message : String(loadError || 'Failed to load config.'))
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }
    void load()
    return () => {
      active = false
    }
  }, [open])

  const previewText = useMemo(() => buildPreviewText(testResult, t.previewEmpty), [t.previewEmpty, testResult])

  const handleField = (key: keyof DeepXivDraft, value: string) => {
    setDraft((current) => ({ ...current, [key]: value }))
    setError('')
  }

  const requireCredential = () => {
    if (draft.token.trim() || draft.token_env.trim()) {
      return true
    }
    setError(t.tokenOrEnvRequired)
    return false
  }

  const handleNext = () => {
    if (step === 0 && !requireCredential()) {
      return
    }
    setError('')
    setStep((current) => Math.min(current + 1, 2))
  }

  const handleTest = async () => {
    if (!requireCredential()) {
      return
    }
    const nextStructuredDraft = mergeDraft(document, draft)
    setTesting(true)
    setError('')
    try {
      const result = await client.deepxivTest(nextStructuredDraft)
      setTestResult(result)
      if (!result.ok) {
        setError([...(result.errors || []), result.summary || ''].filter(Boolean).join('\n'))
      }
    } catch (testError) {
      setError(testError instanceof Error ? testError.message : String(testError || 'DeepXiv test failed.'))
      setTestResult(null)
    } finally {
      setTesting(false)
    }
  }

  const handleSave = async () => {
    if (!document || !requireCredential()) {
      return
    }
    const nextStructuredDraft = mergeDraft(document, draft)
    setSaving(true)
    setError('')
    try {
      const result = await client.saveConfig('config', {
        structured: nextStructuredDraft,
        revision: document.revision,
      })
      if (!result.ok) {
        setError(result.message || '')
        return
      }
      setDocument((current) =>
        current
          ? {
              ...current,
              revision: result.revision || current.revision,
              meta: {
                ...(current.meta || {}),
                structured_config: nextStructuredDraft,
              },
            }
          : current
      )
      onSaved?.({ structured: nextStructuredDraft, revision: result.revision || document.revision })
      onClose()
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : String(saveError || 'Failed to save config.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={t.title}
      description={t.description}
      size="xl"
      className="w-full max-w-[min(1180px,96vw)]"
    >
      <div className="space-y-5" data-onboarding-id="deepxiv-setup-dialog">
        <section className="rounded-[24px] border border-[rgba(45,42,38,0.08)] bg-[linear-gradient(145deg,rgba(253,247,241,0.94),rgba(239,229,220,0.84)_42%,rgba(226,235,239,0.82))] px-5 py-5 shadow-[0_24px_80px_-60px_rgba(44,39,34,0.4)]">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary" className="rounded-full bg-white/75 px-3 py-1 text-[11px] font-semibold text-[#4f4a43]">
              DeepXiv
            </Badge>
            <div className="inline-flex items-center gap-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f8578]">
              <Sparkles className="h-3.5 w-3.5" />
              {t.eyebrow}
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {[0, 1, 2].map((index) => (
              <StepBadge key={index} active={step === index} done={step > index} label={`${t.stepLabel} ${index + 1}`} />
            ))}
          </div>
        </section>

        {loading ? (
          <div className="flex items-center gap-3 rounded-[20px] border border-[rgba(45,42,38,0.08)] bg-white px-5 py-6 text-sm text-[#5d5953]">
            <Loader2 className="h-4 w-4 animate-spin" />
            {t.loading}
          </div>
        ) : (
          <div className={cn('grid gap-5', step === 2 ? 'xl:grid-cols-[minmax(0,0.95fr)_minmax(360px,1.05fr)]' : '')}>
            <section className="rounded-[24px] border border-[rgba(45,42,38,0.08)] bg-[rgba(255,250,245,0.84)] px-5 py-5 shadow-[0_18px_60px_-48px_rgba(44,39,34,0.3)]">
              <div className="text-lg font-semibold text-[#2f2b27]">
                {step === 0 ? t.step1Title : step === 1 ? t.step2Title : t.step3Title}
              </div>
              <div className="mt-2 text-sm leading-7 text-[#5d5953]">
                {step === 0 ? t.step1Body : step === 1 ? t.step2Body : t.step3Body}
              </div>

              {step === 0 ? (
                <div className="mt-5 space-y-4">
                  <Button
                    variant="outline"
                    className="gap-2 rounded-full"
                    onClick={() => window.open(REGISTER_URL, '_blank', 'noopener,noreferrer')}
                  >
                    {t.openRegister}
                    <ArrowUpRight className="h-4 w-4" />
                  </Button>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2 sm:col-span-2">
                      <div className="text-sm font-medium text-[#2f2b27]">{t.baseUrlLabel}</div>
                      <Input
                        value={draft.base_url}
                        onChange={(event) => handleField('base_url', event.target.value)}
                        placeholder={t.baseUrlPlaceholder}
                        className="rounded-[14px] border-black/[0.08] bg-white/80"
                      />
                    </div>
                    <div className="space-y-2">
                      <div className="text-sm font-medium text-[#2f2b27]">{t.tokenLabel}</div>
                      <Input
                        type="password"
                        value={draft.token}
                        onChange={(event) => handleField('token', event.target.value)}
                        placeholder={t.tokenPlaceholder}
                        className="rounded-[14px] border-black/[0.08] bg-white/80"
                      />
                    </div>
                    <div className="space-y-2">
                      <div className="text-sm font-medium text-[#2f2b27]">{t.tokenEnvLabel}</div>
                      <Input
                        value={draft.token_env}
                        onChange={(event) => handleField('token_env', event.target.value)}
                        placeholder={t.tokenEnvPlaceholder}
                        className="rounded-[14px] border-black/[0.08] bg-white/80"
                      />
                    </div>
                  </div>
                  <div className="rounded-[16px] border border-black/[0.08] bg-white/78 px-4 py-3 text-sm leading-7 text-[#5d5953]">
                    {t.credentialHint}
                  </div>
                </div>
              ) : null}

              {step === 1 ? (
                <div className="mt-5 space-y-4">
                  <div className="rounded-[16px] border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                    {t.defaultsHint}
                  </div>
                  <div className="grid gap-4 sm:grid-cols-3">
                    <div className="space-y-2">
                      <div className="text-sm font-medium text-[#2f2b27]">{t.resultSize}</div>
                      <Input
                        type="number"
                        inputMode="numeric"
                        value={draft.default_result_size}
                        onChange={(event) => handleField('default_result_size', event.target.value)}
                        className="rounded-[14px] border-black/[0.08] bg-white/80"
                      />
                    </div>
                    <div className="space-y-2">
                      <div className="text-sm font-medium text-[#2f2b27]">{t.previewChars}</div>
                      <Input
                        type="number"
                        inputMode="numeric"
                        value={draft.preview_characters}
                        onChange={(event) => handleField('preview_characters', event.target.value)}
                        className="rounded-[14px] border-black/[0.08] bg-white/80"
                      />
                    </div>
                    <div className="space-y-2">
                      <div className="text-sm font-medium text-[#2f2b27]">{t.timeout}</div>
                      <Input
                        type="number"
                        inputMode="numeric"
                        value={draft.request_timeout_seconds}
                        onChange={(event) => handleField('request_timeout_seconds', event.target.value)}
                        className="rounded-[14px] border-black/[0.08] bg-white/80"
                      />
                    </div>
                  </div>
                </div>
              ) : null}

              {step === 2 ? (
                <div className="mt-5 space-y-4">
                  <div className="rounded-[16px] border border-black/[0.08] bg-white/78 px-4 py-4 text-sm leading-7 text-[#4f4a43]">
                    <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-[#8f8578]">
                      <Search className="h-3.5 w-3.5" />
                      {t.searchKeyword}
                    </div>
                    <div className="mt-2 font-medium text-[#2f2b27]">{t.searchKeywordValue}</div>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <Button variant="outline" className="gap-2 rounded-full" onClick={() => void handleTest()} isLoading={testing}>
                      <Search className="h-4 w-4" />
                      {testing ? t.testing : t.test}
                    </Button>
                    <Button className="gap-2 rounded-full" onClick={() => void handleSave()} isLoading={saving}>
                      <CheckCircle2 className="h-4 w-4" />
                      {saving ? t.saving : t.save}
                    </Button>
                  </div>
                  <div className="text-sm leading-7 text-[#5d5953]">{t.saveHint}</div>
                  {testResult?.summary ? (
                    <div
                      className={cn(
                        'rounded-[16px] border px-4 py-3 text-sm leading-7',
                        testResult.ok ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-amber-200 bg-amber-50 text-amber-700'
                      )}
                    >
                      {testResult.summary}
                    </div>
                  ) : null}
                </div>
              ) : null}

              {error ? <div className="mt-4 whitespace-pre-wrap text-sm text-[#a01818]">{error}</div> : null}
            </section>

            {step === 2 ? (
              <aside className="rounded-[24px] border border-[rgba(45,42,38,0.08)] bg-[rgba(22,26,31,0.94)] px-5 py-5 shadow-[0_20px_70px_-56px_rgba(14,18,24,0.58)]">
                <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-white/55">{t.previewTitle}</div>
                <pre
                  className="mt-4 min-h-[360px] max-h-[min(62vh,720px)] overflow-x-auto overflow-y-auto whitespace-pre-wrap break-words rounded-[16px] border border-white/10 bg-black/20 px-4 py-4 text-[12px] leading-[1.75] text-white"
                  style={{ WebkitTextFillColor: '#ffffff' }}
                >
                  {previewText}
                </pre>
              </aside>
            ) : null}
          </div>
        )}
      </div>
      <ModalFooter className="-mx-6 -mb-4 mt-5">
        <Button variant="secondary" onClick={step === 0 ? onClose : () => setStep((current) => Math.max(current - 1, 0))}>
          {step === 0 ? t.close : t.back}
        </Button>
        {step < 2 ? <Button onClick={handleNext}>{t.next}</Button> : null}
      </ModalFooter>
    </Modal>
  )
}

export default DeepXivSetupDialog
