import { useDocuments } from '../hooks/useDocuments'

export default function DocumentList() {
  const { documents, loading, error, remove, refresh } = useDocuments()

  return (
    <div className="mt-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Documents</h2>
        <button className="text-sm text-blue-600" onClick={() => refresh()}>
          Refresh
        </button>
      </div>
      {loading && <p className="text-gray-600">Loading...</p>}
      {error && <p className="text-red-600">{error}</p>}
      {!loading && !documents.length && <p className="text-gray-600">No documents yet.</p>}
      <ul className="divide-y border rounded mt-2">
        {documents.map((d) => (
          <li key={d.id} className="p-3 flex items-center justify-between">
            <div>
              <div className="font-medium">{d.original_filename}</div>
              <div className="text-xs text-gray-500">
                {d.content_type} · {(d.size_bytes / (1024 * 1024)).toFixed(2)} MB
              </div>
            </div>
            <button
              className="text-sm text-red-600"
              onClick={() => remove(d.id)}
              aria-label={`Delete ${d.original_filename}`}
            >
              Delete
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}


