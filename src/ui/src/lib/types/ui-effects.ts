export type UIEffectName =
  | 'start_setup:patch'
  | 'file:read'
  | 'file:write'
  | 'file:delete'
  | 'file:move'
  | 'file:rename'
  | 'file:highlight'
  | 'file:open'
  | 'file:jump'
  | 'pdf:jump'
  | 'annotation:created'
  | 'pdf:annotation_created'
  | 'notebook:focus'
  | 'notebook:block_inserted'

export type PdfRect = {
  x1: number
  y1: number
  x2: number
  y2: number
  width?: number
  height?: number
  pageNumber?: number
}

export interface FileEffectData {
  fileId?: string
  fileName?: string
  filePath?: string
  projectId?: string
  created?: boolean
  lines?: number[]
  changeType?: 'create' | 'update' | 'delete'
  diff?: FileDiffPayload
  sourcePath?: string
  targetPath?: string
  sourceName?: string
  targetName?: string
}

export interface FileJumpEffectData extends FileEffectData {
  lineStart?: number
  lineEnd?: number
  line?: number
}

export type FileDiffPayload = {
  lines: string[]
  added?: number
  removed?: number
  truncated?: boolean
}

export interface PdfJumpEffectData {
  fileId: string
  fileName?: string
  page?: number
  rects?: PdfRect[]
  boundingRect?: PdfRect
  color?: string
  colorName?: string
  mode?: 'guide' | 'annotate'
  durationMs?: number
  text?: string
  annotationId?: string
  [key: string]: unknown
}

export interface PdfAnnotationEffectData {
  fileId: string
  fileName?: string
  annotationId?: string
  page?: number
  color?: string
  colorName?: string
  text?: string
  comment?: string
  position?: Record<string, unknown>
  tags?: string[]
  source?: string
  [key: string]: unknown
}

export interface UIEffectDataMap {
  'start_setup:patch': {
    patch?: Record<string, unknown>
    message?: string | null
  }
  'file:read': FileEffectData
  'file:write': FileEffectData
  'file:delete': FileEffectData
  'file:move': FileEffectData
  'file:rename': FileEffectData
  'file:highlight': FileEffectData
  'file:open': FileEffectData
  'file:jump': FileJumpEffectData
  'pdf:jump': PdfJumpEffectData
  'annotation:created': PdfAnnotationEffectData
  'pdf:annotation_created': PdfAnnotationEffectData
  'notebook:focus': {
    notebookId: string
    blockId?: string
  }
  'notebook:block_inserted': {
    notebookId: string
    blockId: string
    blockType?: string
  }
}

export type KnownEffect = {
  [K in keyof UIEffectDataMap]: {
    name: K
    data: UIEffectDataMap[K]
  }
}[keyof UIEffectDataMap]

export type Effect = KnownEffect | { name: string; data: Record<string, unknown> }
