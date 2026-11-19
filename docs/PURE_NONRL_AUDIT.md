# Controller implementation and verification

The study compares ten nonlearning methods from seven papers with one fixed-time reference. Four ECC 2024 variants share the paper by Zoabi and Haddad. The registered decision rules are implemented in `traffic_study/pure_controllers.py`. Shared observations and transitions are in `research_controllers.py` and `pressure_controllers.py` in the same package.

## Source rules and modelling assumptions

- Switching-Loss MP uses maximum movement pressure, protection factor 1+k, and lane-level discharge and receiving-space estimates. The configured k=0.2, startup loss of 2 s, saturation flow of 0.5 vehicles/s/lane, storage spacing of 6 m, and extensions of 1–60 s are modelling assumptions.
- C-MP applies downstream speed weighting separately to each movement before summing with turning proportions. Alpha and beta are both 1.
- TD-MP uses a 5 s decision interval and the switching factor as printed in Equation 1. CV-MP uses its distinct switching factor and a 10 s interval. The CV source version is the 2025 preprint retained with the project.
- Queue-responsive allocation follows proportional allocation followed by independent clamps, review every 120 s, smoothing over five targets, and changes limited to 5 s. The paper leaves the score-to-budget scale unspecified. The implementation assumes 1 s per score unit.
- The ECC variants use the published lane-normalised and capacity-weighted pressure formulations. Their shared saturation and storage assumptions are recorded above.
- Coordinated auction uses deterministic initial budgets from 1 to 100, propagation over five downstream signals, an ETA threshold of 10 s and starvation protection at 120 s. The minimum starvation bonus is 30,000 and increases with storage bounds. Algorithm 3 prints a starvation inequality inconsistent with the accompanying prose. The implementation follows the prose and uses >=. Propagated bids follow the 0.5^p factor in Algorithm 1, starting at p=1. A future bid is assigned once to a feasible lane. The winning lane is mapped to an existing compatible signal phase, with its turning intentions used for the tie-break.
- Observations are sampled at 1 Hz. Turning proportions come from the frozen vehicle routes. CV-MP and auction assume full simulated vehicle information. No occupancy or emergency-priority scenario is required by the current demand.
- Adaptive transitions use 3 s yellow and zero additional all-red. Common green movements remain green during transitions. Fixed-time runs use their stored surveyed and default phases. Existing compatible phases define the controller choices.

The source rules are adapted to this manually edited network. Differences in geometry, vehicle behaviour, phase sets, observations and parameters affect transferability of published performance figures. Tests check the equations and adapter behaviour separately from simulation acceptance.

## Submission movement model

Newly prepared scenarios use Krauss car-following and LC2013 lane-changing. Motorcycles follow one another within each lane and can change to adjacent lanes for speed gain or route following. Sublane movement and parallel filtering within one lane are disabled. This choice was requested on 12 November 2026. It simplifies lateral behaviour and changes road capacity. Earlier recorded sublane datasets represent a different experimental configuration.

The new model requires fresh runs in a separate experiment folder. Saved measurements and their recorded execution signatures identify the configuration that produced them.

## Recorded checks from earlier source revisions

The sections below describe the saved sublane checks before the submission cleanup and lane-based change. Their source signatures and model settings belong to those recorded runs.

### Review on 12 November 2026

The registry retains ten nonlearning methods and one fixed-time reference. The numerical checks use the source equations and their stated observation scenarios.

| Method | Source rule checked | Current timing/observation adapter |
|---|---|---|
| Switching-Loss MP | Sun et al. (2025), maximum movement pressure, current-phase protection and lane-based extension | Stopped-vehicle queues, saturation 0.5 veh/s/lane, k=0.2, startup 2s, extension clipped to 1–60s |
| C-MP | Ahmed et al. (2025), Eq.6–8, movement-specific downstream speed | alpha=1, beta=1, 10s decision slots, full movement observation |
| TD-MP | Liu and Gayah (2023), cumulative upstream delay, recent downstream delay integral and Eq.1 loss factor | 5s decision slots including yellow; printed source factor 1-(T-e)/T is retained |
| CV-MP | Tan et al., 2025 preprint Eq.8–9, normalised link travel time | Full connected observation; network speed limit in free-flow time; switching factor (T0-Ty)/T0; 10s slots |
| Queue-responsive | Albdairi and Almusawi (2026), Algorithm1 | Approach cumulative waiting, 120s reviews, initial green 20s, 15–60s bounds, five-target smoothing and 5s change bound |
| CN-MP | Zoabi and Haddad (2024), Eq.4/6 | Movement saturation divided by lane count; 10s slots |
| WNCN-MP | Zoabi and Haddad (2024), Eq.4/7 | Weight and saturation normalised by lane count; 10s slots |
| W*CN-MP | Zoabi and Haddad (2024), Eq.8/6 | Capacity-per-lane weights and saturation normalisation; 10s slots |
| W*NCN-MP | Zoabi and Haddad (2024), Eq.8/7 | Capacity-per-lane weights and both lane normalisations; 10s slots |
| Coordinated auction | Muzzini and Montangero (2024), Algorithms1–3 | Full connected scenario, deterministic budgets, lane winner mapped to an existing compatible phase; 10s slots |

The auction and CV-MP tests use complete simulated vehicle observation. The selected auction scenario has zero non-connected vehicles and zero emergency vehicles. Its default-bid arithmetic is unit-tested. Shared-turn-lane actuation uses existing compatible SUMO phases. The QR source specifies four phases; the adapter applies the same proportional/clamp/smoothing rule to the available phase count.

C-MP alpha/beta, storage spacing of 6m, saturation, queue threshold and the QR score-to-budget scale remain explicit experiment parameters. Source networks, lane layouts, vehicle mixes and published performance values belong to their respective studies. The current checks cover the selected control rules within this SUMO adapter.

The 2026 journal publication of CV-MP is catalogued at https://doi.org/10.1016/j.trb.2025.103387. Formula checking here uses the locally available 2025 preprint. The method identifier cv_mp_2025 records that source version.

### Corrections applied

- CV-MP and TD-MP now use the current network free-flow limit in their time metrics.
- CV-MP applies the phase-switch capacity discount stated in the source simulation protocol.
- Discrete decision slots include the 3s yellow interval. A 10s switching slot contains 3s yellow and 7s target green. TD-MP uses 3s yellow and 2s target green in a 5s slot.
- Common green movements retain green during phase changes. Departing movements receive yellow and entering movements remain red until activation.
- Queue-responsive uses accumulated waiting on the current approach, subtracting the waiting recorded at approach entry.
- Observation remains 1Hz independently of the numerical step length.
- Generated vehicles choose a route-compatible departure lane and use lcStrategic=5 to prepare for route-required lane changes. These vehicle settings are common to every method and are modelling assumptions.
- XML files are published through parsed temporary files and the complete route input is preloaded at startup.
- Analysis CSV exports omit bibliography fields. Source references are retained in manifests and this document.

### Verification evidence

Regression tests cover the ECC numerical example, downstream C-MP groups, the distinct TD/CV switching factors, queue waiting, busiest-lane extension, shared-green transitions, decision-slot timing, seed/input pairing and interrupted XML writes. The current suite has 39 passing tests. Current-revision full-route cohort outcomes are written to tan_binh_2026/verification_20261112. Technical execution, journey validity and final multi-demand coverage are audited separately.


### Completed cohort and export check

The measured low-load cohort completed eleven methods and 44 tracked journeys. Canonical input selection yields 220 method-pair rows. Twenty probe rows and forty method-pair rows pass the input/version/completion/event pairing rule. Six runs recorded collision or teleport events, and two runs emitted selected internal-lane warnings. Large-batch readiness is false.

The original recorded hash lists included detector output. The exporter corrects pairing by selecting actual input files from those original lists. Raw measurements and execution signatures are retained. The controller core source matches the measured revision. A separate fixed-time/CV-MP plumbing check verifies isolated detector output and unchanged shared input files after the output-path correction. Details are in `tan_binh_2026/verification_20261112/VERIFICATION.md`.


### Internal lane repair and safety investigation, 12 November 2026

Five internal edges in the source network had repeated numeric lane indexes. Six lane indexes were corrected to follow the existing lane IDs and ordering. Connection references have no out-of-range lane indexes after repair. This operation changes lane index attributes only. It can be repeated with `python run_fixed_time.py --repair-network`.

A separate cohort is stored in `tan_binh_2026/verification_safety_20261112`. It uses the same requested scale 0.025 and seed 100 as the earlier technical cohort, with newly prepared inputs. Its common vehicle assumptions increase lateral clearance to 0.6 m and set jmAdvance=0, jmTimegapMinor=1.5 s, jmExtraGap=1 m and jmSigmaMinor=0. These settings are engineering assumptions under investigation. They require calibration before a field-performance claim. Forty-one regression tests pass, including idempotent lane-index repair and rejection of ambiguous lane ordering.

Additional diagnostic runs in that folder test alternative following, lane-changing and time-step settings. They are separate sensitivity checks and are excluded from the method comparison dataset. Results must be assessed for remaining collisions, teleports and routing warnings before choosing a revised common vehicle model.
