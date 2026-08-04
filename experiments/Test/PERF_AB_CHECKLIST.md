# Test Performance A/B Checklist

## Goal
Reduce wall-clock runtime while preserving evacuation behavior quality.

## Variants
- Baseline: experiments/Test/config.yaml
- Variant A: experiments/Test/config_perf_A.yaml
  - decision_interval: 30s
  - min_redecision_interval_seconds: 30s
  - immediate_redecision_on_transfer: false
- Variant B: experiments/Test/config_perf_B.yaml
  - Variant A settings plus:
  - llm.reasoning_effort: low
  - llm.max_completion_tokens: 1000

## Run Commands
Run from monument-evacuation repo root.

```bash
python run_experiment.py experiments/Test/config.yaml --no-viewer --no-spatial-viewer --no-video
python run_experiment.py experiments/Test/config_perf_A.yaml --no-viewer --no-spatial-viewer --no-video
python run_experiment.py experiments/Test/config_perf_B.yaml --no-viewer --no-spatial-viewer --no-video
```

## Collect Key Metrics
Replace RUN_DIR with the latest run folder path (for example results/Test/run_YYYYMMDD_HHMMSS).

```bash
RUN_DIR="results/Test/run_YYYYMMDD_HHMMSS"

# Wall-clock profile summary
cat "$RUN_DIR/performance_report.txt"

# LLM financial summary
cat "$RUN_DIR/financial_report.txt"

# Core aggregates from prompt logs
jq -s 'map({
  dur_ms: (.latency_checkpoint.total_duration_ms // .usage.latency_checkpoint.total_duration_ms // 0),
  pt: .usage.prompt_tokens,
  ct: .usage.completion_tokens,
  tt: .usage.total_tokens
}) | {
  calls: length,
  prompt_tokens: (map(.pt) | add),
  completion_tokens: (map(.ct) | add),
  total_tokens: (map(.tt) | add),
  avg_duration_ms: ((map(.dur_ms) | add) / length),
  p90_duration_ms: (map(.dur_ms) | sort | .[(length * 0.9 | floor)])
}' "$RUN_DIR/llm_prompt_log.jsonl"

# Decision loop/cache summary from simulation log
grep -nE 'LLM CALL OPTIMIZATION SUMMARY|LLM calls made|LLM calls skipped|Skip rate' "$RUN_DIR/simulation.log"
```

## Compare Behavioral Stability
Quick checks to ensure performance gains are not breaking behavior.

```bash
RUN_DIR="results/Test/run_YYYYMMDD_HHMMSS"

# Route-change volume
grep -n 'Total route changes' "$RUN_DIR/route_changes.txt"

# Wait behavior volume
grep -n 'Total wait events' "$RUN_DIR/wait_behavior.txt"

# Message activity volume
grep -nE 'Total messages sent|Total message deliveries' "$RUN_DIR/message_analytics.txt"
```

## Suggested Success Criteria
- Wall-clock runtime reduced by at least 35% vs baseline.
- LLM calls reduced by at least 30% vs baseline.
- Completion tokens reduced by at least 50% vs baseline for Variant B.
- Route-change and wait-event totals remain within about 15-20% of baseline unless behavior shift is intentional.
