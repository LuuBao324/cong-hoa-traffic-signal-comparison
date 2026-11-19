# Cong Hoa Traffic Signal Study

A SUMO simulation study comparing ten nonlearning signal-control methods and a fixed-time reference on Cong Hoa Road in Tan Binh, Ho Chi Minh City. The project includes a Python experiment runner, a recorded dataset, an analysis notebook and an English Streamlit dashboard.

The selected paper dataset contains **132 runs and 528 tracked journeys**, covering three demand scales, four seeds and eleven methods. Each run tracks a car and motorcycle on both the outer and central paths.

> The saved acceptance audit is **false**. There are 494 completed journeys, 34 censored journeys, 674 recorded collisions and 674 teleports. These results support an exploratory simulation comparison. Completion, event flags and matched sample counts remain visible in the analysis.

## Repository structure

```text
app/                         Streamlit dashboard
traffic_study/               Simulation, demand, controllers and dataset logic
scripts/                     Preparation, export, validation and resume utilities
tests/                       Controller and experiment-integrity checks
analysis/
  cong_hoa_analysis.ipynb     Executed analysis notebook
  outputs/cong_hoa_132_runs/  Tables, figures and analysis provenance
docs/                        Method assumptions, evidence and usage guides
output/defense/              Presentation and English speaking/Q&A guide
tan_binh_2026/
  tan_binh.net.xml.gz        Current manually revised network
  tan_binh.sumocfg           Network-view configuration
  source/                   OSM extract and original SUMO Wizard network
  signals/                  Survey records and signal mappings
  dataset_cong_hoa/
    checkpoints/132_runs/   Frozen CSV tables, plan and audit
    inputs/d0.5_s100/        One complete frozen input scenario
    runs/                   Result JSON for the 132 recorded runs
run_fixed_time.py            Fixed-time command-line entry point
compare_pressure.py          Controller comparison entry point
batch_experiments.py         Multi-demand/seed experiment entry point
requirements*.txt            Simulation, dashboard and analysis dependencies
```

Run commands from the repository root. Python 3.13 was used for the recorded experiment. SUMO packages are pinned to version 1.28.0.

## Dashboard quick start

Create a dashboard environment in PowerShell.

```powershell
py -3.13 -m venv .venv-dashboard
.\.venv-dashboard\Scripts\python.exe -m pip install -r requirements-dashboard.txt
.\.venv-dashboard\Scripts\python.exe -m streamlit run app\streamlit_app.py --server.address 127.0.0.1 --server.port 8501
```

Open [http://127.0.0.1:8501](http://127.0.0.1:8501). Stop the server with Ctrl+C. The dashboard reads the included checkpoint and provides completion, journey-time, pairwise-comparison and provenance views. Filter by method, demand, seed, vehicle and path. CSV downloads reflect the current selection. See [the dashboard guide](docs/STREAMLIT.md).

## Analyse the recorded dataset

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-analysis.txt
```

Open [analysis/cong_hoa_analysis.ipynb](analysis/cong_hoa_analysis.ipynb) in VS Code or Jupyter and select the `.venv` kernel. Saved outputs are included. The notebook reads the frozen checkpoint and writes analysis outputs under `analysis/outputs/cong_hoa_132_runs/`.

The checkpoint contains the following tables.

| File | Purpose |
|---|---|
| `dataset.csv` | One record per tracked journey, including incomplete journeys |
| `pairwise.csv` | Comparisons between methods under matched inputs |
| `summary.csv` | Aggregated outcomes within demand, vehicle and path groups |
| `dataset_metadata.json` | Column definitions and recorded experiment metadata |
| `plan.json` | Selected methods, demand scales, seeds and signatures |
| `snapshot.json` | Checkpoint coverage and event counts |
| `acceptance.json` | Saved quality audit |

The default analysis requires all four tracked vehicles in a run to arrive. Collision and teleport events remain recorded. Paired comparisons also require matching inputs, simulator version, vehicle and path. The four probes in one run share a seed. At most four seed observations are available per method, demand, vehicle and path group.

## Control methods

| Method | Source |
|---|---|
| Switching-Loss Max-Pressure | Sun et al. (2025) |
| Coordinated Max-Pressure, C-MP | Ahmed, Liu and Gayah (2025) |
| Total-Delay-Based Max-Pressure, TD-MP | Liu and Gayah (2023) |
| Connected-Vehicle Max-Pressure, CV-MP | Tan et al., retained 2025 preprint; journal publication 2026 |
| CN-MP | Zoabi and Haddad (2024) |
| WNCN-MP | Zoabi and Haddad (2024) |
| W*NCN-MP | Zoabi and Haddad (2024) |
| W*CN-MP | Zoabi and Haddad (2024) |
| Queue-responsive allocation | Albdairi and Almusawi (2026) |
| Coordinated auction | Muzzini and Montangero (2024) |

Fixed-time is the additional reference. Four formulations share one paper, giving ten research methods from seven papers. Source links are in [the registry](traffic_study/paper_methods.py), with implementation assumptions in [the controller audit](docs/PURE_NONRL_AUDIT.md).

## Inspect the network

After installing simulation dependencies, open the current network in NetEdit or SUMO GUI.

```powershell
.\.venv\Scripts\netedit.exe --sumo-net-file .\tan_binh_2026\tan_binh.net.xml.gz
.\.venv\Scripts\sumo-gui.exe -c .\tan_binh_2026\tan_binh.sumocfg
```

The included frozen example opens a traffic scenario at demand scale 0.5 and seed 100.

```powershell
.\.venv\Scripts\sumo-gui.exe -c .\tan_binh_2026\dataset_cong_hoa\inputs\d0.5_s100\view.sumocfg
```

Adaptive methods require the Python controller runner during simulation. A saved GUI configuration loads its stored signal programme.

## Run a new experiment

The lane-based model uses Krauss vehicle following, LC2013 lane changing, a one-second desired headway and a 0.25-second simulation step. The configured composition is 76% motorcycles, 21% cars, 2% trucks and 1% buses.

Prepare a separate experiment with three demand scales and one seed.

```powershell
.\.venv\Scripts\python.exe -X utf8 batch_experiments.py --output tan_binh_2026/new_experiment --scales 0.1 0.5 1.0 --seeds 102 --end 1600
```

Add `--execute --workers 1` to execute the prepared experiment. Each method stops after all four tracked vehicles arrive or at the 1,600-second guard. The reference input requests 36,000 corridor-related journeys/hour plus 31,500 journeys/hour elsewhere. Scales are scenario multipliers. Requested input and realised passage at a detector are different measurements.

The reported field count is approximately 3,000 vehicles in ten minutes in one direction near Cong Hoa Garden on 14 October. The saved metadata leaves the year and time band unconfirmed. Equal opposite-direction flow and background demand are scenario assumptions. See [the experiment design](docs/DATASET_EXPERIMENT.md) and the checkpoint's `field_observation.json`.

## Run checks

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests
```

## Data provenance and repository scope

The repository includes the selected checkpoint, compact underlying results and one complete frozen input scenario. Full local histories, all other frozen route inputs, full-population tripinfo XML, detailed simulator logs, virtual environments and temporary build files are excluded by `.gitignore`. Reanalysis of the included checkpoint is available after cloning. Replaying every original run requires the remaining original frozen inputs. New experiment preparation generates a separate experiment.

Street geometry was imported from OpenStreetMap and manually revised in SUMO/NetEdit. Map data © OpenStreetMap contributors, available under the [Open Database License](https://opendatacommons.org/licenses/odbl/1-0/). See [OpenStreetMap copyright and attribution](https://www.openstreetmap.org/copyright). The network inventory describes the prepared simulation model. The reported controller count is distinct from the field-survey coverage.

See [repository contents and GitHub upload instructions](docs/REPOSITORY.md), [implementation details](docs/PAPER_IMPLEMENTATIONS.md) and [the defense guide](output/defense/Defence_Script_and_QA.md).
