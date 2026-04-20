import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiRequestJson } from '@/lib/api/request'
import { adminApi } from '@/lib/api/admin'

vi.mock('@/lib/api/request', () => ({
  apiRequestJson: vi.fn(),
}))

describe('adminApi', () => {
  beforeEach(() => {
    vi.mocked(apiRequestJson).mockReset()
    vi.mocked(apiRequestJson).mockResolvedValue({})
  })

  it('uses the read-only system visibility endpoints', async () => {
    await adminApi.getOverview()
    await adminApi.getQuests()
    await adminApi.getQuestSummary('quest alpha')
    await adminApi.getRuntimeSessions()
    await adminApi.getLogSources()
    await adminApi.getLogTail('daemon/main.log', 120)
    await adminApi.getFailures()
    await adminApi.getRuntimeTools()
    await adminApi.getHardware()
    await adminApi.getCharts()
    await adminApi.getChart('cpu load', { window: '1h' })
    await adminApi.getStatsSummary()
    await adminApi.search('operator visibility', { limit: 25, scope: 'logs' })

    expect(apiRequestJson).toHaveBeenNthCalledWith(1, '/api/system/overview', {}, expect.any(Object))
    expect(apiRequestJson).toHaveBeenNthCalledWith(2, '/api/system/quests', {}, expect.any(Object))
    expect(apiRequestJson).toHaveBeenNthCalledWith(
      3,
      '/api/system/quests/quest%20alpha/summary',
      {},
      expect.any(Object)
    )
    expect(apiRequestJson).toHaveBeenNthCalledWith(4, '/api/system/runtime/sessions', {}, expect.any(Object))
    expect(apiRequestJson).toHaveBeenNthCalledWith(5, '/api/system/logs/sources', {}, expect.any(Object))
    expect(apiRequestJson).toHaveBeenNthCalledWith(
      6,
      '/api/system/logs/daemon%2Fmain.log/tail?limit=120',
      {},
      expect.any(Object)
    )
    expect(apiRequestJson).toHaveBeenNthCalledWith(7, '/api/system/failures', {}, expect.any(Object))
    expect(apiRequestJson).toHaveBeenNthCalledWith(8, '/api/system/runtime-tools', {}, expect.any(Object))
    expect(apiRequestJson).toHaveBeenNthCalledWith(9, '/api/system/hardware', {}, expect.any(Object))
    expect(apiRequestJson).toHaveBeenNthCalledWith(10, '/api/system/charts', {}, expect.any(Object))
    expect(apiRequestJson).toHaveBeenNthCalledWith(
      11,
      '/api/system/charts/cpu%20load?window=1h',
      {},
      expect.any(Object)
    )
    expect(apiRequestJson).toHaveBeenNthCalledWith(12, '/api/system/stats/summary', {}, expect.any(Object))
    expect(apiRequestJson).toHaveBeenNthCalledWith(
      13,
      '/api/system/search?q=operator+visibility&limit=25&scope=logs',
      {},
      expect.any(Object)
    )
  })
})
