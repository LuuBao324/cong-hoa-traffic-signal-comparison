# Local Streamlit dashboard

## Start and stop

Run from the project root.

```powershell
.\.venv-dashboard\Scripts\python.exe -m streamlit run app\streamlit_app.py --server.address 127.0.0.1 --server.port 8501
```

Open http://127.0.0.1:8501. Stop the server with Ctrl+C.

## Data source

The default source is the selected 132-run checkpoint at `tan_binh_2026/dataset_cong_hoa/checkpoints/132_runs`. Other recorded experiments remain selectable. The dashboard reads saved CSV and JSON files. Metadata and plan signatures must match. Acceptance warnings remain visible, including a warning when a saved audit covers an earlier export.

## Views

- Completion reports all-four run completion and arrival counts before the inclusion policy is applied.
- Journey time reports means, sample standard deviations, medians and seed counts for travel and waiting time. Individual seed distributions are optional. Matched fixed-time improvements are calculated per seed before averaging.
- Pairwise comparison compares all selected methods at one demand scale. The matrix shows mean A minus B in seconds and matched n. Blue favours A, red favours B and grey off-diagonal cells show n = 0. A detailed comparison lists the seed observations for the chosen A and B.
- Data and provenance provides filtered journey downloads, simulation-event counts, exposure windows, demand assumptions, source paths and hashes.

Select one vehicle type and one path at a time. Demand levels remain separate in summaries. Methods and seeds can be filtered. Four vehicles in a run share the same seed.

## Inclusion policies

The default policy requires all four tracked vehicles to arrive. A second policy excludes directly affected tracked observations when the recorded dataset contains those flags. The strict policy also requires zero recorded network collisions and teleports. A pair requires both observations to meet the policy and matching input hashes, engine version, tracked vehicle and path.

Groups with zero eligible observations remain in tables with unavailable means. A single seed has no estimated sample standard deviation. Departure delay is separate from travel time. Event totals are counted once per run, and raw totals have unequal exposure because simulation end times vary.

## Exports

Downloads contain the currently filtered records or calculated summaries. Bibliographic information remains in the research documentation. Source measurements retain their recorded values.

## Environment

The existing `.venv-dashboard` environment uses `requirements-dashboard.txt`. The SUMO and notebook environments remain available separately. The defense walkthrough is in `output/defense/Defence_Script_and_QA.md`.
