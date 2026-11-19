# Dataset acceptance audit

Source: dataset_cong_hoa
Status: NOT READY

| Check | Pass | Evidence |
|---|---|---|
| paper_eligibility | yes | Each research method maps to a 2023+ nonlearning paper; four named ECC2024 variants share one paper; fixed-time is separate. |
| no_rl_or_training | yes | No RL branch is extracted from a hybrid paper in the current registry. |
| method_coverage | yes | 10/10 research methods + baseline |
| demand_coverage | yes | 3/3 demand levels |
| seed_coverage | yes | 4/4 seeds |
| run_coverage | yes | 132/132 complete runs |
| unique_probe_rows | yes | 0 duplicates |
| four_probes_per_run | yes | 528 probe rows / 132 runs |
| all_probes_arrived | no | 34 unfinished probes |
| no_collision_or_teleport | no | 95 affected runs, 68 invalid probes |
| signal_and_connection_warnings | yes | 0 warnings |
| paired_baselines | no | 460/528 valid paired rows |
| transition_policy_documented | yes | Each method must record its transition policy. Stored all-red phases and optional added clearance are distinct; documentation is not a real-world calibration certificate. |
| planned_grid_complete | yes | 132/132 planned combinations |

No dashboard or final comparison should be treated as validated until acceptance checks pass.
Signal warnings require inspection; their presence alone does not establish the cause of each collision.
