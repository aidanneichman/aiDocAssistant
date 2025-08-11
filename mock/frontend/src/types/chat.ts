export type MessageRole = 'system' | 'user' | 'assistant'

export type ChatMessage = {
  id?: string
  role: MessageRole
  content: string
  timestamp?: string
}

export type ChatMode = 'regular' | 'deep_research'

export type Session = {
  id: string
  mode: ChatMode
  document_ids: string[]
}


