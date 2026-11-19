# Results revision and complete comparison tables

## Review of the submitted PDF

- PDF page 29 has a missing initial letter in the opening Results paragraph. Use “The experiment evaluated …”. The chapter heading should read “Results”.
- PDF page 30 refers to Figure 4 for completion coverage. The displayed caption on page 31 identifies that figure as Figure 5. Update all cross-references after final pagination.
- Figure 6 on PDF page 36 is difficult to read at its inserted size. It represents only outer-path cars at demand scale 0.5.
- Figure 7 on PDF page 38 contains four dense panels. Method labels, sample counts and tick labels become too small at page width. Use the exported single-panel figures.
- Tables 10, 11 and 13 already include all ten research methods and fixed-time. Table 12 contains three selected pairs, while Table 14 contains six selected methods. Expand the waiting-time evidence and provide the full pairwise results.
- Table 13 begins with two method rows at the bottom of PDF page 36 and continues on page 37. Keep the table together on a dedicated page, with a concise caption and sample-size note.
- The earlier rule highlighting methods with at least three eligible seeds introduces an arbitrary threshold. Report every method with its eligible n and discuss completion coverage explicitly.
- High-demand means use different eligible seed subsets. A direct pairwise claim must use the intersection of eligible seeds. Inspect the pairwise sample count before interpreting the mean difference.
- Keep WNCN-MP, W*NCN-MP and W*CN-MP visually distinct. Check the starred names in body paragraphs as well as tables.
- State whether figure error bars represent standard deviations or confidence intervals. Current exports show sample standard deviations.
- The recorded event totals and source acceptance status constrain the strength of the conclusions. Arrival-based inclusion can retain event-affected runs.

## Suggested Results structure

1. Experimental coverage and completion for every method at all three demand levels.
2. Travel time for every method, separated by vehicle and path, at each demand level.
3. Mean paired improvements relative to fixed-time for every method.
4. Pairwise comparisons across all methods, with complete matrices in an appendix.
5. Waiting time for every method at all three demand levels.
6. Variability across seeds and completion-conditioned comparisons.
7. Simulation-event sensitivity and a concise summary of observed findings.

## Replacement text for the waiting-time subsection

Waiting time was compared across all ten research controllers and the fixed-time reference. Results were separated by vehicle type, path and demand scale. At scales 0.1 and 0.5, every group contained four eligible seeds. At scale 1.0, the eligible seed count varied between methods under the all-four-arrived policy. A missing value indicates that no run met this policy.

### Mean waiting time at demand scale 0.1

| Method | Eligible seeds | Outer car (s) | Outer motorcycle (s) | Central car (s) | Central motorcycle (s) |
|---|---:|---:|---:|---:|---:|
| Fixed-time | 4 | 97.94 | 108.69 | 87.94 | 108.69 |
| Switching-Loss MP | 4 | 2.56 | 7.69 | 10.12 | 6.12 |
| C-MP | 4 | 8.44 | 13.75 | 2.31 | 12.06 |
| TD-MP | 4 | 11.06 | 8.12 | 3.94 | 8.31 |
| CV-MP | 4 | 16.25 | 12.75 | 9.12 | 17.00 |
| Queue-responsive | 4 | 52.44 | 58.69 | 30.00 | 48.62 |
| CN-MP | 4 | 4.44 | 2.38 | 1.81 | 2.31 |
| WNCN-MP | 4 | 7.31 | 7.69 | 2.94 | 5.62 |
| W*NCN-MP | 4 | 12.00 | 5.38 | 0.44 | 4.75 |
| W*CN-MP | 4 | 15.81 | 9.00 | 1.75 | 12.06 |
| Coordinated Auction | 4 | 30.56 | 57.00 | 26.81 | 34.00 |

### Mean waiting time at demand scale 0.5

| Method | Eligible seeds | Outer car (s) | Outer motorcycle (s) | Central car (s) | Central motorcycle (s) |
|---|---:|---:|---:|---:|---:|
| Fixed-time | 4 | 101.00 | 103.19 | 86.81 | 108.88 |
| Switching-Loss MP | 4 | 39.25 | 19.94 | 4.19 | 18.06 |
| C-MP | 4 | 16.25 | 14.25 | 2.81 | 10.12 |
| TD-MP | 4 | 23.94 | 27.81 | 18.38 | 18.06 |
| CV-MP | 4 | 44.69 | 34.56 | 7.81 | 20.62 |
| Queue-responsive | 4 | 87.19 | 61.06 | 56.25 | 77.88 |
| CN-MP | 4 | 23.94 | 20.44 | 15.38 | 9.12 |
| WNCN-MP | 4 | 16.44 | 27.06 | 7.19 | 16.94 |
| W*NCN-MP | 4 | 30.81 | 16.31 | 12.88 | 20.38 |
| W*CN-MP | 4 | 30.81 | 27.00 | 10.62 | 17.62 |
| Coordinated Auction | 4 | 140.94 | 131.81 | 108.75 | 113.62 |

### Mean waiting time at demand scale 1

| Method | Eligible seeds | Outer car (s) | Outer motorcycle (s) | Central car (s) | Central motorcycle (s) |
|---|---:|---:|---:|---:|---:|
| Fixed-time | 4 | 114.56 | 117.94 | 90.00 | 106.12 |
| Switching-Loss MP | 3 | 44.42 | 20.25 | 5.08 | 9.50 |
| C-MP | 1 | 9.50 | 29.75 | 4.25 | 21.50 |
| TD-MP | 1 | 195.25 | 197.25 | 76.25 | 80.25 |
| CV-MP | 4 | 62.69 | 89.56 | 44.75 | 21.69 |
| Queue-responsive | 4 | 133.31 | 95.69 | 36.88 | 49.25 |
| CN-MP | 0 | — | — | — | — |
| WNCN-MP | 0 | — | — | — | — |
| W*NCN-MP | 4 | 36.62 | 35.19 | 24.56 | 18.75 |
| W*CN-MP | 4 | 5.50 | 18.75 | 8.62 | 6.81 |
| Coordinated Auction | 2 | 289.25 | 274.75 | 270.75 | 280.00 |

At scale 0.1, stationary waiting under the pressure-based controllers was generally lower than under fixed-time. CN-MP recorded mean waiting times between 1.81 and 4.44 seconds across the four groups. W*NCN-MP produced the lowest central-car waiting mean at 0.44 seconds, while W*CN-MP recorded 1.75 seconds for that group. These waiting-time differences should be considered alongside complete journey times.

At scale 0.5, C-MP recorded mean waiting times of 16.25 and 14.25 seconds for outer-path cars and motorcycles. Its corresponding central-path values were 2.81 and 10.12 seconds. Switching-Loss MP, TD-MP, CV-MP and all four modified-pressure variants also recorded lower mean waiting times than fixed-time in every group. Queue-responsive control reduced waiting in each group, although its outer-car travel time exceeded the baseline. Coordinated Auction recorded longer waiting times than fixed-time in all four groups.

At scale 1.0, W*CN-MP retained four eligible seeds and recorded mean waiting times between 5.50 and 18.75 seconds. W*NCN-MP also retained four seeds, with means between 18.75 and 36.62 seconds. CV-MP recorded lower waiting means than fixed-time in all four groups, despite longer outer-path travel times. Queue-responsive control had greater outer-car waiting than fixed-time and lower waiting in the other three groups. Switching-Loss MP had three eligible seeds, C-MP and TD-MP had one, and Coordinated Auction had two. CN-MP and WNCN-MP had no eligible runs under the completion policy.

## Complete fixed-time comparisons

Each percentage is calculated for a matched seed and then averaged. Positive values indicate a shorter journey under the research method. Negative values indicate a longer journey. The fixed-time row is a self-comparison.

### Mean paired travel-time improvement at demand scale 0.1

| Method | Matched seeds | Outer car (%) | Outer motorcycle (%) | Central car (%) | Central motorcycle (%) |
|---|---:|---:|---:|---:|---:|
| Fixed-time | 4 | 0.00 | 0.00 | 0.00 | 0.00 |
| Switching-Loss MP | 4 | 34.69 | 32.64 | 30.53 | 33.71 |
| C-MP | 4 | 28.48 | 27.91 | 31.36 | 31.69 |
| TD-MP | 4 | 27.77 | 30.70 | 31.50 | 31.67 |
| CV-MP | 4 | 24.24 | 24.26 | 27.51 | 27.70 |
| Queue-responsive | 4 | 13.18 | 12.41 | 17.83 | 17.93 |
| CN-MP | 4 | 34.37 | 33.20 | 34.44 | 34.39 |
| WNCN-MP | 4 | 32.09 | 30.94 | 33.47 | 33.45 |
| W*NCN-MP | 4 | 31.22 | 29.93 | 33.03 | 33.29 |
| W*CN-MP | 4 | 27.96 | 31.05 | 31.20 | 31.47 |
| Coordinated Auction | 4 | 22.82 | 11.92 | 22.92 | 23.28 |

### Mean paired travel-time improvement at demand scale 0.5

| Method | Matched seeds | Outer car (%) | Outer motorcycle (%) | Central car (%) | Central motorcycle (%) |
|---|---:|---:|---:|---:|---:|
| Fixed-time | 4 | 0.00 | 0.00 | 0.00 | 0.00 |
| Switching-Loss MP | 4 | 7.93 | 18.51 | 27.41 | 27.87 |
| C-MP | 4 | 17.29 | 25.05 | 31.96 | 31.87 |
| TD-MP | 4 | 13.77 | 16.40 | 24.14 | 27.79 |
| CV-MP | 4 | 6.20 | 12.52 | 27.49 | 27.67 |
| Queue-responsive | 4 | -8.63 | 0.97 | 5.20 | 5.66 |
| CN-MP | 4 | 14.08 | 17.04 | 26.90 | 31.13 |
| WNCN-MP | 4 | 12.19 | 14.19 | 29.48 | 30.11 |
| W*NCN-MP | 4 | 7.48 | 18.08 | 24.16 | 23.67 |
| W*CN-MP | 4 | 12.31 | 16.81 | 23.65 | 24.43 |
| Coordinated Auction | 4 | -42.67 | -38.15 | -18.06 | -13.98 |

### Mean paired travel-time improvement at demand scale 1

| Method | Matched seeds | Outer car (%) | Outer motorcycle (%) | Central car (%) | Central motorcycle (%) |
|---|---:|---:|---:|---:|---:|
| Fixed-time | 4 | 0.00 | 0.00 | 0.00 | 0.00 |
| Switching-Loss MP | 3 | 9.43 | 19.99 | 29.25 | 32.06 |
| C-MP | 1 | 32.83 | 33.73 | 27.40 | 27.70 |
| TD-MP | 1 | -13.55 | -13.99 | 2.14 | 2.16 |
| CV-MP | 4 | -9.54 | -11.48 | 15.22 | 23.06 |
| Queue-responsive | 4 | -18.40 | -10.80 | 15.64 | 15.64 |
| CN-MP | 0 | — | — | — | — |
| WNCN-MP | 0 | — | — | — | — |
| W*NCN-MP | 4 | 16.82 | 15.86 | 23.20 | 29.63 |
| W*CN-MP | 4 | 26.12 | 19.25 | 27.92 | 29.75 |
| Coordinated Auction | 2 | -108.55 | -110.46 | -93.17 | -90.78 |

## Figure placement

Use one vehicle–path group per journey figure at approximately 16 cm width. Choose the figures needed to support the main text and place the remaining strata in the appendix. Every exported figure retains all eleven methods. For pairwise matrices, use a landscape page at approximately 23 cm width. Column identifiers match the identifiers next to the row names. Each non-diagonal cell reports a paired mean difference and its sample count.

The `paper/figures` directory contains separate travel-time, waiting-time and pairwise figures for all twelve demand–vehicle–path groups. The `paper/tables` directory contains full method tables and all pairwise comparisons. The source dataset retains its recorded acceptance status.