#!/bin/bash
# pgvector 扩展 + category_embeddings 表 + 首次嵌入批处理
# 用法: bash /opt/xhs-cloud/cloud_deploy/scripts/ensure_pgvector.sh
set -euo pipefail

ROOT="${XHS_CLOUD_ROOT:-/opt/xhs-cloud}"
ENV_FILE="${XHS_ENV_FILE:-$ROOT/.env}"

GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log() { echo -e "  ${CYAN}[*]${NC} $1"; }
ok() { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}!${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; exit 1; }

[[ -f "$ENV_FILE" ]] || fail "缺少 $ENV_FILE"
set -a && source "$ENV_FILE" && set +a
[[ "${XHS_DATABASE_URL:-}" == postgres* ]] || fail "需要 XHS_DATABASE_URL (PostgreSQL)"

PGV="$ROOT/cloud_deploy/database/10_pgvector_embeddings.sql"
[[ -f "$PGV" ]] || fail "缺少 $PGV"

log "CREATE EXTENSION vector（需 PG superuser 或已预装）"
if psql "$XHS_DATABASE_URL" -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null; then
  ok "pgvector 扩展已就绪"
else
  warn "CREATE EXTENSION 失败 — 请在 PG 管理员控制台执行: CREATE EXTENSION vector;"
  warn "或联系云 RDS 开启 pgvector 后重跑本脚本"
  exit 1
fi

log "应用 10_pgvector_embeddings.sql"
psql "$XHS_DATABASE_URL" -v ON_ERROR_STOP=1 -f "$PGV"
ok "category_embeddings 表已就绪"

log "运行类目嵌入批处理"
export PYTHONPATH="$ROOT"
export PYTHONUNBUFFERED=1
if python3 "$ROOT/cloud_deploy/scripts/run_category_embeddings.py"; then
  ok "嵌入批处理完成"
else
  warn "嵌入批处理未完全成功（可能缺 INSIGHT_LLM_API_KEY 或 embedding 模型不可用）"
  warn "表结构已就绪，可稍后重跑: python3 cloud_deploy/scripts/run_category_embeddings.py"
fi
