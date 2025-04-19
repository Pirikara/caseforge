'use client'
import useSWR from 'swr'
import { useParams } from 'next/navigation'

const fetcher = (url: string) => fetch(url).then(res => res.json())

export default function RunDetailPage() {
  const { id, run_id } = useParams()
  const { data, error } = useSWR(`/api/projects/${id}/runs/${run_id}`, fetcher)

  if (error) return <div>エラー: {error.message}</div>
  if (!data) return <div>読み込み中...</div>

  return (
    <div className="p-4">
      <h1 className="text-xl font-bold mb-4">実行結果: {run_id}</h1>
      <table className="table-auto w-full border">
        <thead>
          <tr className="bg-gray-100">
            <th className="px-2 py-1">ID</th>
            <th className="px-2 py-1">タイトル</th>
            <th className="px-2 py-1">ステータス</th>
            <th className="px-2 py-1">結果</th>
          </tr>
        </thead>
        <tbody>
          {data.map((t: any) => (
            <tr key={t.id}>
              <td className="border px-2 py-1">{t.id}</td>
              <td className="border px-2 py-1">{t.title}</td>
              <td className="border px-2 py-1">{t.status ?? '―'}</td>
              <td className="border px-2 py-1">{t.pass ? '✅' : '❌'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}