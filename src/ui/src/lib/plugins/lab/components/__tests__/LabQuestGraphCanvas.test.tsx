import * as React from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import LabQuestGraphCanvas from '@/lib/plugins/lab/components/LabQuestGraphCanvas'

jest.mock('@/lib/api/lab', () => {
  const actual = jest.requireActual('@/lib/api/lab')
  return {
    ...actual,
    listLabAgents: jest.fn().mockResolvedValue({ items: [] }),
    listLabMemory: jest.fn().mockResolvedValue({ items: [] }),
    listLabPapers: jest.fn().mockResolvedValue({ items: [] }),
    updateLabQuestLayout: jest.fn().mockResolvedValue({ layout_json: {}, updated_at: '2026-03-21T00:00:00Z' }),
  }
})

jest.mock('@xyflow/react', () => {
  const ReactRuntime = require('react') as typeof React
  return {
    MarkerType: { ArrowClosed: 'arrowclosed' },
    Position: { Left: 'left', Right: 'right' },
    Handle: () => null,
    ReactFlow: ({
      children,
      nodes,
      nodeTypes,
    }: {
      children?: React.ReactNode
      nodes?: Array<{ id: string; type?: string; data?: unknown }>
      nodeTypes?: Record<string, React.ComponentType<any>>
    }) => (
      <div data-testid="reactflow">
        {(nodes ?? []).map((node) => {
          const NodeComponent = node.type ? nodeTypes?.[node.type] : null
          return NodeComponent ? <NodeComponent key={node.id} data={node.data} /> : null
        })}
        {children}
      </div>
    ),
    ReactFlowProvider: ({ children }: { children?: React.ReactNode }) => (
      <div data-testid="reactflow-provider">{children}</div>
    ),
    Background: () => null,
    Controls: () => null,
    MiniMap: () => null,
    useNodesInitialized: () => true,
    useReactFlow: () => ({
      setCenter: jest.fn(),
      fitView: jest.fn(),
      getNodes: jest.fn().mockReturnValue([]),
      getInternalNode: jest.fn().mockReturnValue(undefined),
    }),
    useNodesState: (initial: unknown) => {
      const [nodes, setNodes] = ReactRuntime.useState(initial)
      return [nodes, setNodes, jest.fn()]
    },
    useEdgesState: (initial: unknown) => {
      const [edges, setEdges] = ReactRuntime.useState(initial)
      return [edges, setEdges, jest.fn()]
    },
  }
})

jest.mock('@xyflow/react/dist/style.css', () => ({}))
jest.mock('@/lib/plugins/lab/lab.css', () => ({}))

describe('LabQuestGraphCanvas', () => {
  it('does not loop state updates when queries are disabled (empty projectId/questId)', () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    render(
      <QueryClientProvider client={queryClient}>
        <LabQuestGraphCanvas projectId="" questId="" />
      </QueryClientProvider>
    )

    expect(screen.getByTestId('reactflow')).toBeInTheDocument()
    expect(screen.getByLabelText('Show Branches')).toBeInTheDocument()
    expect(screen.getByLabelText('Show Recent events')).toBeInTheDocument()
    expect(screen.getByLabelText('Show Papers')).toBeInTheDocument()
    expect(screen.queryByText('No graph nodes yet.')).toBeNull()
  })

  it('does not loop state updates when graph queries resolve with data', async () => {
    const fetchGraph = jest.fn().mockResolvedValue({
      view: 'branch',
      nodes: [
        {
          node_id: 'branch-1',
          branch_name: 'main',
          created_at: '2025-01-01T00:00:00Z',
        },
      ],
      edges: [],
      head_branch: 'main',
      layout_json: {},
    })
    const fetchEvents = jest.fn().mockResolvedValue({ items: [], next_cursor: null })

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    render(
      <QueryClientProvider client={queryClient}>
        <LabQuestGraphCanvas
          projectId="project-1"
          questId="quest-1"
          fetchGraph={fetchGraph}
          fetchEvents={fetchEvents}
        />
      </QueryClientProvider>
    )

    await waitFor(() => {
      expect(fetchGraph).toHaveBeenCalled()
    })

    expect(screen.getByTestId('reactflow')).toBeInTheDocument()
    fireEvent.click(screen.getByLabelText('Show Branches'))
    expect(screen.getByText(/Current view/i)).toBeInTheDocument()
  })

  it('skips hidden panel queries when the canvas is branch-only', async () => {
    const labApi = await import('@/lib/api/lab')
    ;(labApi.listLabAgents as jest.Mock).mockClear()
    ;(labApi.listLabMemory as jest.Mock).mockClear()
    ;(labApi.listLabPapers as jest.Mock).mockClear()

    const fetchGraph = jest.fn().mockResolvedValue({
      view: 'branch',
      nodes: [
        {
          node_id: 'branch-1',
          branch_name: 'main',
          created_at: '2025-01-01T00:00:00Z',
        },
      ],
      edges: [],
      head_branch: 'main',
      layout_json: {},
    })
    const fetchEvents = jest.fn().mockResolvedValue({ items: [], next_cursor: null })

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    render(
      <QueryClientProvider client={queryClient}>
        <LabQuestGraphCanvas
          projectId="project-1"
          questId="quest-1"
          preferredViewMode="branch"
          showFloatingPanels={false}
          fetchGraph={fetchGraph}
          fetchEvents={fetchEvents}
        />
      </QueryClientProvider>
    )

    await waitFor(() => {
      expect(fetchGraph).toHaveBeenCalledTimes(1)
    })

    await waitFor(() => {
      expect(fetchEvents).toHaveBeenCalledTimes(1)
    })

    expect(fetchEvents).toHaveBeenCalledWith(
      'project-1',
      'quest-1',
      expect.objectContaining({
        eventTypes: expect.arrayContaining(['artifact.recorded', 'runner.tool_result']),
        limit: 800,
        includePayload: true,
      })
    )
    expect(labApi.listLabAgents).toHaveBeenCalledTimes(1)
    expect(labApi.listLabMemory).toHaveBeenCalledTimes(1)
    expect(labApi.listLabPapers).not.toHaveBeenCalled()
  })

  it('renders replay-aware memory hints on branch nodes', async () => {
    const labApi = await import('@/lib/api/lab')
    ;(labApi.listLabMemory as jest.Mock).mockResolvedValue({
      items: [
        {
          entry_id: 'MEM-1',
          kind: 'knowledge',
          branch_name: 'main',
          title: 'Warmup lesson',
          summary: 'Longer warmup stabilizes the branch.',
          updated_at: '2026-02-07T00:00:00Z',
        },
      ],
    })

    const fetchGraph = jest.fn().mockResolvedValue({
      view: 'branch',
      nodes: [
        {
          node_id: 'branch-1',
          branch_name: 'main',
          created_at: '2025-01-01T00:00:00Z',
          metrics_json: {
            primary: {
              label: 'Accuracy',
              delta: '+1.2%',
            },
          },
        },
      ],
      edges: [],
      head_branch: 'main',
      layout_json: {},
    })
    const fetchEvents = jest.fn().mockResolvedValue({ items: [], next_cursor: null })

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    render(
      <QueryClientProvider client={queryClient}>
        <LabQuestGraphCanvas
          projectId="project-1"
          questId="quest-1"
          atEventId="evt-1"
          fetchGraph={fetchGraph}
          fetchEvents={fetchEvents}
        />
      </QueryClientProvider>
    )

    await waitFor(() => {
      expect(labApi.listLabMemory).toHaveBeenCalledWith(
        'project-1',
        expect.objectContaining({ questId: 'quest-1', atEventId: 'evt-1' })
      )
    })

    expect(await screen.findByText('1 memory note')).toBeInTheDocument()
    expect(screen.getByText('Longer warmup stabilizes the branch.')).toBeInTheDocument()
  })

  it('switches branch nodes into metric mode and keeps baseline metrics visible', async () => {
    const fetchGraph = jest.fn().mockResolvedValue({
      view: 'branch',
      nodes: [
        {
          node_id: 'baseline-root',
          branch_name: 'baseline',
          node_kind: 'baseline_root',
          target_label: 'Accepted Baseline',
          status: 'confirmed',
          created_at: '2025-01-01T00:00:00Z',
          metrics_json: { acc: 0.8 },
          node_summary: {
            last_reply: 'Baseline locked.',
            latest_metrics: { acc: 0.8 },
          },
        },
        {
          node_id: 'branch-1',
          branch_name: 'main',
          branch_no: '001',
          idea_title: 'Branch Alpha',
          created_at: '2025-01-02T00:00:00Z',
          metrics_json: { acc: 0.86 },
          node_summary: {
            last_reply: 'Main branch beats baseline.',
            metrics_delta: { acc: 0.06 },
          },
        },
      ],
      edges: [],
      head_branch: 'main',
      layout_json: {},
      metric_catalog: [{ key: 'acc', label: 'Accuracy', direction: 'higher', importance: 1 }],
    })
    const fetchEvents = jest.fn().mockResolvedValue({ items: [], next_cursor: null })

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    render(
      <QueryClientProvider client={queryClient}>
        <LabQuestGraphCanvas
          projectId="project-1"
          questId="quest-1"
          fetchGraph={fetchGraph}
          fetchEvents={fetchEvents}
        />
      </QueryClientProvider>
    )

    await waitFor(() => {
      expect(fetchGraph).toHaveBeenCalled()
    })

    fireEvent.click(screen.getByRole('button', { name: 'Metric' }))

    expect(screen.getByText('0.8000')).toBeInTheDocument()
    expect(screen.getByText('0.8600')).toBeInTheDocument()
    expect(screen.getByText('Baseline reference')).toBeInTheDocument()
    expect(screen.getByText('Δ +0.0600 vs baseline')).toBeInTheDocument()
  })

  it('keeps branch list clicks as selection-only without opening the stage page', async () => {
    const fetchGraph = jest.fn().mockResolvedValue({
      view: 'branch',
      nodes: [
        {
          node_id: 'branch-1',
          branch_name: 'main',
          branch_no: '001',
          idea_title: 'Branch Alpha',
          next_target: 'Run ablation',
          created_at: '2025-01-01T00:00:00Z',
        },
      ],
      edges: [],
      head_branch: 'main',
      layout_json: {},
    })
    const fetchEvents = jest.fn().mockResolvedValue({ items: [], next_cursor: null })
    const onBranchSelect = jest.fn()
    const onStageOpen = jest.fn()
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <LabQuestGraphCanvas
          projectId="project-1"
          questId="quest-1"
          fetchGraph={fetchGraph}
          fetchEvents={fetchEvents}
          onBranchSelect={onBranchSelect}
          onStageOpen={onStageOpen}
        />
      </QueryClientProvider>
    )

    await waitFor(() => {
      expect(fetchGraph).toHaveBeenCalled()
    })

    const branchButton = container.querySelector('.lab-quest-branch-item') as HTMLButtonElement | null
    expect(branchButton).not.toBeNull()
    fireEvent.click(branchButton as HTMLButtonElement)

    expect(onBranchSelect).toHaveBeenCalledWith('main')
    expect(onStageOpen).not.toHaveBeenCalled()
  })

  it('restores current-path filtering from persisted layout and saves filter changes', async () => {
    jest.useFakeTimers()
    const labApi = await import('@/lib/api/lab')
    ;(labApi.updateLabQuestLayout as jest.Mock).mockClear()
    const fetchGraph = jest.fn().mockResolvedValue({
      view: 'branch',
      nodes: [
        {
          node_id: 'baseline-root',
          branch_name: 'baseline',
          node_kind: 'baseline_root',
          target_label: 'Baseline',
          created_at: '2025-01-01T00:00:00Z',
        },
        {
          node_id: 'main',
          branch_name: 'main',
          idea_title: 'Main Route',
          created_at: '2025-01-01T00:00:00Z',
        },
        {
          node_id: 'run/current',
          branch_name: 'run/current',
          parent_branch: 'main',
          idea_title: 'Current Route',
          created_at: '2025-01-02T00:00:00Z',
          workflow_state: {
            analysis_state: 'active',
            writing_state: 'blocked_by_analysis',
            status_reason: 'Analysis 1/2 done · next: slice-b',
          },
        },
        {
          node_id: 'run/other',
          branch_name: 'run/other',
          parent_branch: 'main',
          idea_title: 'Sibling Route',
          created_at: '2025-01-03T00:00:00Z',
          workflow_state: {
            analysis_state: 'none',
            writing_state: 'ready',
            status_reason: 'Main experiment recorded. Ready for writing.',
          },
        },
      ],
      edges: [
        { source: 'main', target: 'run/current' },
        { source: 'main', target: 'run/other' },
      ],
      head_branch: 'run/current',
      layout_json: {
        preferences: {
          pathFilterMode: 'current',
          showAnalysis: true,
        },
      },
    })
    const fetchEvents = jest.fn().mockResolvedValue({ items: [], next_cursor: null })
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    render(
      <QueryClientProvider client={queryClient}>
        <LabQuestGraphCanvas
          projectId="project-1"
          questId="quest-1"
          fetchGraph={fetchGraph}
          fetchEvents={fetchEvents}
        />
      </QueryClientProvider>
    )

    await waitFor(() => {
      expect(fetchGraph).toHaveBeenCalled()
    })

    fireEvent.click(screen.getByLabelText('Show Branches'))
    expect(screen.getByText('Current Route')).toBeInTheDocument()
    expect(screen.queryByText('Sibling Route')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: 'All' }))

    await waitFor(() => {
      expect(screen.getByText('Sibling Route')).toBeInTheDocument()
    })

    jest.advanceTimersByTime(900)

    await waitFor(() => {
      expect(labApi.updateLabQuestLayout).toHaveBeenCalledWith(
        'project-1',
        'quest-1',
        expect.objectContaining({
          preferences: expect.objectContaining({
            pathFilterMode: 'all',
          }),
        })
      )
    })
    jest.useRealTimers()
  })
})
