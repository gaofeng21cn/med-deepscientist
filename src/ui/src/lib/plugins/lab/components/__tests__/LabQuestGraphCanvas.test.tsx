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
    useReactFlow: () => ({ setCenter: jest.fn(), fitView: jest.fn() }),
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
})
