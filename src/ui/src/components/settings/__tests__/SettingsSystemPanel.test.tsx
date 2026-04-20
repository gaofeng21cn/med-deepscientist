import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it, vi } from 'vitest'

import { SettingsSystemPanelView } from '@/components/settings/SettingsSystemPanel'

describe('SettingsSystemPanelView', () => {
  it('renders the read-only system visibility sections with loaded data', () => {
    const html = renderToStaticMarkup(
      <SettingsSystemPanelView
        locale="en"
        refreshing={false}
        overview={{ data: { ok: true, updated_at: '2026-04-20T09:15:00Z', counts: { quests_running: 1 } }, loading: false, error: '' }}
        quests={{
          data: {
            items: [{ quest_id: 'quest-001', title: 'Cardio risk', status: 'running' }],
          },
          loading: false,
          error: '',
        }}
        questSummary={{
          data: {
            ok: true,
            quest: { quest_id: 'quest-001', title: 'Cardio risk', status: 'running' },
            runtime_audit: { active_run_id: 'run-main-001', worker_running: true },
            bash_sessions: [],
          },
          loading: false,
          error: '',
        }}
        runtimeSessions={{
          data: {
            quest_sessions: [{ quest_id: 'quest-001', title: 'Cardio risk', status: 'running', active_run_id: 'run-main-001' }],
            connector_sessions: [{ quest_id: 'quest-001', bound_sources: ['web-react'], status: 'bound' }],
            bash_sessions: [{ bash_id: 'bash-1', quest_id: 'quest-001', status: 'running' }],
            totals: { quest_sessions: 1, connector_sessions: 1, bash_sessions: 1 },
          },
          loading: false,
          error: '',
        }}
        logSources={{
          data: { items: [{ source_id: 'daemon.log', label: 'Daemon log', source_type: 'daemon' }] },
          loading: false,
          error: '',
        }}
        logTail={{
          data: { source_id: 'daemon.log', lines: ['boot ok', 'watcher online'] },
          loading: false,
          error: '',
        }}
        failures={{
          data: { items: [{ id: 'fail-1', severity: 'warning', summary: 'Slow poll loop' }] },
          loading: false,
          error: '',
        }}
        runtimeTools={{
          data: { items: [{ tool_name: 'artifact.interact', kind: 'managed', available: true, summary: 'Artifact entrypoint' }] },
          loading: false,
          error: '',
        }}
        hardware={{ data: { cpu: 'M4 Max', memory_gb: 128 }, loading: false, error: '' }}
        charts={{
          data: { items: [{ chart_id: 'cpu', title: 'CPU Load', description: 'host cpu usage' }] },
          loading: false,
          error: '',
        }}
        chartDetail={{
          data: { chart_id: 'cpu', title: 'CPU Load', series: [{ label: 'cpu', value: 3 }] },
          loading: false,
          error: '',
        }}
        statsSummary={{ data: { quest_status_counts: { running: 1 }, runtime_session_counts: { bash_sessions: 1 } }, loading: false, error: '' }}
        searchResults={{
          data: { items: [{ result_id: 'hit-1', label: 'daemon.log', description: 'watcher online', result_type: 'logs' }] },
          loading: false,
          error: '',
        }}
        selectedQuestId="quest-001"
        selectedLogSourceId="daemon.log"
        selectedChartId="cpu"
        chartWindow="1h"
        searchQuery="watcher"
        onRefresh={vi.fn()}
        onSelectQuest={vi.fn()}
        onSelectLogSource={vi.fn()}
        onSelectChart={vi.fn()}
        onChartWindowChange={vi.fn()}
        onSearchQueryChange={vi.fn()}
        onSearch={vi.fn()}
      />
    )

    expect(html).toContain('System visibility')
    expect(html).toContain('/api/system/*')
    expect(html).toContain('System overview')
    expect(html).toContain('Cardio risk')
    expect(html).toContain('run-main-001')
    expect(html).toContain('Runtime sessions')
    expect(html).toContain('Daemon log')
    expect(html).toContain('watcher online')
    expect(html).toContain('artifact.interact')
    expect(html).toContain('CPU Load')
    expect(html).toContain('Chart query')
    expect(html).toContain('System search input')
  })
})
