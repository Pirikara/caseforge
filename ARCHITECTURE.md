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
│   │   ├── config.py      # 環境変数・設定管理
│   │   ├── logging_config.py # ロギング設定
│   │   ├── models/        # SQLModel データモデル定義
│   │   ├── schemas/       # Pydantic スキーマ
│   │   ├── services/      # ドメインロジック（RAG, Schemaパース, テスト生成・実行）
│   │   ├── workers/       # Celery タスク定義
│   │   └── main.py        # FastAPI エントリーポイント
│   ├── tests/             # テストコード（単体・統合テスト）
│   │   ├── unit/          # 単体テスト
│   │   └── integration/   # 統合テスト
│   └── requirements.txt   # Python 依存パッケージ定義
│
├── frontend/
│   └── src/app/           # Next.js App Router ベースの UI
│       ├── components/    # コンポーネント（UI, atoms, molecules, organisms）
│       ├── hooks/         # カスタムフック（データフェッチング等）
│       ├── lib/           # ユーティリティ関数
│       └── projects/[id]/ # プロジェクト関連ページ（テスト生成・実行等）
│
├── docker-compose.yml     # backend, frontend, redis, chroma, db を含む開発用サービス定義
└── .env.example           # 環境変数テンプレート
```

---

## 使用技術

| レイヤ | 技術 |
|--------|------|
| フロントエンド | Next.js (App Router) / Tailwind CSS / SWR / Recharts / shadcn/ui / Zod / React Hook Form |
| バックエンド | FastAPI / Celery / LangChain (RAG) / FAISS / SQLModel / Pydantic Settings |
| インフラ | Docker Compose / Redis (Broker) / PostgreSQL |
| テスト | Pytest / Pytest-asyncio |

---

## システム構成図（Mermaid）

```mermaid
graph TD;
  subgraph Frontend
    A[Next.js App] -- REST API --> B[FastAPI API]
    A1[UI Components] --> A
    A2[Custom Hooks] --> A
  end

  subgraph Backend
    B -- Celery Task --> C[Worker]
    C -- DB ORM --> D[PostgreSQL]
    C -- Vector Search --> E[FAISS]
    
    F[Config] --> B
    F --> C
    G[Logging] --> B
    G --> C
  end

  subgraph Database
    D --- D1[Project]
    D --- D2[Schema]
    D --- D3[TestChain]
    D --- D4[TestChainStep]
    D --- D5[TestRun]
    D --- D6[TestResult]
  end

  R[Redis Broker]
  C --- R
  B --> R
```

---

## 動作フロー概要

1. ユーザーが OpenAPI schema をアップロード
2. スキーマをデータベースに保存し、LangChain を通じてベクトル化して FAISS に保存（RAGの準備）
3. ユーザーが「テストチェーン生成」を指示 → Celery 経由で非同期タスクを実行
4. LLM を用いた RAG によりテストチェーンを生成し、データベースに保存
5. テスト実行時、データベースからテストチェーンを読み込んで各 API を叩き、レスポンスを評価
6. 実行結果をデータベースに保存し、UI 上で以下を可視化：
    - 実行結果の一覧・詳細
    - ステータス別フィルター
    - グラフ（成功率・応答時間など）

### テストチェーン生成詳細フロー

```mermaid
sequenceDiagram
  participant User as ユーザー
  participant UI as フロントエンド
  participant API as FastAPI
  participant Worker as Celery Worker
  participant DB as PostgreSQL
  participant Vector as FAISS
  participant LLM as LLM API

  User->>UI: テストチェーン生成リクエスト
  UI->>API: POST /api/projects/{id}/generate-tests
  API->>Worker: generate_chains_task
  Worker->>DB: プロジェクト情報取得
  Worker->>Vector: スキーマベクトル検索
  Vector-->>Worker: 関連スキーマ情報
  Worker->>LLM: テストチェーン生成リクエスト
  LLM-->>Worker: 生成されたテストチェーン
  Worker->>DB: テストチェーン保存
  Worker-->>API: タスク完了通知
  API-->>UI: 生成完了レスポンス
  UI->>User: 完了通知
```

### テストチェーン実行フロー

```mermaid
sequenceDiagram
  participant User as ユーザー
  participant UI as フロントエンド
  participant API as FastAPI
  participant DB as PostgreSQL
  participant Target as 対象API

  User->>UI: テストチェーン実行リクエスト
  UI->>API: POST /api/projects/{id}/run
  API->>DB: テストチェーン取得
  API->>Target: リクエスト実行（ステップ1）
  Target-->>API: レスポンス
  API->>API: 変数抽出・評価
  API->>Target: リクエスト実行（ステップ2...）
  Target-->>API: レスポンス
  API->>DB: 実行結果保存
  API-->>UI: 実行結果レスポンス
  UI->>User: 結果表示
```

---

## 拡張設計ポイント

- **LLM**：Claude / GPT / HuggingFace など、API呼び出し部分は差し替え可能
- **RAG**：LangChain 使用。必要に応じて chunker / retriever のカスタムも容易
- **テスト形式**：生成結果は JSON 形式で保存されるため、`pytest` や `Postman` 等と連携可能
- **UI層**：API ファースト設計。将来的に GraphQL や gRPC への置換も視野
- **環境変数管理**：Pydantic Settings を使用した型安全な設定管理
- **エラーハンドリング**：構造化された例外処理と詳細なロギング
- **データベース**：SQLModel による型安全なORM、マイグレーション対応
- **デバッグ**：debugpy によるリモートデバッグ対応
- **フロントエンド**：
  - ダークモード対応（next-themes）
  - レスポンシブデザイン
  - パフォーマンス最適化（React.memo, useMemo, 動的インポート）

---

## データモデル構造

```mermaid
erDiagram
  Project {
    string id PK
    string name
    string description
    datetime created_at
    datetime updated_at
  }
  
  Schema {
    string id PK
    string project_id FK
    string filename
    string content
    datetime created_at
  }
  
  TestChain {
    string id PK
    string project_id FK
    string chain_id
    string name
    string description
    datetime created_at
  }
  
  TestChainStep {
    string id PK
    string chain_id FK
    integer sequence
    string name
    string method
    string path
    json request_headers
    json request_body
    json request_params
    json extract_rules
    integer expected_status
    datetime created_at
  }
  
  TestRun {
    string id PK
    string project_id FK
    string chain_id FK
    datetime started_at
    datetime completed_at
    string status
  }
  
  TestResult {
    string id PK
    string test_run_id FK
    string step_id FK
    string status
    integer response_time
    string response_body
    string error_message
    datetime created_at
  }
  
  Project ||--o{ Schema : "has"
  Project ||--o{ TestChain : "has"
  Project ||--o{ TestRun : "has"
  TestChain ||--o{ TestChainStep : "has"
  TestChain ||--o{ TestRun : "has"
  TestRun ||--o{ TestResult : "has"
  TestChainStep ||--o{ TestResult : "for"
```

---

## リクエストチェーン構造（JSON形式）

```json
{
  "name": "ユーザー作成と取得",
  "steps": [
    {
      "method": "POST",
      "path": "/users",
      "request": {
        "headers": { "Content-Type": "application/json" },
        "body": { "name": "Test User", "email": "test@example.com" }
      },
      "response": {
        "extract": { "user_id": "$.id" }
      }
    },
    {
      "method": "GET",
      "path": "/users/{user_id}",
      "request": {},
      "response": {}
    }
  ]
}
```

---

## 依存関係を考慮したテストチェーン生成

Caseforgeは、OpenAPIスキーマから依存関係を考慮したテストチェーンを自動生成します。

1. **依存関係の抽出**：OpenAPIスキーマを解析し、エンドポイント間の依存関係を特定
   - パスパラメータの依存関係（例：`POST /users` → `GET /users/{id}`）
   - リソース操作の依存関係（例：作成→取得→更新→削除）

2. **チェーン候補の特定**：依存関係グラフから有望なチェーン候補を特定
   - 依存関係のないエンドポイントからスタート
   - 最長のパスを優先的に選択

3. **RAGによるチェーン生成**：LLMを使用して各チェーン候補に対するテストチェーンを生成
   - リクエストボディの生成
   - レスポンスからの変数抽出ルールの設定
   - 後続リクエストでの変数利用

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

## テスト実行方法

バックエンドのテストは以下のコマンドで実行できます：

```bash
cd backend
python -m pytest
```

特定のテストだけを実行したい場合：

```bash
# サービス層のテストのみ実行
python -m pytest tests/unit/services/

# 特定のテストファイルを実行
python -m pytest tests/unit/api/test_projects.py
```

---

> Caseforge は、開発者・QA エンジニア・SRE 向けに「AIでQAを加速する」ためのフルスタックOSS基盤です。
> フィードバック・Issue・PR 大歓迎です！