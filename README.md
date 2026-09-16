# Monument Station Evacuation Study

Experiment series (E1–E5) examining the effect of different information and
intervention strategies on pedestrian evacuation from Monument Station, Newcastle.

## Experiments

| ID | Scenario |
|----|----------|
| E1 | Fire alarm only |
| E2 | Station staff direct the evacuation |
| E3 | Public address system used to tell people to evacuate |
| E4 | Staff assist + PA tells people to board trains to evacuate |
| E5 | PA gives detailed information on fire location and actions required |

## Running an experiment

```bash
python run_experiment.py experiments/E1/config.yaml
```

Results are written to `results/<experiment_id>/<timestamp>/`.

To start at a specific time of day, skipping earlier passenger and event
schedules, use `--start-time`:

```bash
python run_experiment.py experiments/Calibration/config.yaml \
	--start-time 07:30 --no-viewer --no-spatial-viewer --no-video
```

`--max-steps` remains elapsed duration from that start. With Calibration's
`dt: 0.1`, for example, `--max-steps 36000` runs one hour from 07:30 to 08:30.

## Comparing results

```bash
python analysis/compare_experiments.py
```

## Dependencies

- [evacusim](https://github.com/your-org/evacusim) — the simulation framework
- Monument Station geometry in `geometry/monument/`

## Setup

```bash
pip install -e .
cp .env.example .env   # add Azure OpenAI credentials
```
