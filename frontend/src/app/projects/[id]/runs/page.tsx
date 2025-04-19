'use client'
import useSWR from 'swr'
import Link from 'next/link'
import { useParams } from 'next/navigation'

const fetcher = (url: string) => fetch(url).then(res => res.json())

export default function RunListPage() {
  const { id } = useParams()
  const { data, error } = useSWR(`/api/projects/${id}/runs`, fetcher)

  if (error) return <div>エラー: {error.message}</div>
  if (!data) return <div>読み込み中...</div>

  return (
    <div className="p-4">
      <h1 className="text-xl font-bold mb-2">テスト実行履歴</h1>
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