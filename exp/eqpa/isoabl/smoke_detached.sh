#!/usr/bin/env bash
# Phase I smoke for the ISO mechanism ablation: dev cases x A/B/C/R via official DeepSeek.
# Smoke is EXCLUDED from formal data (freeze plan §21). Selftest must pass first.
# Survives SSH disconnect. Peak guard: Beijing Mon-Fri 09:00-12:00 & 14:00-18:00.
set -uo pipefail
cd /root/cyy/llm_code/submit
export PYTHONUNBUFFERED=1
ART=exp/eqpa/runtime/logs
LOG="$ART/e4_isoabl_smoke_20260915.log"
PIDF="$ART/e4_isoabl_smoke_20260915.pid"
echo $$ > "$PIDF"

APIKEY=$(grep -E '^DEEPSEEK_API_KEY=' /root/cyy/llm_code/submit/.env | head -1 | cut -d= -f2- | tr -d '"')
if [[ -z "$APIKEY" ]]; then echo "REFUSE: DEEPSEEK_API_KEY missing" | tee -a "$LOG"; rm -f "$PIDF"; exit 2; fi

PROBE=$(curl -sS -m 30 https://api.deepseek.com/v1/chat/completions \
  -H "Authorization: Bearer $APIKEY" -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"hi"}],"max_tokens":1}' || true)
if ! grep -q '"choices"' <<<"$PROBE"; then
  echo "REFUSE: API probe failed: ${PROBE:0:300}" | tee -a "$LOG"; rm -f "$PIDF"; exit 2
fi
echo "API probe ok $(date -Is)" | tee -a "$LOG"

python3 -m exp.eqpa.isoabl.selftest >> "$LOG" 2>&1
RC=$?
if [[ $RC -ne 0 ]]; then
  echo "REFUSE: selftest failed rc=$RC" | tee -a "$LOG"; rm -f "$PIDF"; exit 2
fi
echo "selftest OK, starting smoke $(date -Is)" | tee -a "$LOG"

python3 -u -m exp.eqpa.isoabl.runner smoke --workers 4 2>&1 | tee -a "$LOG"
echo "===== $(date -Is) smoke exit=${PIPESTATUS[0]} DONE =====" | tee -a "$LOG"
rm -f "$PIDF"
