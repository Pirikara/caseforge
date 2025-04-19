'use client'
import useSWR from 'swr'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { useState } from 'react'

const fetcher = (url: string) => fetch(url).then(res => res.json())

export default function RunListPage() {
  const { id } = useParams()
  const { data, error, mutate } = useSWR(`/api/projects/${id}/runs`, fetcher)
  const [loading, setLoading] = useState(false)

  const handleRunClick = async () => {
    setLoading(true)
    await fetch(`/api/projects/${id}/run`, { method: 'POST' })
    await mutate()  // 再取得
    setLoading(false)
  }

  if (error) return <div>エラー: {error.message}</div>
  if (!data) return <div>読み込み中...</div>

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-xl font-bold">テスト実行履歴</h1>
        <button
          onClick={handleRunClick}
          disabled={loading}
          className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          {loading ? '実行中...' : 'テスト実行'}
        </button>
      </div>
      <ul className="space-y-1">
        {data.map((runId: string) => (
          <li key={runId}>
            <Link href={`/projects/${id}/runs/${runId}`}>{runId}</Link>
          </li>
        ))}
      </ul>
    </div>
  )
}