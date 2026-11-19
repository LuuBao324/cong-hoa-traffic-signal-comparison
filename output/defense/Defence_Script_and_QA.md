# Cong Hoa thesis defence guide

Prepared for an approximately eight-minute English research presentation. The main presentation follows the supplied whiteboard flow. Slides 10–16 are hidden backup slides for questions.

## Timing

| Slide | Topic | Target duration |
|---|---|---:|
| 1 | Traffic Signal Control on Cong Hoa Road | 15 s |
| 2 | Motivation and research gap | 45 s |
| 3 | Network preparation and field inputs | 65 s |
| 4 | Shared inputs and four tracked journeys | 45 s |
| 5 | Ten methods from seven papers | 55 s |
| 6 | C-MP had the lowest means at scale 0.5 | 55 s |
| 7 | Journey completion at scale 1.0 | 55 s |
| 8 | Demo of the saved experiment | 80 s |
| 9 | Limitations and future development | 65 s |
| **Total** | | **480 s / 8 minutes** |

Use the speaker notes in PowerPoint Presenter View. Rehearse against these target times. The script is intended as speaking material and can be shortened to match your pace.

## English speaking script

### Slide 1 — Traffic Signal Control on Cong Hoa Road

Good morning. My name is Luu Nguyen Tan Bao. My project compares traffic signal controllers on Cong Hoa Road using a shared SUMO simulation. I will explain the data and model, the experimental comparison, and the main findings.

### Slide 2 — Motivation and research gap

Cong Hoa connects airport-related traffic with surrounding urban streets. A vehicle can pass several signalised junctions during one journey. A useful controller therefore needs to support progression along the corridor. Previous studies evaluate different networks and traffic conditions, which limits comparison between their reported improvements. My research question is which implemented controller gives shorter and more complete journeys under the same local simulation conditions. I compare both cars and motorcycles on the two corridor paths.

### Slide 3 — Network preparation and field inputs

I imported OpenStreetMap data into SUMO and revised junctions, lane connections and turning permissions in NetEdit. The prepared network contains 74 signal controllers. Field timing observations informed eight controllers. The remaining programmes use configured assumptions. The map shows the two tracked paths and their shared sections. Near Cong Hoa Garden, the reported video count was approximately three thousand vehicles in ten minutes in one direction. This gives an hourly extrapolation of eighteen thousand vehicles. Opposing demand and traffic elsewhere in the map were estimated separately. I retain this distinction between field observations and simulation inputs.

### Slide 4 — Shared inputs and four tracked journeys

The experiment combines eleven methods, three demand levels and four random seeds, giving one hundred and thirty-two runs. Each run tracks a car and a motorcycle on both the outer and central paths. This produces five hundred and twenty-eight journey records. Within each demand and seed, every method receives the same network, routes and scheduled departures. Travel time starts when the vehicle enters the simulation. Each run ends when all four tracked vehicles arrive or at sixteen hundred simulation seconds. I analyse the four vehicle and path groups separately.

### Slide 5 — Ten methods from seven papers

The comparison contains ten research methods from seven papers, plus fixed-time. Switching-Loss Max-Pressure considers phase-change losses. Total-Delay-Based Max-Pressure uses cumulative vehicle delay. Coordinated Max-Pressure uses counts and speeds to support progression. Connected-Vehicle Max-Pressure uses vehicle travel information. Four related formulations examine lane and capacity weighting. Queue-responsive control adjusts green durations, while Coordinated Auction exchanges priority information. I adapted these published decision rules to the phases available in SUMO. The implementations and their parameters are documented in the project. All methods use the same prepared traffic inputs.

### Slide 6 — C-MP had the lowest means at scale 0.5

At demand scale zero point five, every method completed all four tracked journeys in every seed. The chart shows outer-path cars for all eleven methods. C-MP recorded two hundred and sixty point five six seconds, compared with three hundred and fifteen point zero six seconds under fixed-time. This saves approximately fifty-four point five seconds. The mean paired improvement was seventeen point two nine percent. C-MP also had the lowest mean in the other three journey groups, with improvements reaching thirty-one point nine six percent. The full tables retain every method, vehicle type and path. These are descriptive results across four seeds.

### Slide 7 — Journey completion at scale 1.0

At scale one, completion becomes important. The table shows how many of the four runs completed all tracked journeys. W-star-CN-MP completed all four runs and recorded an outer-car mean of two hundred and fifty-three point three eight seconds. Its paired improvement over fixed-time was twenty-six point one two percent. Switching-Loss MP completed three runs, while C-MP and TD-MP completed one each. CN-MP and WNCN-MP had unfinished outer-path vehicles in every run. Their central vehicles arrived, but those runs did not meet the four-vehicle inclusion rule. Overall, one hundred and forty-two of one hundred and seventy-six high-demand journeys finished.

### Slide 8 — Demo of the saved experiment

I will now show how the saved results can be inspected. I select the current dataset, passenger cars and the outer path, then demand scale zero point five. All eleven methods remain selected. The journey table reports the mean, standard deviation and seed count. The pairwise comparison tab shows every method against every other method. I inspect C-MP against fixed-time on the four matching seeds. I then change to motorcycles and the central path to show why the groups are analysed separately. Finally, I open the notebook, where the figures and comparisons are calculated from the saved CSV. The dashboard displays the recorded results and their outstanding validation warning.

### Slide 9 — Limitations and future development

The main contribution is a reproducible dataset and a matched comparison of controller behaviour on Cong Hoa. The study has important limits. It uses four seeds per demand level and four tracked journeys per run. Traffic observations cover one location and a short period. The simulation recorded six hundred and seventy-four collisions and the same number of teleports. Thirty-four tracked journeys were unfinished, and the source audit remains unaccepted. The results therefore support exploratory comparisons within this model. Future work should first diagnose junction blockage and calibrate demand and vehicle behaviour, then repeat the comparison with more seeds and departure times. Thank you. I welcome your questions.

## Demo walkthrough — 80 seconds

Before the presentation, open the dashboard and notebook. Keep the browser ready on the local address and select the 132-run checkpoint.

| Time | Action | Evidence to point out |
|---|---|---|
| 0–15 s | Select Car, Outer path and demand scale 0.5 | All eleven methods remain selected |
| 15–35 s | Open Journey time | C-MP mean 260.56 s, fixed-time 315.06 s, four eligible seeds |
| 35–50 s | Open Pairwise comparison and choose scale 0.5 | Inspect C-MP against fixed-time, mean difference −54.50 s |
| 50–65 s | Change to Motorcycle and Center path | C-MP mean 212.81 s, fixed-time 312.38 s |
| 65–80 s | Open the executed notebook | Matched-seed checks and all-method comparisons |

If the browser fails, continue with the screenshot and native result tables in the deck. Existing executed notebook outputs provide the calculation evidence.

### Start the local dashboard

Run from the project root in PowerShell.

```powershell
.\.venv-dashboard\Scripts\python.exe -m streamlit run app\streamlit_app.py --server.address 127.0.0.1 --server.port 8501
```

Open http://127.0.0.1:8501 and stop the owned server with Ctrl+C. Select the Completion, Journey time, Pairwise comparison or Data and provenance tab. The inclusion policy is available in the sidebar expander.

### Notebook

Open `analysis/cong_hoa_analysis.ipynb` in VS Code. Select the project `.venv` kernel. The notebook already contains saved outputs.

### SUMO network view for a question

Use the frozen input network if the examiner asks to inspect geometry. The command opens the saved network for visual inspection.

```powershell
.\.venv\Scripts\sumo-gui.exe --net-file .\tan_binh_2026\dataset_cong_hoa\inputs\d0.5_s100\network_snapshot.net.xml.gz
```

Python controls adaptive methods through the simulator interface during experiments. Opening a saved `.sumocfg` alone shows its stored traffic-light programme. A live rerun requires the controller runner and a separate output destination.

## Questions and suggested answers

### 1. What is the contribution of your project?

The contribution is a shared-input comparison dataset and a reproducible analysis of implemented signal controllers on Cong Hoa. It includes demand variation, separate vehicle and path groups, and matched-seed comparisons. The controller decision rules come from published studies.

### 2. Why did you choose Cong Hoa?

Cong Hoa carries airport-related and surrounding urban traffic through several interacting junctions. Published local research describes congestion in this area. Its connecting streets and parallel paths make corridor journey progression a relevant question. I also had access to local signal and traffic observations.

### 3. Why are there ten methods but seven papers?

Four related pressure formulations come from the same ECC 2024 paper. I evaluate them separately because their pressure calculations differ. The other six research methods come from six papers. Fixed-time is an additional reference.

### 4. Does this reproduce each original paper exactly?

I applied the published decision mechanisms through documented SUMO adaptations. The network, vehicle behaviour, available phases and observation settings belong to this experiment. The implementation notes record assumptions and adaptations. This scope limits comparisons with original experimental percentages.

### 5. Why did you use SUMO?

SUMO supports microscopic vehicle simulation, external Python control and vehicle-level output. It allowed the methods to share one network and traffic inputs. NetEdit also supported inspection of lane connections and signal programmes.

### 6. Where did the 74 traffic-light controllers come from?

This count was extracted from the prepared SUMO network after import and manual revisions. Eight controllers were informed by field timing observations. Remaining timings use configured programmes. The network inventory describes the model, and further field verification is needed.

### 7. Where did the traffic volume come from?

The reported observation was approximately 3,000 vehicles in ten minutes in one direction near Cong Hoa Garden. Multiplying by six gives an hourly extrapolation of 18,000 vehicles for that direction. Equal opposing flow and additional background demand were scenario assumptions. The year and time band are unconfirmed in the saved metadata, and the raw count sheet is not archived.

### 8. Is 67,500 vehicles per hour the measured flow on Cong Hoa?

It is the nominal whole-map requested input at scale 1.0. It combines 36,000 journeys per hour using a Cong Hoa segment and 31,500 other journeys. Actual passage at a cross-section depends on routes, insertion and congestion. Field passenger-car-unit figures also require vehicle-equivalence conversion before comparison with raw vehicle counts.

### 9. What does a random seed do?

A seed sets the random traffic realisation. All methods use the same prepared routes and departures within that scenario. The four seeds provide repeated traffic samples. Four tracked vehicles within one run share that sample, so each vehicle and path group has at most four seed observations.

### 10. How is travel time measured?

It is arrival time minus actual departure time. Waiting before the simulator inserts the vehicle is departure delay and is recorded separately. Waiting during the journey contributes to travel time. The tracked route and vehicle type remain fixed within each matched comparison.

### 11. Why are cars and motorcycles analysed separately?

The vehicle classes have different configured dimensions and interactions. Results can also vary between the central and outer paths. Keeping these groups separate prevents an overall mean from hiding a benefit in one group and a deterioration in another.

### 12. Did you use the sublane model in this dataset?

The selected 132-run dataset uses Krauss following and LC2013 lane changing with single-file movement within each lane. Earlier sublane experiments remain in separate folders. The present findings are bounded by the lane-based movement assumption.

### 13. Why do CN-MP and WNCN-MP have missing means at scale 1.0?

Their outer-path tracked vehicles remained unfinished at the time limit in every seed. Central-path vehicles arrived, but the main inclusion rule requires all four tracked vehicles in a run to arrive. The raw data preserve these records as censored observations. Completion counts are reported alongside means.

### 14. Why could fixed-time finish when some adaptive controllers could not?

The recorded outcomes show different vehicle progression under the control decisions. Fixed-time gives movements scheduled service, while the research controllers use their state-dependent rules. Prolonged outer-path waiting is confirmed. Establishing the exact cause at each junction requires signal and vehicle histories. Fixed-time also stopped after tracked arrivals, so that result alone cannot establish long-duration network stability.

### 15. Do the collisions and teleports invalidate the conclusions?

They restrict the strength of the conclusions. I report 674 collisions and 674 teleports, with one directly affected tracked vehicle. The main arrival-based policy retains event-affected runs. Sensitivity analysis shows how event exclusions reduce coverage. The source acceptance audit remains false, and the findings are exploratory.

### 16. Why keep an all-four-arrived policy?

This was the selected run-level criterion for the current comparison. It gives a common completion condition for the four tracked journeys within a run. It also excludes completed central journeys when outer journeys are unfinished. The raw records and completion tables preserve that information, and the limitation is stated.

### 17. Do you compare only with fixed-time?

The analysis includes all 55 unique method pairs within each demand, vehicle and path group. Pairing requires common eligible seeds and matching inputs. At scales 0.1 and 0.5, every pair has four seeds. At scale 1.0, 36 pairs per group are available, including ten pairs with four seeds.

### 18. Why can I not subtract any two high-demand means?

The methods can have different eligible seed subsets. A fair difference uses their common seeds. For example, Switching-Loss MP and W-star-CN-MP share three eligible seeds at scale 1.0. The pairwise table calculates each difference on those seeds before averaging.

### 19. Which controller is best?

C-MP has the lowest observed means in all four groups at scale 0.5. At scale 1.0, W-star-CN-MP completes all four runs and has the lowest means among methods with four eligible seeds. Other comparisons depend on path, vehicle and completion coverage. The evidence supports these scenario-specific findings.

### 20. Have you demonstrated statistical significance?

The analysis reports descriptive means, sample standard deviations, matched differences and sample counts. Four seeds provide limited statistical precision. I have not claimed significance from these descriptive comparisons. More independent seeds and a prespecified statistical analysis would support stronger inference.

### 21. Can the percentages be compared directly with the original papers?

Networks, demand, reference timings and measured populations differ. Some papers report network delay, while this project reports selected corridor travel times. I discuss the direction and context of findings and identify the metric differences when showing published percentages.

### 22. What would you improve first?

I would inspect the junctions associated with prolonged waiting, verify connections and downstream discharge, and calibrate demand and vehicle behaviour using additional observations. I would then repeat the comparison with more seeds and tracked departure times, alongside completion and event-sensitive analysis.

## Algorithm questions for the defence

### A short overview to learn first

“I compare ten research methods from seven papers, together with fixed-time control. The methods differ in the information used to assign priority. Switching-Loss MP considers the cost of changing phase. C-MP adds speed information for coordination. TD-MP uses accumulated delay, while CV-MP uses normalised time spent on road segments. Four related methods examine lane and storage normalisation. Queue-responsive control adjusts green durations, and coordinated auction allocates priority using vehicle bids.”

An upstream link brings vehicles towards a junction. A downstream link receives vehicles after they cross. A movement is a particular upstream-to-downstream connection. A phase serves a compatible set of movements. Pressure expresses upstream demand relative to downstream conditions. The precise weight and phase aggregation differ between the implemented methods.

### 1. Switching-Loss Max-Pressure

**Source.** Sun et al. (2025).

**Suggested answer.** “This method considers the service lost when signals change. It evaluates stopped-vehicle pressure, protects the current phase against small gains from switching, and estimates a suitable green extension from discharge needs and receiving space.”

**Implementation detail.** The phase score uses the maximum movement contribution. Current-phase protection applies the factor 1 + k, with k = 0.2. Extension estimates use a saturation assumption of 0.5 vehicles per second per lane, a two-second startup allowance and six-metre storage spacing. Extensions are bounded between one and sixty seconds.

**Likely follow-up.** “A larger protection factor can retain the current phase more often. Its effect depends on the pressure values and competing demand. The selected k is a scenario parameter, and I have not established an optimal value for Cong Hoa.”

### 2. Coordinated Max-Pressure, C-MP

**Source.** Ahmed, Liu and Gayah (2025).

**Suggested answer.** “C-MP uses vehicle counts together with average movement speeds. Speed relative to free-flow speed changes the upstream and downstream weights. This allows moving groups of vehicles to influence priority and supports progression between successive junctions.”

**Implementation detail.** Downstream speed weighting is calculated separately for each downstream movement before aggregation with turning proportions. Alpha and beta are both one. Decisions use ten-second slots.

**Likely follow-up.** “Coordination emerges through the speed-sensitive priorities. The implementation does not prescribe a fixed green-wave offset between the junctions.”

### 3. Total-Delay-Based Max-Pressure, TD-MP

**Source.** Liu and Gayah (2023).

**Suggested answer.** “TD-MP uses accumulated delay to assign movement priority. Vehicles that have experienced substantial delay can influence the decision even when their approach contains relatively few vehicles. The score also accounts for recent downstream queuing.”

**Implementation detail.** Upstream delay is estimated from elapsed segment time minus the free-flow time corresponding to distance travelled. The downstream term uses the recent queue history and turning proportions. Decisions use five-second slots, including transition time when a change occurs.

**Likely follow-up.** “TD-MP and Switching-Loss MP have different objectives and calculations. TD-MP emphasises delay accumulated by vehicles. Switching-Loss MP explicitly protects the current phase and estimates extensions.”

### 4. Connected-Vehicle Max-Pressure, CV-MP

**Source.** Tan et al., journal publication catalogued as 2026. Formula verification in this project used the retained 2025 preprint, reflected in the internal identifier `cv_mp_2025`.

**Suggested answer.** “CV-MP uses the time vehicles have spent on their current road segment, normalised by that segment's free-flow travel time. These values contribute to upstream and downstream movement priorities. It allows travel information to affect the signal decision.”

**Implementation detail.** Free-flow time is segment length divided by the network speed limit. The controller assumes full simulated vehicle observation and uses ten-second decision slots. Its phase-switch discount differs from the factor retained for TD-MP.

**Likely follow-up.** “The connected-vehicle assumption concerns access to vehicle information. It does not require passenger occupancy. Full observation is an experimental assumption, and reduced data coverage would need separate testing.”

### 5–8. Four pressure formulations from Zoabi and Haddad

**Source.** Zoabi and Haddad (2024).

**Suggested answer.** “These four methods examine how lane count and road storage affect pressure. They share a source paper and are treated as related formulations. Their inclusion lets the experiment examine the effect of these different weight definitions within the same corridor.”

For this explanation, let n be the number of active lanes serving a movement, s its assumed saturation rate, w its upstream-minus-downstream vehicle-count weight, and w-star the corresponding capacity-adjusted weight. The movement contributions implemented in the project are shown below. A phase combines its served movement contributions.

| Method | Implemented movement contribution | Explanation to give |
|---|---|---|
| CN-MP | w × s / n | Normalises the service contribution by lane count. |
| WNCN-MP | w × s / n² | Applies an additional lane normalisation to the weight. |
| W*CN-MP | w-star × s / n | Uses capacity-adjusted weights with service normalisation. |
| W*NCN-MP | w-star × s / n² | Combines capacity-adjusted weights and both lane normalisations. |

In this implementation, s = 0.5 × n. Storage capacity is estimated using lane length and six-metre spacing. The capacity-adjusted upstream term divides its movement count by estimated capacity per lane. The downstream term applies the same principle to downstream movements with turning proportions. All four use ten-second decision slots.

**Likely follow-up.** “The star identifies the capacity-adjusted weight. The extra N identifies the additional normalisation in the registered formulation. These are four related methods from one paper. The names WNCN-MP and W*NCN-MP refer to different formulas.”

### 9. Queue-responsive allocation

**Source.** Albdairi and Almusawi (2026).

**Suggested answer.** “This controller adjusts green durations using queue size, accumulated waiting and speed. It distributes a green budget in proportion to a combined demand score. Bounds and smoothing limit abrupt changes. The phases retain their cyclic order.”

**Implementation detail.** The score combines queue per lane with weight 0.35, accumulated waiting with weight 0.35, and inverse speed with weight 0.30. Plans are reviewed every 120 seconds. Targets are independently bounded to 15–60 seconds, smoothed over five targets, and changed by at most five seconds per review. Initial greens are twenty seconds. The score-to-budget conversion is an explicit project assumption. Independent bounds can change the total allocated budget.

**Likely follow-up.** “The main adjustment is how long each phase receives green. Pressure-based controllers generally select a phase by comparing movement priorities at decision opportunities.”

### 10. Coordinated auction

**Source.** Muzzini and Montangero (2024).

**Suggested answer.** “Vehicles receive virtual budgets and submit bids for service. Bids also propagate towards downstream signals, allowing expected arrivals to influence priority. The winning lane is served through an available compatible signal phase.”

**Implementation detail.** Initial budgets are deterministically assigned between one and one hundred. A vehicle divides its remaining budget across remaining signals. Bids propagate up to five downstream signals, decreasing by a factor of one half per hop. The arrival threshold is ten seconds, and a 120-second starvation rule provides additional priority. Decisions use ten-second slots. The scenario assumes full vehicle communication.

**Likely follow-up.** “The budget is a virtual priority mechanism. It involves no financial transaction. The paper contains an inconsistency between the starvation inequality in its pseudocode and explanatory text. This implementation follows the text, and that choice is documented.”

### Common implementation questions

**Do these controllers know which vehicles are being measured?**

“The tracked IDs are used for measurement and the stopping condition. The controller rules use the available traffic observations across their movements. The experiment does not assign special signal priority to the four tracked vehicles.”

**How are cars and motorcycles counted?**

“Count-based terms count each simulated vehicle as one vehicle. Vehicle dimensions and following behaviour affect traffic movement, but the controller does not apply a passenger-car-equivalent conversion. Some methods instead use delay, travel time or bids as their weights.”

**What happens during a phase change?**

“The adaptive adapter uses three seconds of yellow and zero additional all-red. Movements that remain green in both phases retain green. Fixed-time uses its saved signal programme. These transition settings must be considered when interpreting the comparison.”

**Are all parameters taken directly from the papers?**

“The implementation follows the registered decision mechanisms with documented network adaptations. Some settings, including storage, saturation and observation coverage, are scenario assumptions. Parameter sensitivity and field calibration would strengthen the evaluation.”

**Why can a controller still perform poorly?**

“Its decisions depend on the observed state, available phases, downstream conditions and configured parameters. A local priority rule can produce unfavourable corridor journeys. For an unfinished journey, the saved completion and waiting records establish the outcome. Explaining its exact junction-level cause requires signal histories and trajectories.”

### How to prepare

Learn the short overview, one suggested answer per method, and the four-formulation table first. Use implementation details when asked for the equation, parameter or code behaviour. The eight-minute presentation summarises the methods, while this section supports the question period.

These explanations were checked against `pure_controllers.py`, `research_controllers.py`, `pressure_controllers.py` and `docs/PURE_NONRL_AUDIT.md`. They describe the project implementation. Exact reproduction of each source experiment and numerical equivalence of the 2025 CV-MP preprint with its later journal version have not been established by this preparation check.

## Facts to keep consistent during the defence

- Selected checkpoint contains 132 runs and 528 tracked-vehicle records.
- 494 journeys arrived and 34 were censored. The main all-four-arrived analysis includes 115 runs and 460 observations.
- There are ten research methods from seven papers, plus fixed-time.
- Three scales are 0.1, 0.5 and 1.0. Four seeds are 100–103.
- Four probes in one run share a seed. Per-group samples contain up to four independent seed observations.
- Network controller counts, field counts and assumed demand totals have different provenance.
- The current movement model is lane-based LC2013. The older 3,412-record sublane dataset is separate.
- Simulation events remain a limitation. Source audit accepted = false.
- Parameter choices and observation settings should be described as implemented assumptions where applicable.

## Slide backup index

10. Demand and vehicle assumptions
11. All methods at scale 0.1
12. All methods at scale 0.5
13. All methods at scale 1.0
14. Method sources
15. Incomplete journeys at scale 1.0
16. Matched-seed comparison example

## Preparation choices

The supplied flow was interpreted as an eight-minute research presentation, with a brief opening, approximately one minute on motivation and gap, approximately six minutes on methodology, results and demo, and approximately one minute on limitations and future development. The title is a descriptive working title derived from the project subject. The whiteboard also contains an app/web/game branch, and the deck follows its research branch.

## Evidence files

- `tan_binh_2026/dataset_cong_hoa/checkpoints/132_runs/dataset.csv`
- `tan_binh_2026/dataset_cong_hoa/checkpoints/132_runs/plan.json`
- `tan_binh_2026/dataset_cong_hoa/checkpoints/132_runs/snapshot.json`
- `tan_binh_2026/dataset_cong_hoa/checkpoints/132_runs/field_observation.json`
- `analysis/cong_hoa_analysis.ipynb`
- `analysis/outputs/cong_hoa_132_runs/journey_summary.csv`
- `analysis/outputs/cong_hoa_132_runs/method_pair_summary.csv`
- `traffic_study/paper_methods.py`
- `docs/PURE_NONRL_AUDIT.md`
