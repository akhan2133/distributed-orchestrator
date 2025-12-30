# Distributed Failure Orchestrator & Reliability Analyzer

This project is a mini chaos-engineering / reliability testing framework.

It lets you:

- spin up a distributed system (HTTP services or Redis nodes)
- inject failures (kill / restart nodes)
- generate synthetic load
- collect metrics
- automatically detect anomalies & recovery time, and
- optionally ask an LLM to write a human summary of what happened.

It also includes visualization tools for throughput and baseline-vs-run comparisons.

The goal was to build something that feels like a tiny version of real chaos frameworks (e.g., Chaos Mesh). But understandable and runnable on a laptop.

---

## Features:
### Scenario-driven failure orchestration
Runs are defined in YAML:
- warmup load
- fail a node
- continue load
- restart nodes

## Works with two backends
- HTTP service cluster
- Redis replicated setup

## Load generation
- Configurable RPS, runs in background threads.

### Metrics pipeline
Writes CSV logs for each run:
- timestamp
- latency
- HTTP/Redis success/failure
- error messages

Aggregated later into summaries

### Anomaly detection
Automatically finds:
- periods of degraded throughput
- elevated error rates
- estimated recovery time
- Uses tunable thresholds (via config).

### Visualizations  
- throughput over time (with anomaly shading)
- baseline vs failure run comparison charts

### LLM summaries (optional)
Uses Groq LLM to generate readable diagnostic reports.

---

### Repository Structure
orchestrator/
  coordinator.py          # orchestrates scenarios + agents
  agents.py               # load agents (HTTP + Redis) and control agent
  analysis.py             # summarization + anomaly detection
  llm_summary.py          # optional Groq-based narrative summary
  visualize_throughput.py # plot throughput curve
  visualize_compare.py    # compare baseline vs failure
  config.yaml             # tuning knobs (thresholds, LLM toggle, etc.)
  scenarios/
    baseline.yaml
    failure.yaml
runs/
  ... (auto-populated per run)

--- 

### Getting started
## Install dependencies 
```bash
pip install -r requirements.txt
```
## Bring up the cluster(s)
HTTP or Redis (depending on scenario)
```bash
docker compose up -d
```

---

### Running experiments
## Baseline run
```bash
python -m orchestrator.coordinator \
  --scenario scenarios/baseline.yaml \
  --run-id baseline1 \
  --mode http
```

## Failure-injection run
```bash
python -m orchestrator.coordinator \
  --scenario scenarios/failure.yaml \
  --run-id run1 \
  --mode http
```

---

### Analyze Results
## Compute comparison & anomaly detection
```bash
python -m orchestrator.compare \
  --baseline-id baseline1 \
  --run-id run1
```

Output JSON includes:
- throughput change
- latency shifts
- anomaly windows
- recovery time estimate

---

### Optional LLM summary (Groq)
Set your key:
```bash
export GROQ_API_KEY=your-key
```

Then run:
```bash
python -m orchestrator.llm_summary \
  --baseline-id baseline1 \
  --run-id run1
```
Model will produce a readable reliability report.

### Visualizations 
## Throughput timeline
```bash
python -m orchestrator.visualize_throughput --run-id run1
```

creates:

```bash
runs/run1/throughput.png
```

## Baseline vs Failure comparison
```bash
python -m orchestrator.visualize_compare \
  --baseline-id baseline1 \
  --run-id run1
```

creates:

```bash
runs/run1/compare.png
```

---

### Configuration (config.yaml)
```bash
# Target services 
http_nodes:
  - http://localhost:8001
  - http://localhost:8002
  - http://localhost:8003

redis_nodes:
  - redis://localhost:6379
  - redis://localhost:6380

# Failure detection tuning 
anomaly_detection:
  # Fractional drop compared to baseline
  throughput_drop_threshold: 0.5 # 50%
  error_rate_threshold: 0.1 # 10%
  warmup_ignore_sec: 5 # ignore early noise

# LLM settings 
llm:
  provider: groq
  model: llama-3.3-70b-versatile
  temperature: 0.2
  max_words: 300
  enabled: true
```

All thresholds and behavior are tunable (no code changes needed)

---

### Testing strategy
Current tests were validated by:
- running HTTP scenarios
- running Redis scenarios
- verifying anomaly detection behavior
- checking generated plots
- validating LLM summaries

Future improvements could include:
- CI automation
- mock-based unit tests for anomaly logic
- container health checks
- scenario replay tests

