import { client } from '@/lib/api'
import type { BenchCatalogPayload, BenchSetupPacketPayload } from '@/lib/types/benchstore'

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
