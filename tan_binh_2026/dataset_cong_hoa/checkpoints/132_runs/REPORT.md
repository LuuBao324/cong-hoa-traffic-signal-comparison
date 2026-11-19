# Four-seed dataset report

This checkpoint contains 132 signed runs from 11 methods, three demand levels and four independent seeds (100–103). It contains 528 tracked vehicle records. The planned 24-seed dataset will extend these same experiments.

## Execution and quality

- all four arrived runs: 115
- censored probes: 34
- collisions: 674
- teleports: 674
- event affected runs: 95
- probe teleports: 1
- probe collisions: 1
- paired valid rows: 460
- valid pairwise rows: 2088

The strict acceptance audit returned accepted=false. The approved main comparison policy includes runs with all four arrivals. Quality events remain recorded. Runs with censored probes are retained in dataset.csv and excluded from the main travel-time comparisons. Four tracked vehicles within one run share the same seed.

## Travel times by demand level and tracked journey

Times are seconds. Each row reports the mean and sample standard deviation across eligible seeds. Read every value alongside its valid sample count. The paired percentage improvement uses matched fixed-time runs. Positive values indicate shorter travel times.

Corridor-related reference demand is 36,000 journeys/hour at scale 1.0. Equal opposite-direction demand is assumed from the approximately 3,000 vehicles per ten-minute one-direction observation. Generated corridor-related journeys and measured vehicle passages at one section use different definitions.

### Scale 0.1, probe_car

| Method | Valid seeds | Mean travel time (s) | SD (s) | Paired seeds | Mean improvement vs fixed-time (%) |
|---|---:|---:|---:|---:|---:|
| c_mp | 4/4 | 225.50 | 11.55 | 4 | 28.48 |
| cn_mp_2024 | 4/4 | 206.94 | 7.99 | 4 | 34.37 |
| coordinated_auction_2024 | 4/4 | 243.38 | 38.49 | 4 | 22.82 |
| cv_mp_2025 | 4/4 | 238.88 | 13.62 | 4 | 24.24 |
| fixed_time | 4/4 | 315.31 | 0.24 | 4 | 0.00 |
| queue_responsive_2026 | 4/4 | 273.75 | 22.17 | 4 | 13.18 |
| switching_loss_mp | 4/4 | 205.94 | 6.54 | 4 | 34.69 |
| td_mp_2023 | 4/4 | 227.75 | 8.68 | 4 | 27.77 |
| wncn_mp_2024 | 4/4 | 214.12 | 4.55 | 4 | 32.09 |
| wstar_cn_mp_2024 | 4/4 | 227.12 | 22.07 | 4 | 27.96 |
| wstar_ncn_mp_2024 | 4/4 | 216.88 | 14.27 | 4 | 31.22 |

### Scale 0.1, probe_motorcycle

| Method | Valid seeds | Mean travel time (s) | SD (s) | Paired seeds | Mean improvement vs fixed-time (%) |
|---|---:|---:|---:|---:|---:|
| c_mp | 4/4 | 225.69 | 10.28 | 4 | 27.91 |
| cn_mp_2024 | 4/4 | 209.12 | 7.40 | 4 | 33.20 |
| coordinated_auction_2024 | 4/4 | 275.69 | 57.76 | 4 | 11.92 |
| cv_mp_2025 | 4/4 | 237.12 | 15.50 | 4 | 24.26 |
| fixed_time | 4/4 | 313.06 | 0.62 | 4 | 0.00 |
| queue_responsive_2026 | 4/4 | 274.25 | 23.17 | 4 | 12.41 |
| switching_loss_mp | 4/4 | 210.88 | 10.96 | 4 | 32.64 |
| td_mp_2023 | 4/4 | 216.94 | 6.19 | 4 | 30.70 |
| wncn_mp_2024 | 4/4 | 216.19 | 4.85 | 4 | 30.94 |
| wstar_cn_mp_2024 | 4/4 | 215.88 | 10.46 | 4 | 31.05 |
| wstar_ncn_mp_2024 | 4/4 | 219.38 | 13.96 | 4 | 29.93 |

### Scale 0.1, probe_car_center

| Method | Valid seeds | Mean travel time (s) | SD (s) | Paired seeds | Mean improvement vs fixed-time (%) |
|---|---:|---:|---:|---:|---:|
| c_mp | 4/4 | 216.25 | 9.11 | 4 | 31.36 |
| cn_mp_2024 | 4/4 | 206.56 | 7.68 | 4 | 34.44 |
| coordinated_auction_2024 | 4/4 | 242.88 | 36.77 | 4 | 22.92 |
| cv_mp_2025 | 4/4 | 228.38 | 8.35 | 4 | 27.51 |
| fixed_time | 4/4 | 315.06 | 0.43 | 4 | 0.00 |
| queue_responsive_2026 | 4/4 | 258.88 | 12.79 | 4 | 17.83 |
| switching_loss_mp | 4/4 | 218.88 | 12.91 | 4 | 30.53 |
| td_mp_2023 | 4/4 | 215.81 | 13.60 | 4 | 31.50 |
| wncn_mp_2024 | 4/4 | 209.62 | 8.93 | 4 | 33.47 |
| wstar_cn_mp_2024 | 4/4 | 216.75 | 9.19 | 4 | 31.20 |
| wstar_ncn_mp_2024 | 4/4 | 211.00 | 6.64 | 4 | 33.03 |

### Scale 0.1, probe_motorcycle_center

| Method | Valid seeds | Mean travel time (s) | SD (s) | Paired seeds | Mean improvement vs fixed-time (%) |
|---|---:|---:|---:|---:|---:|
| c_mp | 4/4 | 213.31 | 9.13 | 4 | 31.69 |
| cn_mp_2024 | 4/4 | 204.88 | 9.68 | 4 | 34.39 |
| coordinated_auction_2024 | 4/4 | 239.56 | 36.76 | 4 | 23.28 |
| cv_mp_2025 | 4/4 | 225.75 | 8.19 | 4 | 27.70 |
| fixed_time | 4/4 | 312.25 | 0.00 | 4 | 0.00 |
| queue_responsive_2026 | 4/4 | 256.25 | 12.64 | 4 | 17.93 |
| switching_loss_mp | 4/4 | 207.00 | 10.72 | 4 | 33.71 |
| td_mp_2023 | 4/4 | 213.38 | 13.69 | 4 | 31.67 |
| wncn_mp_2024 | 4/4 | 207.81 | 10.46 | 4 | 33.45 |
| wstar_cn_mp_2024 | 4/4 | 214.00 | 9.19 | 4 | 31.47 |
| wstar_ncn_mp_2024 | 4/4 | 208.31 | 6.64 | 4 | 33.29 |

### Scale 0.5, probe_car

| Method | Valid seeds | Mean travel time (s) | SD (s) | Paired seeds | Mean improvement vs fixed-time (%) |
|---|---:|---:|---:|---:|---:|
| c_mp | 4/4 | 260.56 | 27.41 | 4 | 17.29 |
| cn_mp_2024 | 4/4 | 270.69 | 28.80 | 4 | 14.08 |
| coordinated_auction_2024 | 4/4 | 449.50 | 79.47 | 4 | -42.67 |
| cv_mp_2025 | 4/4 | 295.56 | 49.50 | 4 | 6.20 |
| fixed_time | 4/4 | 315.06 | 0.38 | 4 | 0.00 |
| queue_responsive_2026 | 4/4 | 342.25 | 54.36 | 4 | -8.63 |
| switching_loss_mp | 4/4 | 290.06 | 36.44 | 4 | 7.93 |
| td_mp_2023 | 4/4 | 271.69 | 15.45 | 4 | 13.77 |
| wncn_mp_2024 | 4/4 | 276.62 | 28.84 | 4 | 12.19 |
| wstar_cn_mp_2024 | 4/4 | 276.25 | 31.71 | 4 | 12.31 |
| wstar_ncn_mp_2024 | 4/4 | 291.50 | 27.51 | 4 | 7.48 |

### Scale 0.5, probe_motorcycle

| Method | Valid seeds | Mean travel time (s) | SD (s) | Paired seeds | Mean improvement vs fixed-time (%) |
|---|---:|---:|---:|---:|---:|
| c_mp | 4/4 | 235.56 | 21.75 | 4 | 25.05 |
| cn_mp_2024 | 4/4 | 260.75 | 16.54 | 4 | 17.04 |
| coordinated_auction_2024 | 4/4 | 434.19 | 65.83 | 4 | -38.15 |
| cv_mp_2025 | 4/4 | 275.00 | 39.36 | 4 | 12.52 |
| fixed_time | 4/4 | 314.31 | 0.62 | 4 | 0.00 |
| queue_responsive_2026 | 4/4 | 311.25 | 24.91 | 4 | 0.97 |
| switching_loss_mp | 4/4 | 256.12 | 11.50 | 4 | 18.51 |
| td_mp_2023 | 4/4 | 262.75 | 24.59 | 4 | 16.40 |
| wncn_mp_2024 | 4/4 | 269.69 | 30.85 | 4 | 14.19 |
| wstar_cn_mp_2024 | 4/4 | 261.44 | 22.59 | 4 | 16.81 |
| wstar_ncn_mp_2024 | 4/4 | 257.50 | 18.86 | 4 | 18.08 |

### Scale 0.5, probe_car_center

| Method | Valid seeds | Mean travel time (s) | SD (s) | Paired seeds | Mean improvement vs fixed-time (%) |
|---|---:|---:|---:|---:|---:|
| c_mp | 4/4 | 214.38 | 16.61 | 4 | 31.96 |
| cn_mp_2024 | 4/4 | 230.31 | 9.49 | 4 | 26.90 |
| coordinated_auction_2024 | 4/4 | 371.94 | 77.40 | 4 | -18.06 |
| cv_mp_2025 | 4/4 | 228.44 | 17.58 | 4 | 27.49 |
| fixed_time | 4/4 | 315.06 | 0.12 | 4 | 0.00 |
| queue_responsive_2026 | 4/4 | 298.69 | 23.72 | 4 | 5.20 |
| switching_loss_mp | 4/4 | 228.69 | 8.28 | 4 | 27.41 |
| td_mp_2023 | 4/4 | 239.00 | 10.75 | 4 | 24.14 |
| wncn_mp_2024 | 4/4 | 222.19 | 20.88 | 4 | 29.48 |
| wstar_cn_mp_2024 | 4/4 | 240.56 | 16.17 | 4 | 23.65 |
| wstar_ncn_mp_2024 | 4/4 | 238.94 | 13.92 | 4 | 24.16 |

### Scale 0.5, probe_motorcycle_center

| Method | Valid seeds | Mean travel time (s) | SD (s) | Paired seeds | Mean improvement vs fixed-time (%) |
|---|---:|---:|---:|---:|---:|
| c_mp | 4/4 | 212.81 | 15.16 | 4 | 31.87 |
| cn_mp_2024 | 4/4 | 215.12 | 7.20 | 4 | 31.13 |
| coordinated_auction_2024 | 4/4 | 356.06 | 90.35 | 4 | -13.98 |
| cv_mp_2025 | 4/4 | 225.94 | 17.62 | 4 | 27.67 |
| fixed_time | 4/4 | 312.38 | 0.14 | 4 | 0.00 |
| queue_responsive_2026 | 4/4 | 294.69 | 24.95 | 4 | 5.66 |
| switching_loss_mp | 4/4 | 225.31 | 8.34 | 4 | 27.87 |
| td_mp_2023 | 4/4 | 225.56 | 5.46 | 4 | 27.79 |
| wncn_mp_2024 | 4/4 | 218.31 | 18.48 | 4 | 30.11 |
| wstar_cn_mp_2024 | 4/4 | 236.06 | 17.21 | 4 | 24.43 |
| wstar_ncn_mp_2024 | 4/4 | 238.44 | 12.68 | 4 | 23.67 |

### Scale 1, probe_car

| Method | Valid seeds | Mean travel time (s) | SD (s) | Paired seeds | Mean improvement vs fixed-time (%) |
|---|---:|---:|---:|---:|---:|
| c_mp | 1/4 | 278.75 | Unavailable | 1 | 32.83 |
| cn_mp_2024 | 0/4 | Unavailable | Unavailable | 0 | Unavailable |
| coordinated_auction_2024 | 2/4 | 763.25 | 20.15 | 2 | -108.55 |
| cv_mp_2025 | 4/4 | 375.75 | 29.11 | 4 | -9.54 |
| fixed_time | 4/4 | 346.56 | 45.95 | 4 | 0.00 |
| queue_responsive_2026 | 4/4 | 411.75 | 106.97 | 4 | -18.40 |
| switching_loss_mp | 3/4 | 319.25 | 20.48 | 3 | 9.43 |
| td_mp_2023 | 1/4 | 471.25 | Unavailable | 1 | -13.55 |
| wncn_mp_2024 | 0/4 | Unavailable | Unavailable | 0 | Unavailable |
| wstar_cn_mp_2024 | 4/4 | 253.38 | 5.68 | 4 | 26.12 |
| wstar_ncn_mp_2024 | 4/4 | 281.31 | 58.62 | 4 | 16.82 |

### Scale 1, probe_motorcycle

| Method | Valid seeds | Mean travel time (s) | SD (s) | Paired seeds | Mean improvement vs fixed-time (%) |
|---|---:|---:|---:|---:|---:|
| c_mp | 1/4 | 276.00 | Unavailable | 1 | 33.73 |
| cn_mp_2024 | 0/4 | Unavailable | Unavailable | 0 | Unavailable |
| coordinated_auction_2024 | 2/4 | 753.50 | 2.83 | 2 | -110.46 |
| cv_mp_2025 | 4/4 | 378.94 | 35.33 | 4 | -11.48 |
| fixed_time | 4/4 | 344.44 | 48.27 | 4 | 0.00 |
| queue_responsive_2026 | 4/4 | 378.75 | 34.60 | 4 | -10.80 |
| switching_loss_mp | 3/4 | 274.42 | 24.30 | 3 | 19.99 |
| td_mp_2023 | 1/4 | 474.75 | Unavailable | 1 | -13.99 |
| wncn_mp_2024 | 0/4 | Unavailable | Unavailable | 0 | Unavailable |
| wstar_cn_mp_2024 | 4/4 | 277.38 | 33.77 | 4 | 19.25 |
| wstar_ncn_mp_2024 | 4/4 | 283.44 | 84.09 | 4 | 15.86 |

### Scale 1, probe_car_center

| Method | Valid seeds | Mean travel time (s) | SD (s) | Paired seeds | Mean improvement vs fixed-time (%) |
|---|---:|---:|---:|---:|---:|
| c_mp | 1/4 | 228.50 | Unavailable | 1 | 27.40 |
| cn_mp_2024 | 0/4 | Unavailable | Unavailable | 0 | Unavailable |
| coordinated_auction_2024 | 2/4 | 608.00 | 94.75 | 2 | -93.17 |
| cv_mp_2025 | 4/4 | 267.00 | 9.46 | 4 | 15.22 |
| fixed_time | 4/4 | 314.94 | 0.24 | 4 | 0.00 |
| queue_responsive_2026 | 4/4 | 265.69 | 4.80 | 4 | 15.64 |
| switching_loss_mp | 3/4 | 222.75 | 6.31 | 3 | 29.25 |
| td_mp_2023 | 1/4 | 308.00 | Unavailable | 1 | 2.14 |
| wncn_mp_2024 | 0/4 | Unavailable | Unavailable | 0 | Unavailable |
| wstar_cn_mp_2024 | 4/4 | 227.00 | 12.62 | 4 | 27.92 |
| wstar_ncn_mp_2024 | 4/4 | 241.88 | 24.49 | 4 | 23.20 |

### Scale 1, probe_motorcycle_center

| Method | Valid seeds | Mean travel time (s) | SD (s) | Paired seeds | Mean improvement vs fixed-time (%) |
|---|---:|---:|---:|---:|---:|
| c_mp | 1/4 | 225.75 | Unavailable | 1 | 27.70 |
| cn_mp_2024 | 0/4 | Unavailable | Unavailable | 0 | Unavailable |
| coordinated_auction_2024 | 2/4 | 599.12 | 85.38 | 2 | -90.78 |
| cv_mp_2025 | 4/4 | 241.06 | 22.06 | 4 | 23.06 |
| fixed_time | 4/4 | 313.25 | 2.00 | 4 | 0.00 |
| queue_responsive_2026 | 4/4 | 264.25 | 3.46 | 4 | 15.64 |
| switching_loss_mp | 3/4 | 213.00 | 5.65 | 3 | 32.06 |
| td_mp_2023 | 1/4 | 305.50 | Unavailable | 1 | 2.16 |
| wncn_mp_2024 | 0/4 | Unavailable | Unavailable | 0 | Unavailable |
| wstar_cn_mp_2024 | 4/4 | 220.12 | 14.91 | 4 | 29.75 |
| wstar_ncn_mp_2024 | 4/4 | 220.50 | 17.02 | 4 | 29.63 |
