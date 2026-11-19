# Complete comparisons between all signal-control methods

## Replacement Results subsection

All ten research controllers and the fixed-time reference were included in the pairwise analysis. Eleven methods produced 55 unique method pairs within each demand, vehicle-type and path group. Each comparison matched the same seed, tracked journey and simulation inputs. Mean differences were calculated from the common eligible seeds for the two methods.

At demand scales 0.1 and 0.5, all 55 pairs were available in every vehicle–path group, with four matched seeds per pair. At scale 1.0, 36 pairs were available in each group. Ten of these pairs retained four matched seeds. The remaining available pairs used smaller matched subsets. Nineteen pairs were unavailable because they involved CN-MP or WNCN-MP, which had no runs satisfying the all-four-arrived criterion.

At scale 0.1, Switching-Loss MP produced the lowest outer-car mean, while CN-MP produced the lowest means in the other three groups. WNCN-MP and W*NCN-MP also produced relatively short central-path journeys. C-MP, TD-MP, CV-MP and W*CN-MP improved on fixed-time across all groups, with different relative advantages by vehicle and path. Queue-responsive control and Coordinated Auction also reduced mean travel times relative to fixed-time at this demand level, although their improvements were generally smaller than those of the leading pressure-based methods.

At scale 0.5, C-MP had a lower paired mean travel time than every other method in all four groups. The relative position of CN-MP, WNCN-MP, W*NCN-MP, W*CN-MP, Switching-Loss MP, TD-MP and CV-MP depended on vehicle type and path. For example, CN-MP was faster than WNCN-MP for outer cars, while WNCN-MP was faster for central cars. Switching-Loss MP was faster than TD-MP for outer motorcycles, while TD-MP was faster for outer cars. Queue-responsive control produced a longer outer-car journey than fixed-time, with shorter means in the other groups. Coordinated Auction produced longer journeys than fixed-time in every group.

At scale 1.0, W*CN-MP had the lowest means in all four groups among the five methods retaining four eligible seeds. These five methods were fixed-time, CV-MP, queue-responsive control, W*NCN-MP and W*CN-MP. Switching-Loss MP retained three eligible seeds. On its common seeds with W*CN-MP, Switching-Loss MP was faster by an average of 4.92 seconds for central cars, 10.58 seconds for central motorcycles and 8.50 seconds for outer motorcycles. W*CN-MP was faster by 64.42 seconds for outer cars. These results demonstrate why high-demand pairwise differences must use matched seeds.

C-MP and TD-MP each retained one eligible seed at scale 1.0. C-MP recorded relatively short journeys in that seed, while TD-MP recorded longer outer-path journeys than its matched fixed-time observations. CV-MP and queue-responsive control improved central-path travel times relative to fixed-time and produced longer outer-path journeys. W*NCN-MP improved on fixed-time in all four groups. Coordinated Auction retained two eligible seeds and recorded substantially longer journeys. CN-MP and WNCN-MP retained their completion results in the analysis, with no eligible travel-time means under the selected policy.

These pairwise results are descriptive. Completion coverage, unequal matched sample sizes and recorded simulation events remain relevant to their interpretation. The source dataset audit records accepted = false.

## Complete comparison tables

Each cell reports the mean travel-time difference A minus B in seconds, followed by the matched seed count in parentheses. Negative values favour A. Positive values favour B. A dash with n = 0 denotes an unavailable comparison. The tables use the all-four-arrived inclusion policy and retain event-affected runs under that policy.

### Demand scale 0.1

| Method A | Method B | Outer car | Outer motorcycle | Central car | Central motorcycle |
|---|---|---:|---:|---:|---:|
| Fixed-time | Switching-Loss MP | 109.38 (n=4) | 102.19 (n=4) | 96.19 (n=4) | 105.25 (n=4) |
| Fixed-time | C-MP | 89.81 (n=4) | 87.38 (n=4) | 98.81 (n=4) | 98.94 (n=4) |
| Fixed-time | TD-MP | 87.56 (n=4) | 96.12 (n=4) | 99.25 (n=4) | 98.88 (n=4) |
| Fixed-time | CV-MP | 76.44 (n=4) | 75.94 (n=4) | 86.69 (n=4) | 86.50 (n=4) |
| Fixed-time | Queue-responsive | 41.56 (n=4) | 38.81 (n=4) | 56.19 (n=4) | 56.00 (n=4) |
| Fixed-time | CN-MP | 108.38 (n=4) | 103.94 (n=4) | 108.50 (n=4) | 107.38 (n=4) |
| Fixed-time | WNCN-MP | 101.19 (n=4) | 96.88 (n=4) | 105.44 (n=4) | 104.44 (n=4) |
| Fixed-time | W*NCN-MP | 98.44 (n=4) | 93.69 (n=4) | 104.06 (n=4) | 103.94 (n=4) |
| Fixed-time | W*CN-MP | 88.19 (n=4) | 97.19 (n=4) | 98.31 (n=4) | 98.25 (n=4) |
| Fixed-time | Coordinated Auction | 71.94 (n=4) | 37.38 (n=4) | 72.19 (n=4) | 72.69 (n=4) |
| Switching-Loss MP | C-MP | -19.56 (n=4) | -14.81 (n=4) | 2.62 (n=4) | -6.31 (n=4) |
| Switching-Loss MP | TD-MP | -21.81 (n=4) | -6.06 (n=4) | 3.06 (n=4) | -6.38 (n=4) |
| Switching-Loss MP | CV-MP | -32.94 (n=4) | -26.25 (n=4) | -9.50 (n=4) | -18.75 (n=4) |
| Switching-Loss MP | Queue-responsive | -67.81 (n=4) | -63.38 (n=4) | -40.00 (n=4) | -49.25 (n=4) |
| Switching-Loss MP | CN-MP | -1.00 (n=4) | 1.75 (n=4) | 12.31 (n=4) | 2.12 (n=4) |
| Switching-Loss MP | WNCN-MP | -8.19 (n=4) | -5.31 (n=4) | 9.25 (n=4) | -0.81 (n=4) |
| Switching-Loss MP | W*NCN-MP | -10.94 (n=4) | -8.50 (n=4) | 7.88 (n=4) | -1.31 (n=4) |
| Switching-Loss MP | W*CN-MP | -21.19 (n=4) | -5.00 (n=4) | 2.12 (n=4) | -7.00 (n=4) |
| Switching-Loss MP | Coordinated Auction | -37.44 (n=4) | -64.81 (n=4) | -24.00 (n=4) | -32.56 (n=4) |
| C-MP | TD-MP | -2.25 (n=4) | 8.75 (n=4) | 0.44 (n=4) | -0.06 (n=4) |
| C-MP | CV-MP | -13.38 (n=4) | -11.44 (n=4) | -12.12 (n=4) | -12.44 (n=4) |
| C-MP | Queue-responsive | -48.25 (n=4) | -48.56 (n=4) | -42.62 (n=4) | -42.94 (n=4) |
| C-MP | CN-MP | 18.56 (n=4) | 16.56 (n=4) | 9.69 (n=4) | 8.44 (n=4) |
| C-MP | WNCN-MP | 11.38 (n=4) | 9.50 (n=4) | 6.62 (n=4) | 5.50 (n=4) |
| C-MP | W*NCN-MP | 8.62 (n=4) | 6.31 (n=4) | 5.25 (n=4) | 5.00 (n=4) |
| C-MP | W*CN-MP | -1.62 (n=4) | 9.81 (n=4) | -0.50 (n=4) | -0.69 (n=4) |
| C-MP | Coordinated Auction | -17.88 (n=4) | -50.00 (n=4) | -26.62 (n=4) | -26.25 (n=4) |
| TD-MP | CV-MP | -11.12 (n=4) | -20.19 (n=4) | -12.56 (n=4) | -12.38 (n=4) |
| TD-MP | Queue-responsive | -46.00 (n=4) | -57.31 (n=4) | -43.06 (n=4) | -42.88 (n=4) |
| TD-MP | CN-MP | 20.81 (n=4) | 7.81 (n=4) | 9.25 (n=4) | 8.50 (n=4) |
| TD-MP | WNCN-MP | 13.62 (n=4) | 0.75 (n=4) | 6.19 (n=4) | 5.56 (n=4) |
| TD-MP | W*NCN-MP | 10.88 (n=4) | -2.44 (n=4) | 4.81 (n=4) | 5.06 (n=4) |
| TD-MP | W*CN-MP | 0.62 (n=4) | 1.06 (n=4) | -0.94 (n=4) | -0.62 (n=4) |
| TD-MP | Coordinated Auction | -15.62 (n=4) | -58.75 (n=4) | -27.06 (n=4) | -26.19 (n=4) |
| CV-MP | Queue-responsive | -34.88 (n=4) | -37.12 (n=4) | -30.50 (n=4) | -30.50 (n=4) |
| CV-MP | CN-MP | 31.94 (n=4) | 28.00 (n=4) | 21.81 (n=4) | 20.88 (n=4) |
| CV-MP | WNCN-MP | 24.75 (n=4) | 20.94 (n=4) | 18.75 (n=4) | 17.94 (n=4) |
| CV-MP | W*NCN-MP | 22.00 (n=4) | 17.75 (n=4) | 17.38 (n=4) | 17.44 (n=4) |
| CV-MP | W*CN-MP | 11.75 (n=4) | 21.25 (n=4) | 11.62 (n=4) | 11.75 (n=4) |
| CV-MP | Coordinated Auction | -4.50 (n=4) | -38.56 (n=4) | -14.50 (n=4) | -13.81 (n=4) |
| Queue-responsive | CN-MP | 66.81 (n=4) | 65.12 (n=4) | 52.31 (n=4) | 51.38 (n=4) |
| Queue-responsive | WNCN-MP | 59.62 (n=4) | 58.06 (n=4) | 49.25 (n=4) | 48.44 (n=4) |
| Queue-responsive | W*NCN-MP | 56.88 (n=4) | 54.88 (n=4) | 47.88 (n=4) | 47.94 (n=4) |
| Queue-responsive | W*CN-MP | 46.62 (n=4) | 58.38 (n=4) | 42.12 (n=4) | 42.25 (n=4) |
| Queue-responsive | Coordinated Auction | 30.38 (n=4) | -1.44 (n=4) | 16.00 (n=4) | 16.69 (n=4) |
| CN-MP | WNCN-MP | -7.19 (n=4) | -7.06 (n=4) | -3.06 (n=4) | -2.94 (n=4) |
| CN-MP | W*NCN-MP | -9.94 (n=4) | -10.25 (n=4) | -4.44 (n=4) | -3.44 (n=4) |
| CN-MP | W*CN-MP | -20.19 (n=4) | -6.75 (n=4) | -10.19 (n=4) | -9.12 (n=4) |
| CN-MP | Coordinated Auction | -36.44 (n=4) | -66.56 (n=4) | -36.31 (n=4) | -34.69 (n=4) |
| WNCN-MP | W*NCN-MP | -2.75 (n=4) | -3.19 (n=4) | -1.38 (n=4) | -0.50 (n=4) |
| WNCN-MP | W*CN-MP | -13.00 (n=4) | 0.31 (n=4) | -7.12 (n=4) | -6.19 (n=4) |
| WNCN-MP | Coordinated Auction | -29.25 (n=4) | -59.50 (n=4) | -33.25 (n=4) | -31.75 (n=4) |
| W*NCN-MP | W*CN-MP | -10.25 (n=4) | 3.50 (n=4) | -5.75 (n=4) | -5.69 (n=4) |
| W*NCN-MP | Coordinated Auction | -26.50 (n=4) | -56.31 (n=4) | -31.88 (n=4) | -31.25 (n=4) |
| W*CN-MP | Coordinated Auction | -16.25 (n=4) | -59.81 (n=4) | -26.12 (n=4) | -25.56 (n=4) |

### Demand scale 0.5

| Method A | Method B | Outer car | Outer motorcycle | Central car | Central motorcycle |
|---|---|---:|---:|---:|---:|
| Fixed-time | Switching-Loss MP | 25.00 (n=4) | 58.19 (n=4) | 86.38 (n=4) | 87.06 (n=4) |
| Fixed-time | C-MP | 54.50 (n=4) | 78.75 (n=4) | 100.69 (n=4) | 99.56 (n=4) |
| Fixed-time | TD-MP | 43.38 (n=4) | 51.56 (n=4) | 76.06 (n=4) | 86.81 (n=4) |
| Fixed-time | CV-MP | 19.50 (n=4) | 39.31 (n=4) | 86.62 (n=4) | 86.44 (n=4) |
| Fixed-time | Queue-responsive | -27.19 (n=4) | 3.06 (n=4) | 16.38 (n=4) | 17.69 (n=4) |
| Fixed-time | CN-MP | 44.38 (n=4) | 53.56 (n=4) | 84.75 (n=4) | 97.25 (n=4) |
| Fixed-time | WNCN-MP | 38.44 (n=4) | 44.62 (n=4) | 92.88 (n=4) | 94.06 (n=4) |
| Fixed-time | W*NCN-MP | 23.56 (n=4) | 56.81 (n=4) | 76.12 (n=4) | 73.94 (n=4) |
| Fixed-time | W*CN-MP | 38.81 (n=4) | 52.88 (n=4) | 74.50 (n=4) | 76.31 (n=4) |
| Fixed-time | Coordinated Auction | -134.44 (n=4) | -119.88 (n=4) | -56.88 (n=4) | -43.69 (n=4) |
| Switching-Loss MP | C-MP | 29.50 (n=4) | 20.56 (n=4) | 14.31 (n=4) | 12.50 (n=4) |
| Switching-Loss MP | TD-MP | 18.38 (n=4) | -6.62 (n=4) | -10.31 (n=4) | -0.25 (n=4) |
| Switching-Loss MP | CV-MP | -5.50 (n=4) | -18.88 (n=4) | 0.25 (n=4) | -0.62 (n=4) |
| Switching-Loss MP | Queue-responsive | -52.19 (n=4) | -55.12 (n=4) | -70.00 (n=4) | -69.38 (n=4) |
| Switching-Loss MP | CN-MP | 19.38 (n=4) | -4.62 (n=4) | -1.62 (n=4) | 10.19 (n=4) |
| Switching-Loss MP | WNCN-MP | 13.44 (n=4) | -13.56 (n=4) | 6.50 (n=4) | 7.00 (n=4) |
| Switching-Loss MP | W*NCN-MP | -1.44 (n=4) | -1.38 (n=4) | -10.25 (n=4) | -13.12 (n=4) |
| Switching-Loss MP | W*CN-MP | 13.81 (n=4) | -5.31 (n=4) | -11.88 (n=4) | -10.75 (n=4) |
| Switching-Loss MP | Coordinated Auction | -159.44 (n=4) | -178.06 (n=4) | -143.25 (n=4) | -130.75 (n=4) |
| C-MP | TD-MP | -11.12 (n=4) | -27.19 (n=4) | -24.62 (n=4) | -12.75 (n=4) |
| C-MP | CV-MP | -35.00 (n=4) | -39.44 (n=4) | -14.06 (n=4) | -13.12 (n=4) |
| C-MP | Queue-responsive | -81.69 (n=4) | -75.69 (n=4) | -84.31 (n=4) | -81.88 (n=4) |
| C-MP | CN-MP | -10.12 (n=4) | -25.19 (n=4) | -15.94 (n=4) | -2.31 (n=4) |
| C-MP | WNCN-MP | -16.06 (n=4) | -34.12 (n=4) | -7.81 (n=4) | -5.50 (n=4) |
| C-MP | W*NCN-MP | -30.94 (n=4) | -21.94 (n=4) | -24.56 (n=4) | -25.62 (n=4) |
| C-MP | W*CN-MP | -15.69 (n=4) | -25.88 (n=4) | -26.19 (n=4) | -23.25 (n=4) |
| C-MP | Coordinated Auction | -188.94 (n=4) | -198.62 (n=4) | -157.56 (n=4) | -143.25 (n=4) |
| TD-MP | CV-MP | -23.88 (n=4) | -12.25 (n=4) | 10.56 (n=4) | -0.38 (n=4) |
| TD-MP | Queue-responsive | -70.56 (n=4) | -48.50 (n=4) | -59.69 (n=4) | -69.12 (n=4) |
| TD-MP | CN-MP | 1.00 (n=4) | 2.00 (n=4) | 8.69 (n=4) | 10.44 (n=4) |
| TD-MP | WNCN-MP | -4.94 (n=4) | -6.94 (n=4) | 16.81 (n=4) | 7.25 (n=4) |
| TD-MP | W*NCN-MP | -19.81 (n=4) | 5.25 (n=4) | 0.06 (n=4) | -12.88 (n=4) |
| TD-MP | W*CN-MP | -4.56 (n=4) | 1.31 (n=4) | -1.56 (n=4) | -10.50 (n=4) |
| TD-MP | Coordinated Auction | -177.81 (n=4) | -171.44 (n=4) | -132.94 (n=4) | -130.50 (n=4) |
| CV-MP | Queue-responsive | -46.69 (n=4) | -36.25 (n=4) | -70.25 (n=4) | -68.75 (n=4) |
| CV-MP | CN-MP | 24.88 (n=4) | 14.25 (n=4) | -1.88 (n=4) | 10.81 (n=4) |
| CV-MP | WNCN-MP | 18.94 (n=4) | 5.31 (n=4) | 6.25 (n=4) | 7.62 (n=4) |
| CV-MP | W*NCN-MP | 4.06 (n=4) | 17.50 (n=4) | -10.50 (n=4) | -12.50 (n=4) |
| CV-MP | W*CN-MP | 19.31 (n=4) | 13.56 (n=4) | -12.12 (n=4) | -10.12 (n=4) |
| CV-MP | Coordinated Auction | -153.94 (n=4) | -159.19 (n=4) | -143.50 (n=4) | -130.12 (n=4) |
| Queue-responsive | CN-MP | 71.56 (n=4) | 50.50 (n=4) | 68.38 (n=4) | 79.56 (n=4) |
| Queue-responsive | WNCN-MP | 65.62 (n=4) | 41.56 (n=4) | 76.50 (n=4) | 76.38 (n=4) |
| Queue-responsive | W*NCN-MP | 50.75 (n=4) | 53.75 (n=4) | 59.75 (n=4) | 56.25 (n=4) |
| Queue-responsive | W*CN-MP | 66.00 (n=4) | 49.81 (n=4) | 58.12 (n=4) | 58.62 (n=4) |
| Queue-responsive | Coordinated Auction | -107.25 (n=4) | -122.94 (n=4) | -73.25 (n=4) | -61.38 (n=4) |
| CN-MP | WNCN-MP | -5.94 (n=4) | -8.94 (n=4) | 8.12 (n=4) | -3.19 (n=4) |
| CN-MP | W*NCN-MP | -20.81 (n=4) | 3.25 (n=4) | -8.62 (n=4) | -23.31 (n=4) |
| CN-MP | W*CN-MP | -5.56 (n=4) | -0.69 (n=4) | -10.25 (n=4) | -20.94 (n=4) |
| CN-MP | Coordinated Auction | -178.81 (n=4) | -173.44 (n=4) | -141.62 (n=4) | -140.94 (n=4) |
| WNCN-MP | W*NCN-MP | -14.88 (n=4) | 12.19 (n=4) | -16.75 (n=4) | -20.12 (n=4) |
| WNCN-MP | W*CN-MP | 0.38 (n=4) | 8.25 (n=4) | -18.38 (n=4) | -17.75 (n=4) |
| WNCN-MP | Coordinated Auction | -172.88 (n=4) | -164.50 (n=4) | -149.75 (n=4) | -137.75 (n=4) |
| W*NCN-MP | W*CN-MP | 15.25 (n=4) | -3.94 (n=4) | -1.62 (n=4) | 2.38 (n=4) |
| W*NCN-MP | Coordinated Auction | -158.00 (n=4) | -176.69 (n=4) | -133.00 (n=4) | -117.62 (n=4) |
| W*CN-MP | Coordinated Auction | -173.25 (n=4) | -172.75 (n=4) | -131.38 (n=4) | -120.00 (n=4) |

### Demand scale 1

| Method A | Method B | Outer car | Outer motorcycle | Central car | Central motorcycle |
|---|---|---:|---:|---:|---:|
| Fixed-time | Switching-Loss MP | 37.42 (n=3) | 76.92 (n=3) | 92.08 (n=3) | 100.58 (n=3) |
| Fixed-time | C-MP | 136.25 (n=1) | 140.50 (n=1) | 86.25 (n=1) | 86.50 (n=1) |
| Fixed-time | TD-MP | -56.25 (n=1) | -58.25 (n=1) | 6.75 (n=1) | 6.75 (n=1) |
| Fixed-time | CV-MP | -29.19 (n=4) | -34.50 (n=4) | 47.94 (n=4) | 72.19 (n=4) |
| Fixed-time | Queue-responsive | -65.19 (n=4) | -34.31 (n=4) | 49.25 (n=4) | 49.00 (n=4) |
| Fixed-time | CN-MP | — (n=0) | — (n=0) | — (n=0) | — (n=0) |
| Fixed-time | WNCN-MP | — (n=0) | — (n=0) | — (n=0) | — (n=0) |
| Fixed-time | W*NCN-MP | 65.25 (n=4) | 61.00 (n=4) | 73.06 (n=4) | 92.75 (n=4) |
| Fixed-time | W*CN-MP | 93.19 (n=4) | 67.06 (n=4) | 87.94 (n=4) | 93.12 (n=4) |
| Fixed-time | Coordinated Auction | -392.75 (n=2) | -388.38 (n=2) | -293.25 (n=2) | -284.88 (n=2) |
| Switching-Loss MP | C-MP | 44.00 (n=1) | -28.50 (n=1) | -11.00 (n=1) | -11.25 (n=1) |
| Switching-Loss MP | TD-MP | -148.50 (n=1) | -227.25 (n=1) | -90.50 (n=1) | -91.00 (n=1) |
| Switching-Loss MP | CV-MP | -62.00 (n=3) | -87.92 (n=3) | -47.83 (n=3) | -25.17 (n=3) |
| Switching-Loss MP | Queue-responsive | -102.92 (n=3) | -102.50 (n=3) | -44.92 (n=3) | -52.25 (n=3) |
| Switching-Loss MP | CN-MP | — (n=0) | — (n=0) | — (n=0) | — (n=0) |
| Switching-Loss MP | WNCN-MP | — (n=0) | — (n=0) | — (n=0) | — (n=0) |
| Switching-Loss MP | W*NCN-MP | 65.17 (n=3) | 32.92 (n=3) | -7.83 (n=3) | -14.42 (n=3) |
| Switching-Loss MP | W*CN-MP | 64.42 (n=3) | -8.50 (n=3) | -4.92 (n=3) | -10.58 (n=3) |
| Switching-Loss MP | Coordinated Auction | -433.00 (n=2) | -489.25 (n=2) | -384.38 (n=2) | -388.50 (n=2) |
| C-MP | TD-MP | -192.50 (n=1) | -198.75 (n=1) | -79.50 (n=1) | -79.75 (n=1) |
| C-MP | CV-MP | -103.00 (n=1) | -99.75 (n=1) | -38.75 (n=1) | -24.50 (n=1) |
| C-MP | Queue-responsive | -236.25 (n=1) | -131.00 (n=1) | -37.25 (n=1) | -37.50 (n=1) |
| C-MP | CN-MP | — (n=0) | — (n=0) | — (n=0) | — (n=0) |
| C-MP | WNCN-MP | — (n=0) | — (n=0) | — (n=0) | — (n=0) |
| C-MP | W*NCN-MP | 48.00 (n=1) | 42.00 (n=1) | 1.25 (n=1) | 1.25 (n=1) |
| C-MP | W*CN-MP | 19.75 (n=1) | -49.75 (n=1) | 3.00 (n=1) | 7.50 (n=1) |
| C-MP | Coordinated Auction | -498.75 (n=1) | -479.50 (n=1) | -446.50 (n=1) | -433.75 (n=1) |
| TD-MP | CV-MP | 89.50 (n=1) | 99.00 (n=1) | 40.75 (n=1) | 55.25 (n=1) |
| TD-MP | Queue-responsive | -43.75 (n=1) | 67.75 (n=1) | 42.25 (n=1) | 42.25 (n=1) |
| TD-MP | CN-MP | — (n=0) | — (n=0) | — (n=0) | — (n=0) |
| TD-MP | WNCN-MP | — (n=0) | — (n=0) | — (n=0) | — (n=0) |
| TD-MP | W*NCN-MP | 240.50 (n=1) | 240.75 (n=1) | 80.75 (n=1) | 81.00 (n=1) |
| TD-MP | W*CN-MP | 212.25 (n=1) | 149.00 (n=1) | 82.50 (n=1) | 87.25 (n=1) |
| TD-MP | Coordinated Auction | -306.25 (n=1) | -280.75 (n=1) | -367.00 (n=1) | -354.00 (n=1) |
| CV-MP | Queue-responsive | -36.00 (n=4) | 0.19 (n=4) | 1.31 (n=4) | -23.19 (n=4) |
| CV-MP | CN-MP | — (n=0) | — (n=0) | — (n=0) | — (n=0) |
| CV-MP | WNCN-MP | — (n=0) | — (n=0) | — (n=0) | — (n=0) |
| CV-MP | W*NCN-MP | 94.44 (n=4) | 95.50 (n=4) | 25.12 (n=4) | 20.56 (n=4) |
| CV-MP | W*CN-MP | 122.38 (n=4) | 101.56 (n=4) | 40.00 (n=4) | 20.94 (n=4) |
| CV-MP | Coordinated Auction | -398.38 (n=2) | -383.25 (n=2) | -334.75 (n=2) | -346.00 (n=2) |
| Queue-responsive | CN-MP | — (n=0) | — (n=0) | — (n=0) | — (n=0) |
| Queue-responsive | WNCN-MP | — (n=0) | — (n=0) | — (n=0) | — (n=0) |
| Queue-responsive | W*NCN-MP | 130.44 (n=4) | 95.31 (n=4) | 23.81 (n=4) | 43.75 (n=4) |
| Queue-responsive | W*CN-MP | 158.38 (n=4) | 101.38 (n=4) | 38.69 (n=4) | 44.12 (n=4) |
| Queue-responsive | Coordinated Auction | -368.00 (n=2) | -385.62 (n=2) | -339.38 (n=2) | -332.88 (n=2) |
| CN-MP | WNCN-MP | — (n=0) | — (n=0) | — (n=0) | — (n=0) |
| CN-MP | W*NCN-MP | — (n=0) | — (n=0) | — (n=0) | — (n=0) |
| CN-MP | W*CN-MP | — (n=0) | — (n=0) | — (n=0) | — (n=0) |
| CN-MP | Coordinated Auction | — (n=0) | — (n=0) | — (n=0) | — (n=0) |
| WNCN-MP | W*NCN-MP | — (n=0) | — (n=0) | — (n=0) | — (n=0) |
| WNCN-MP | W*CN-MP | — (n=0) | — (n=0) | — (n=0) | — (n=0) |
| WNCN-MP | Coordinated Auction | — (n=0) | — (n=0) | — (n=0) | — (n=0) |
| W*NCN-MP | W*CN-MP | 27.94 (n=4) | 6.06 (n=4) | 14.88 (n=4) | 0.38 (n=4) |
| W*NCN-MP | Coordinated Auction | -506.38 (n=2) | -512.12 (n=2) | -372.62 (n=2) | -366.50 (n=2) |
| W*CN-MP | Coordinated Auction | -505.00 (n=2) | -453.75 (n=2) | -373.25 (n=2) | -369.12 (n=2) |
