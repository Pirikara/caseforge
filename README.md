# Caseforge

OpenAPI スキーマから AI が依存関係を考慮したリクエストチェーン形式のテストシナリオを生成・実行する OSS ツール。

## Quick start
```bash
git clone --template https://github.com/<you>/caseforge.git
cp .env.example .env
docker compose -f docker-compose.dev.yml up --build
```