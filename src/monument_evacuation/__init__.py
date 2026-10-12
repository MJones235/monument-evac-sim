"""Monument Station evacuation study: Proulx (1991) drills, LLM vs rule-based agents.

The flow of the study::

    experiments/                 inputs: base.yaml + a scenario + a decision engine
        base.yaml                  the station, staff and defaults shared by every run
        scenarios/E1..E5.yaml      what each Proulx drill changes
        engines/*.yaml             llm or rule_based
        calibration/*.yaml         normal-day runs against observed usage
        batches/*.yaml             scenario x engine x seed matrices
          │
          ▼  monument run / monument batch          (run.py, batch.py)
    evacusim                     the simulation engine
          │
          ▼
    results/<scenario>/run_<time>_<engine>_s<seed>/    outputs (manifest.json first)
          │
          ▼  monument analyse ...                    (analysis/)
    figures and tables

Command line: ``monument --help`` (see cli.py).
"""
