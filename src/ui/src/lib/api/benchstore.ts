import { client } from '@/lib/api'
import { getApiBaseUrl } from '@/lib/api/client'
import type {
  BenchCatalogPayload,
  BenchCatalogQuery,
  BenchLocale,
  BenchSetupPacketPayload,
} from '@/lib/types/benchstore'

const BENCHSTORE_BASE = '/api/benchstore'

function sanitizeEntryId(entryId: string): string {
  const normalized = String(entryId || '').trim()
  if (!normalized) {
    throw new Error('BenchStore entry id is required.')
  }
  return normalized
}

function sanitizeStringList(values?: string[]): string[] {
  if (!Array.isArray(values)) return []
  const seen = new Set<string>()
  const next: string[] = []
  for (const value of values) {
    const normalized = String(value || '').trim()
    if (!normalized || seen.has(normalized)) continue
    seen.add(normalized)
    next.push(normalized)
  }
  return next
}

function appendListParams(params: URLSearchParams, key: string, values?: string[]) {
  for (const value of sanitizeStringList(values)) {
    params.append(key, value)
  }
}

export function normalizeBenchStoreLocale(locale?: string | null): BenchLocale {
  return String(locale || '').trim().toLowerCase().startsWith('zh') ? 'zh' : 'en'
}

export function buildBenchStoreCatalogPath(query: BenchCatalogQuery = {}): string {
  const params = new URLSearchParams()
  params.set('locale', normalizeBenchStoreLocale(query.locale))

  const search = String(query.search || '').trim()
  if (search) {
    params.set('search', search)
  }

  appendListParams(params, 'capability_tags', query.capabilityTags)
  appendListParams(params, 'cost_band', query.costBands)
  appendListParams(params, 'time_band', query.timeBands)

  if (typeof query.requiresPaper === 'boolean') {
    params.set('requires_paper', String(query.requiresPaper))
  }
  if (typeof query.requiresExecution === 'boolean') {
    params.set('requires_execution', String(query.requiresExecution))
  }
  if (typeof query.maxTimeHours === 'number' && Number.isFinite(query.maxTimeHours)) {
    params.set('max_time_hours', String(query.maxTimeHours))
  }

  return `${BENCHSTORE_BASE}?${params.toString()}`
}

export function buildBenchStoreEntryPath(entryId: string, locale?: BenchLocale | string | null): string {
  const params = new URLSearchParams()
  params.set('locale', normalizeBenchStoreLocale(locale))
  return `${BENCHSTORE_BASE}/${encodeURIComponent(sanitizeEntryId(entryId))}?${params.toString()}`
}

export function buildBenchStoreSetupPacketPath(
  entryId: string,
  locale?: BenchLocale | string | null
): string {
  const params = new URLSearchParams()
  params.set('locale', normalizeBenchStoreLocale(locale))
  return `${BENCHSTORE_BASE}/${encodeURIComponent(sanitizeEntryId(entryId))}/setup-packet?${params.toString()}`
}

export function buildBenchStoreEntryImagePath(
  entryId: string,
  locale?: BenchLocale | string | null
): string {
  const params = new URLSearchParams()
  params.set('locale', normalizeBenchStoreLocale(locale))
  return `${BENCHSTORE_BASE}/${encodeURIComponent(sanitizeEntryId(entryId))}/image?${params.toString()}`
}

export function buildBenchStoreEntryImageUrl(
  entryId: string,
  locale?: BenchLocale | string | null
): string {
  const base = getApiBaseUrl().replace(/\/$/, '')
  return `${base}${buildBenchStoreEntryImagePath(entryId, locale)}`
}

export async function listBenchStoreEntries(): Promise<BenchCatalogPayload> {
  const payload = await client.benchstoreEntries()
  return {
    ok: Boolean(payload.ok),
    catalog_root: typeof payload.catalog_root === 'string' ? payload.catalog_root : undefined,
    filter_options: payload.filter_options,
    invalid_entries: Array.isArray(payload.invalid_entries) ? payload.invalid_entries : [],
    items: Array.isArray(payload.items) ? (payload.items as BenchCatalogPayload['items']) : [],
    total: typeof payload.total === 'number' ? payload.total : Array.isArray(payload.items) ? payload.items.length : 0,
  }
}

export async function getBenchStoreSetupPacket(entryId: string): Promise<BenchSetupPacketPayload> {
  const payload = await client.benchstoreEntrySetupPacket(entryId)
  return {
    ok: Boolean(payload.ok),
    entry_id: String(payload.entry_id || entryId),
    setup_packet:
      payload.setup_packet && typeof payload.setup_packet === 'object'
        ? (payload.setup_packet as BenchSetupPacketPayload['setup_packet'])
        : ({
            entry_id: String(payload.entry_id || entryId),
          } as BenchSetupPacketPayload['setup_packet']),
  }
}
