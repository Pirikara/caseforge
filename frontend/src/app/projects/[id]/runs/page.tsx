'use client'
import Link from 'next/link'
import useSWR from 'swr'
import { useParams } from 'next/navigation'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const API = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000'
const fetcher = (url: string) =>
  fetch(`${API}${url}`).then(r => {
    if (!r.ok) throw new Error(`API ${r.status}`)
    return r.json()
  })

export default function RunListPage() {
  const { id } = useParams()
  const { data, error } = useSWR(`/api/projects/${id}/runs`, fetcher)

  if (error) return <div>エラー: {error.message}</div>
  if (!data) return <div>読み込み中...</div>

  const chartData = data.map((runId: string) => {
    const timestamp = runId.replace(/^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})$/, '$1/$2/$3 $4:$5:$6')
    return { name: timestamp, value: parseInt(runId.replace(/.*-(\d+)$/, '$1')) || 0 }
  })

  return (
    <div className="p-4">
      <h1 className="text-xl font-bold mb-4">テスト実行履歴</h1>

      <div className="h-64 mb-8">
        <ResponsiveContainer>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
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