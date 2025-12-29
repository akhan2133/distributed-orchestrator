#!/usr/bin/env bash
set -euo pipefail

# Simple end-to-end demo for the distributed orchestrator.
# Runs HTTP baseline + failure
# Runs Redis baseline + failure
# Produces analysis JSON, plots, and (if configured) an LLM summary.

echo "[demo] Starting end-to-end demo..."

# Make sure Docker stack is up
echo "[demo] Bringing up docker-compose stack..."
docker compose up -d

# Generate a unique suffix so runs don't collide
RUN_SUFFIX=$(date +%Y%m%d_%H%M%S)

HTTP_BASELINE_ID="http_baseline_${RUN_SUFFIX}"
HTTP_RUN_ID="http_run_${RUN_SUFFIX}"

REDIS_BASELINE_ID="redis_baseline_${RUN_SUFFIX}"
REDIS_RUN_ID="redis_run_${RUN_SUFFIX}"

echo "[demo] Using run IDs:"
echo "  HTTP baseline: ${HTTP_BASELINE_ID}"
echo "  HTTP run:      ${HTTP_RUN_ID}"
echo "  Redis baseline:${REDIS_BASELINE_ID}"
echo "  Redis run:     ${REDIS_RUN_ID}"
echo

# HTTP mode: baseline
echo "[demo][HTTP] Running baseline scenario..."
python -m orchestrator.coordinator \
  --scenario scenarios/baseline_warmup.yaml \
  --run-id "${HTTP_BASELINE_ID}" \
  --mode http

# HTTP mode: failure scenario
echo "[demo][HTTP] Running failure scenario..."
python -m orchestrator.coordinator \
  --scenario scenarios/node_failure.yaml \
  --run-id "${HTTP_RUN_ID}" \
  --mode http

# HTTP analysis plus plots
echo "[demo][HTTP] Running analysis..."
python -m orchestrator.analysis \
  --baseline-id "${HTTP_BASELINE_ID}" \
  --run-id "${HTTP_RUN_ID}" \
  > "runs/${HTTP_RUN_ID}/analysis.json"

echo "[demo][HTTP] Generating plots..."
python -m orchestrator.plot_run \
  --run-id "${HTTP_RUN_ID}" \
  --baseline-id "${HTTP_BASELINE_ID}"

# HTTP LLM summary (if GROQ_API_KEY + llm.enabled in config.yaml)
if [[ -n "${GROQ_API_KEY:-}" ]]; then
  echo "[demo][HTTP] Generating LLM summary..."
  python -m orchestrator.llm_summary \
    --baseline-id "${HTTP_BASELINE_ID}" \
    --run-id "${HTTP_RUN_ID}" \
    --output-path "runs/${HTTP_RUN_ID}/llm_summary.md"
else
  echo "[demo][HTTP] Skipping LLM summary (GROQ_API_KEY not set)."
fi

echo

# Redis mode: baseline
echo "[demo][Redis] Running baseline scenario..."
python -m orchestrator.coordinator \
  --scenario scenarios/baseline_warmup.yaml \
  --run-id "${REDIS_BASELINE_ID}" \
  --mode redis

# Redis mode: failure scenario
echo "[demo][Redis] Running failure scenario..."
python -m orchestrator.coordinator \
  --scenario scenarios/redis_node_failure.yaml \
  --run-id "${REDIS_RUN_ID}" \
  --mode redis

# Redis plot
echo "[demo][Redis] Generating throughput plot..."
python -m orchestrator.plot_run \
  --run-id "${REDIS_RUN_ID}" \
  --filename redis_metrics.csv

echo
echo "[demo] Done!"
echo "Artifacts created:"
echo "  HTTP:"
echo "    runs/${HTTP_RUN_ID}/metrics.csv"
echo "    runs/${HTTP_RUN_ID}/analysis.json"
echo "    runs/${HTTP_RUN_ID}/throughput.png"
echo "    runs/${HTTP_RUN_ID}/comparison.png"
echo "    runs/${HTTP_RUN_ID}/llm_summary.md (if LLM enabled)"
echo "  Redis:"
echo "    runs/${REDIS_RUN_ID}/redis_metrics.csv"
echo "    runs/${REDIS_RUN_ID}/throughput.png"
