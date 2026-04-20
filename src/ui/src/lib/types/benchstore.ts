export type BenchLocale = 'en' | 'zh'

export type BenchCatalogQuery = {
  locale?: BenchLocale | string | null
  search?: string | null
  capabilityTags?: string[]
  costBands?: string[]
  timeBands?: string[]
  requiresPaper?: boolean | null
  requiresExecution?: boolean | null
  maxTimeHours?: number | null
}

export type BenchEntry = {
  id: string
  name: string
  one_line?: string | null
  task_description?: string | null
  capability_tags?: string[]
  track_fit?: string[]
  requires_execution?: boolean | null
  requires_paper?: boolean | null
  time_band?: string | null
  cost_band?: string | null
  paper?: {
    title?: string | null
    url?: string | null
  } | null
  download?: {
    url?: string | null
  } | null
  source_file?: string | null
  raw_payload?: Record<string, unknown> | null
}

export type BenchCatalogPayload = {
  ok: boolean
  catalog_root?: string
  filter_options?: Record<string, unknown>
  invalid_entries?: Array<Record<string, unknown>>
  items: BenchEntry[]
  total: number
}

export type BenchSetupPacket = {
  entry_id: string
  assistant_label?: string | null
  project_title?: string | null
  benchmark_local_path?: string | null
  local_dataset_paths?: string[]
  latex_markdown_path?: string | null
  device_summary?: string | null
  device_fit?: string | null
  requires_paper?: boolean | null
  benchmark_goal?: string | null
  constraints?: string[]
  suggested_form?: Record<string, unknown> | null
  startup_instruction?: string | null
  launch_payload?: {
    title?: string | null
    goal?: string | null
    initial_message?: string | null
    startup_contract?: Record<string, unknown> | null
  } | null
}

export type BenchSetupPacketPayload = {
  ok: boolean
  entry_id: string
  setup_packet: BenchSetupPacket
}
