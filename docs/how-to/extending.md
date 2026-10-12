# Adding a scenario or an engine

## A scenario

1. Create `experiments/scenarios/<name>.yaml` with `extends: ../base.yaml`,
   and only what differs: `agents.count`, `events`, `systems`.
2. Give every warning a cue label (`cue`, `zone_cues`, `cues_by_zone`)
   following the [labelling rule](../scenarios/index.md#cue-labels-rule-based-engine).
   Without them the rule engine ignores the warning.
3. Check it runs: `monument run <name> --engine rule_based --max-steps 2000`.
   An unknown key fails at load, so a typo cannot slip through.
4. If it has observed outcomes, add them to `analysis/proulx_1991.py`, or a
   module like it, so it can be scored.
5. Add a page under `docs/scenarios/` and to the batch file.

## An engine configuration

An engine overlay is a config file merged on top of the scenario. A variant,
such as another LLM temperature or fitted rule weights, is a new file in
`experiments/engines/`, used with `--engine <file name>`.

A new *kind* of engine is written in evacusim: subclass `DecisionEngine` and
add a config model. See evacusim's [decision engines](https://github.com/MJones235/llm-evacuation-sim/blob/main/docs/concepts/decision-engines.md).
