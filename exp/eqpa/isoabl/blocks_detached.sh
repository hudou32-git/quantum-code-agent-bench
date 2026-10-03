#!/usr/bin/env bash
# Phase II main ablation: frozen cohort (56 tasks) x A/B/C/R, matched blocks, official DeepSeek.
# Cohort frozen by operator 2026-09-15 21:05 Beijing (draft v1, 56 tasks: binding 40 / planning 16).
# Survives SSH disconnect; resume-safe (completed (task, arm) skipped). Peak-guarded.
set -uo pipefail
cd /root/cyy/llm_code/submit
export PYTHONUNBUFFERED=1
ART=exp/eqpa/runtime/logs
LOG="$ART/e4_isoabl_blocks_20260915.log"
PIDF="$ART/e4_isoabl_blocks_20260915.pid"
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
if [[ $? -ne 0 ]]; then echo "REFUSE: selftest failed" | tee -a "$LOG"; rm -f "$PIDF"; exit 2; fi

echo "===== $(date -Is) start Phase II blocks workers=32 pid=$$ =====" | tee -a "$LOG"
python3 -u -m exp.eqpa.isoabl.runner blocks --workers 32 2>&1 | tee -a "$LOG"
echo "===== $(date -Is) blocks exit=${PIPESTATUS[0]} PHASE II DONE =====" | tee -a "$LOG"
rm -f "$PIDF"
