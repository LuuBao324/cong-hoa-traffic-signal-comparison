# Published methods

The registry in `traffic_study/paper_methods.py` contains ten nonlearning methods from seven papers published from 2023 onward. Fixed-time is the eleventh method and provides a shared reference. The four variants from Zoabi and Haddad (2024) belong to one paper.

The decision rules are in `traffic_study/pure_controllers.py`. The common observation and signal-transition code is in `research_controllers.py` and `pressure_controllers.py` in the same package. The retired G2P, fuzzy, smoothing, occupancy and QD branches have been removed from the active implementation.

See [controller implementation and verification](PURE_NONRL_AUDIT.md) for formulas, source links, parameters and explicit network adaptations. The same references are recorded in experiment plans.

The earlier 249-run trial is retained in `historical/paper_dataset_final`. The paused sublane experiment is in `tan_binh_2026/dataset_pure_nonrl`. Newly generated lane-based experiments use a separate folder and signature.
