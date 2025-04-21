'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function UploadSchemaPage() {
  const router = useRouter()
  const [projectId, setProjectId] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const API = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000'

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file || !projectId) return
    setLoading(true)

    const formData = new FormData()
    formData.append('file', file)

    const res = await fetch(`${API}/api/projects/${projectId}/schema`, {
      method: 'POST',
      body: formData,
    })

    setLoading(false)
    if (res.ok) router.push(`/projects/${projectId}/runs`)
    else alert('Upload failed')
  }

  return (
    <div className="max-w-lg mx-auto p-6">
      <h1 className="text-2xl font-bold mb-4">OpenAPI Schema Upload</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="text"
          placeholder="Project ID (e.g. demo)"
          value={projectId}
          onChange={(e) => setProjectId(e.target.value)}
          className="w-full border p-2 rounded"
          required
        />
        <input
          type="file"
          accept=".yaml,.yml,.json"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="w-full"
          required
        />
        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
        >
          {loading ? 'Uploading…' : 'Upload'}
        </button>
      </form>
    </div>
  )
}