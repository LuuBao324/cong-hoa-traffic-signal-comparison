# Dataset design and verification

## Demand reference

The user initially estimated 20 vehicles/second for both Cong Hoa directions combined from a ten-minute video near Cong Hoa Garden and Duong 20 Cong Hoa. The estimate is retained in the observation metadata. The current experimental reference requests 36,000 corridor-related journeys/hour, corresponding to the subsequently requested ten journeys/second. A corridor-related journey uses at least one Cong Hoa segment. A cross-section detector records realised passage separately, beside the Duong 20 intersection.

Ordinary traffic is generated across the map. Only the four tracked vehicles have imposed full-corridor journeys. Side-road and T3 groups allow ordinary traffic to enter, leave and cross Cong Hoa. Every ordinary route terminates at a selected peripheral outlet. The whole-map reference is 67,500 vehicles/hour, comprising 36,000 corridor-related journeys and 31,500 journeys elsewhere. The latter allocation is an engineering assumption. These requested inputs and the observed passage estimate have separate meanings.

The motorcycle/car/truck/bus mix is 76/21/2/1 percent. Origin preference weights are 50% boundary, 28% general interior, 20% signalised side approaches and 2% T3. Weights are normalised over available corridor and non-corridor route pools. Actual origin counts are recorded by class. First corridor-exit roads are weighted by their permitted movement lanes. Counts are rounded by class.

## Scale and seed

`demand_scale` multiplies requested demand. A seed changes departure jitter and route selection within a demand level. The same seed also controls SUMO randomness. Every method in a scenario reads the same frozen vehicle routes, departures, vehicle types, network and simulator seed.

Both scale and seed are required for the proposed multi-demand experiment. Seeds provide repeated observations within each demand level. Scales expose controller behaviour under different loads.

The batch planner currently defines the following candidate levels.

| Scale | Corridor-related journeys/h | Journeys/h elsewhere | Total requested vehicles/h |
|---:|---:|---:|---:|
| 0.10 | 3,600 | 3,150 | 6,750 |
| 0.50 | 18,000 | 15,750 | 33,750 |
| 1.00 | 36,000 | 31,500 | 67,500 |

These nominal rates are approximate because counts are rounded by vehicle class. Four tracked vehicles are added to each scenario. Requested demand is spread over 1,800 seconds. Generated vehicle totals include departures scheduled after the observation stops. Actual insertion counts are reported separately. The original video estimate remains fixed in the observation metadata.

Check insertion, completion and congestion at each candidate level before executing the large dataset. At high demand, unfinished journeys are recorded as censored observations.

The earlier controller verification cohort used scale 0.025 and seed 100 with the previous allocation. Its requested corridor flow was approximately 1,350 vehicles/hour/direction and background flow approximately 675 vehicles/hour, subject to class rounding. Its saved results belong to that earlier configuration.

## Experimental units and comparisons

Ten research methods from seven papers are registered in `traffic_study/paper_methods.py`, with four related variants from Zoabi and Haddad (2024). Fixed-time is an additional reference. Source equations and SUMO adapter assumptions are documented in `PURE_NONRL_AUDIT.md`.

The complete plan uses three demand levels (0.1, 0.5 and 1.0), twenty-four seeds (100–123) and eleven methods, giving 792 runs. These contain 720 research-controller runs and 72 fixed-time references, with up to 3,168 probe rows. The balanced interim subset uses four seeds (100–103), giving 132 runs and up to 528 probe rows. A probe row describes one journey. The independent repetition unit is the scenario seed.

The four probes are car/outer, motorcycle/outer, car/centre and motorcycle/centre, travelling from the beginning to the end of Cong Hoa towards Truong Chinh. A run ends when all four arrive or reaches the 1,600-second guard. Probe departures are scheduled at 300 seconds. Travel time begins at actual insertion. Departure delay is reported separately. Waiting time is already included in travel time.

Every pair is matched by demand level, seed and probe identity. Frozen-input digest, simulator backend, engine version, vehicle type and route variant must also match. The saved `all_four_arrived` policy permits comparisons when both runs complete all four tracked journeys. Whole-run collision and teleport counts remain visible, together with `clean_run` and probe-specific event flags. `pairwise.csv` covers all method pairs, giving up to 15,840 rows in the complete grid. Its signed difference is `travel_time_a - travel_time_b`. Positive `improvement_a_vs_b_percent` indicates that A is faster.

Analyse each demand level, vehicle type and route variant separately. `summary.csv` reports means and sample standard deviations across seeds. Network snapshot counts and controller switch totals have method-dependent observation horizons.

## Columns

| Role | Columns |
|---|---|
| Identity | `run_id`, `scenario`, `method`, `probe_id`, `seed` |
| Demand inputs | `demand_scale`, `corridor_related_requested_vph`, `corridor_related_generated_vehicles`, `map_requested_vph`, `demand_duration_s`, four vehicle shares |
| Journey inputs | `vehicle_type`, `route_variant`, `probe_requested_depart_s` |
| Journey outcomes | `travel_time_s`, `waiting_time_s`, `depart_delay_s`, `time_loss_s`, `waiting_count`, `route_length_m`, `mean_speed_kmh` |
| Completion and validity | `departed`, `completed`, `censored`, `all_four_arrived`, `valid_for_comparison`, `paired_valid`, `clean_run`, `probe_teleported`, `probe_collision`, `controller_exercised` |
| Network diagnostics | `collisions`, `teleports`, `inserted_network_vehicles`, `arrived_network_vehicles`, `running_network_vehicles`, `pending_network_vehicles`, `halted_network_vehicles`, `mean_network_speed_mps` |
| Provenance | `network_sha256`, `input_sha256`, `backend`, `engine_version`, `actual_end_s`, `stop_reason` |

Use physical units for these descriptive comparisons. Measurements retain physical units. Demand scaling changes the simulated load.

Paper links and publication years are stored in registry and manifests. Analysis CSV exports contain traffic and experiment fields. Quality diagnostics support filtering and audit even when they are hidden in dashboard views.

## Input integrity

Route, signal and configuration XML files are written to temporary files in the destination folder, parsed, and then atomically replaced. A failed write preserves the previous destination file. Each generated configuration sets `route-steps=0`, so SUMO loads the full route input at startup. Each batch scenario prepares its inputs once before its method runs. Every method writes detector output into its own result folder. The frozen-input digest covers the configuration and referenced network, route and additional-input files.

## Verification before the large batch

1. Run formula and adapter regression tests.
2. Freeze the current network, code, parameters and package versions.
3. Execute the eleven-method low-load cohort against identical inputs.
4. Inspect controller exercise, probe completion, collisions, teleports, signal warnings and input pairing.
5. Review the measured comparison table and then test feasibility of higher demand levels.

The current cohort is `tan_binh_2026/dataset_cong_hoa`. Earlier model checks and datasets retain their own input signatures and results. The behaviour-model comparison is recorded in `tan_binh_2026/model_validation_20261113/MODEL_SELECTION.json`.

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests
.\.venv\Scripts\python.exe -X utf8 scripts/resume_dataset.py --source dataset_cong_hoa
```

The second command resumes the saved execution grid while checking its source signature. Column definitions and missing-value counts are exported to `dataset_metadata.json`. Execution coverage, comparison eligibility and the strict collision-free audit are reported separately.


## Export and movement-model version

`dataset.csv` is the main journey-level table. `pairwise.csv` and `summary.csv` provide derived comparisons. `dataset_metadata.json` describes the columns, missing values and the saved plan. All three tables are assembled by `traffic_study/dataset.py` from recorded results. The dashboard reads `dataset.csv`.

Current scenarios use Krauss car-following, a one-second desired headway and LC2013 lane-based movement. Motorcycles travel in single file within a lane and can change lanes. The simulation step is 0.25 seconds. Routes retain entering-lane state and are checked against individual lane width and turn connections. Multiple lane changes use a 30 m planning margin per changed lane. Unmeasured traffic signals use protected groups, each with 30 seconds green and three seconds yellow. These engineering assumptions apply to every method.

Collision detection uses physical contact/overlap (`collision.mingap-factor=0`), including checks inside junctions (`collision.check-junctions=true`). The policy is recorded in each result. The strict audit retains a zero-event criterion even though the user-selected comparison policy includes flagged runs with four completed probes.


## Current execution schedule

Execution proceeds through an eleven-method, one-seed check, the balanced four-seed interim subset and the complete twenty-four-seed grid. Completed runs are reused when signatures and the simulation guard match. Paused runs are excluded until completed on resume. The interim report must retain its seed count when used in writing.
