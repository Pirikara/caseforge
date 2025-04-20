# Caseforge Architecture

Caseforge は OpenAPI スキーマに基づく AI テスト生成・実行・可視化の OSS ツールです。コンテナ化された Frontend + Backend 構成で、clone → docker compose up ですぐに開発を開始できます。

---

## ディレクトリ構成

caseforge/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPIルーター
│   │   ├── services/      # ドメインロジック（RAG, Schema, テスト実行）
│   │   ├── workers/       # Celery タスク定義
│   │   └── main.py        # FastAPI アプリ本体
│   └── requirements.txt   # Python依存パッケージ
│
├── frontend/
│   └── src/app/           # Next.js App Router ベース UI
│       └── projects/[id]/runs/…  # 実行履歴 / 詳細表示
│
├── docker-compose.yml     # 全サービス定義（backend, frontend, redis, chroma, db）
└── .env.example            # 環境変数テンプレート

---

## 使用技術

| レイヤ | 技術                     |
|--------|--------------------------|
| フロント | Next.js 14 / App Router / Tailwind / SWR / recharts |
| バックエンド | FastAPI / Celery / LangChain / ChromaDB / SQLModel |
| インフラ | Docker Compose / Redis / PostgreSQL |

---

## システム構成図

┌──────────────┐
│   ユーザー (UI) │
└────┬───────┘
│ HTTP
┌────▼───────┐
│ Next.js Frontend │
└────┬───────┘
│ REST API
┌────▼───────┐
│ FastAPI Backend │
├──────────────┤
│  - schema upload      │
│  - test generate      │
│  - test runner        │
└────┬────────────┘
│ Celery
┌────▼───────┐        ┌─────────────┐
│ Celery Worker │<────▶ ChromaDB (RAG)
└────┬───────┘        └─────────────┘
│
▼
Redis (broker)

---

## 動作フロー概要

1. ユーザーが OpenAPI schema をアップロード
2. Chroma にベクトル化して保存（LangChain）
3. テスト生成を指示（Celery経由） → RAG でLLM呼び出し
4. 結果をファイル保存（tests.json）
5. テスト実行 → レスポンス比較
6. 結果ログを保存 & UIで一覧／詳細／グラフ可視化

---

## 開発・拡張の観点

- テスト生成部は LLM 呼び出しに差し替え可能（Claude, GPT, etc）
- RAG 処理に LangChain 使用。要件に応じて独自 chunker や retriever 追加可能
- テストケースは JSON形式で保存 → pytest や Postman 実行エンジンとも連携可能性あり
- UI は API 主導なので、GraphQLや gRPC への変更も容易