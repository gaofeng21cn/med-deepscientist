export {}

declare global {
  interface Window {
    __DEEPSCIENTIST_RUNTIME__?: {
      surface?: string
      version?: string
      supports?: {
        productApis?: boolean
        socketIo?: boolean
        notifications?: boolean
        broadcasts?: boolean
        points?: boolean
        arxiv?: boolean
        cliFrontend?: boolean
      }
    }
  }
}
