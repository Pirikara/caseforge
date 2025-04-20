# Caseforge Architecture

**Caseforge** は OpenAPI スキーマに基づく AI テストケースの生成・実行・可視化を行う OSS ツールです。  
コンテナ化された Frontend + Backend 構成で、`git clone` → `docker compose up` によりすぐに起動可能です。

---

## ディレクトリ構成

```
caseforge/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI ルーター
│   │   ├── services/      # ドメインロジック（RAG, Schemaパース, テスト生成・実行）
│   │   ├── workers/       # Celery タスク定義
│   │   └── main.py        # FastAPI エントリーポイント
│   └── requirements.txt   # Python 依存パッケージ定義
│
├── frontend/
│   └── src/app/           # Next.js App Router ベースの UI
│       └── projects/[id]/runs/…  # 実行履歴や詳細表示ページ
│
├── docker-compose.yml     # backend, frontend, redis, chroma, db を含む開発用サービス定義
└── .env.example           # 環境変数テンプレート
```

---

## 使用技術

| レイヤ | 技術 |
|--------|------|
| フロントエンド | Next.js (App Router) / Tailwind CSS / SWR / Recharts |
| バックエンド | FastAPI / Celery / LangChain (RAG) / ChromaDB / SQLModel |
| インフラ | Docker Compose / Redis (Broker) / PostgreSQL |

---

## システム構成図（Mermaid）

```mermaid
graph TD;
  subgraph Frontend
    A[Next.js App] -- REST / WebSocket --> B[FastAPI API]
  end

  subgraph Backend
    B -- Celery Task --> C[Worker]
    C -- DB ORM --> D[PostgreSQL]
    C -- Vector Search --> E[ChromaDB]
  end

  R[Redis (Broker)]
  C --- R
  B --> R
```

---

## 動作フロー概要

1. ユーザーが OpenAPI schema をアップロード
2. LangChain を通じて schema をベクトル化し、Chroma に保存（RAGの準備）
3. ユーザーが「テスト生成」を指示 → Celery 経由で非同期タスクを実行
4. LLM を用いた RAG によりテストケースを生成（`tests/{project_id}/tests.json` に保存）
5. テスト実行時、テストケースを読み込んで各 API を叩き、レスポンスを評価
6. 実行結果ログを保存し、UI 上で以下を可視化：
    - 実行結果の一覧・詳細
    - ステータス別フィルター
    - グラフ（成功率・応答時間など）

---

## 拡張設計ポイント

- **LLM**：Claude / GPT / HuggingFace など、API呼び出し部分は差し替え可能
- **RAG**：LangChain 使用。必要に応じて chunker / retriever のカスタムも容易
- **テスト形式**：生成結果は JSON 形式で保存されるため、`pytest` や `Postman` 等と連携可能
- **UI層**：API ファースト設計。将来的に GraphQL や gRPC への置換も視野

---

## サンプルテストケース構造（tests.json）

```json
[
  {
    "name": "正常ログインができる",
    "method": "POST",
    "path": "/login",
    "request": {
      "headers": { "Content-Type": "application/json" },
      "body": { "email": "user@example.com", "password": "secure123" }
    },
    "expected_response": {
      "status": 200,
      "body_contains": ["token"]
    }
  },
  ...
]
```

---

## 開発ステップ（ローカル起動）

```bash
git clone https://github.com/yourname/caseforge.git
cd caseforge
cp .env.example .env
docker compose up --build
```

起動後、`http://localhost:3000` にアクセスして UI を確認できます。

---

> Caseforge は、開発者・QA エンジニア・SRE 向けに「AIでQAを加速する」ためのフルスタックOSS基盤です。
> フィードバック・Issue・PR 大歓迎です！