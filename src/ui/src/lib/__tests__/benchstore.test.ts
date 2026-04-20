import { describe, expect, it } from 'vitest'

import { BenchStoreDialog } from '@/components/landing/BenchStoreDialog'
import {
  buildBenchStoreCatalogPath,
  buildBenchStoreEntryPath,
  buildBenchStoreSetupPacketPath,
  normalizeBenchStoreLocale,
} from '@/lib/api/benchstore'

describe('benchstore api helpers', () => {
  it('normalizes locale to zh or en', () => {
    expect(normalizeBenchStoreLocale('zh-CN')).toBe('zh')
    expect(normalizeBenchStoreLocale('zh')).toBe('zh')
    expect(normalizeBenchStoreLocale('en-US')).toBe('en')
    expect(normalizeBenchStoreLocale(undefined)).toBe('en')
  })

  it('builds catalog path with stable query params', () => {
    expect(
      buildBenchStoreCatalogPath({
        locale: 'zh-CN',
        search: ' vision bench ',
        capabilityTags: ['vision', 'multimodal'],
        costBands: ['low', 'medium'],
        timeBands: ['2h'],
        requiresPaper: true,
        requiresExecution: false,
        maxTimeHours: 6,
      })
    ).toBe(
      '/api/benchstore?locale=zh&search=vision+bench&capability_tags=vision&capability_tags=multimodal&cost_band=low&cost_band=medium&time_band=2h&requires_paper=true&requires_execution=false&max_time_hours=6'
    )
  })

  it('builds detail and setup-packet paths with encoded ids', () => {
    expect(buildBenchStoreEntryPath('Vision Bench/1', 'zh')).toBe(
      '/api/benchstore/Vision%20Bench%2F1?locale=zh'
    )
    expect(buildBenchStoreSetupPacketPath('Vision Bench/1', 'en')).toBe(
      '/api/benchstore/Vision%20Bench%2F1/setup-packet?locale=en'
    )
  })

  it('imports BenchStoreDialog as a compile-ready module', () => {
    expect(BenchStoreDialog).toBeTypeOf('function')
  })
})
