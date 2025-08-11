import { useEffect, useState } from 'react'
import DocumentUpload from './components/DocumentUpload'
import DocumentList from './components/DocumentList'
import ChatInterface from './components/ChatInterface'

function App() {
  const [health, setHealth] = useState<string>('unknown')

  useEffect(() => {
    fetch('/api/health')
      .then((r) => r.json())
      .then((d) => setHealth(d.status ?? 'unknown'))
      .catch(() => setHealth('error'))
  }, [])

  return (
    <div className="min-h-screen p-6 space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">AI Legal Assistant</h1>
        <p className="text-gray-600">Backend health: {health}</p>
      </header>
      <section>
        <DocumentUpload onUploaded={() => { /* refresh handled in list */ }} />
        <DocumentList />
      </section>
      <section>
        <ChatInterface />
      </section>
    </div>
  )
}

export default App


