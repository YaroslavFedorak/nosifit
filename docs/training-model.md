# Training model (v2)

An evidence-informed, heuristic training-load model for decision support.
Research informs its structure and the direction of every effect, but many
numbers (half-life, readiness scale, curve shapes, contribution weights,
novelty premium, sleep penalty, volume bands) are engineering assumptions,
labelled as such in `parameters.py`. It is not a scientifically validated
algorithm and not a physiological measurement: internal scores are bounded
and stabilised, and the UI shows levels and states instead of percentages.

Code: `backend/app/services/training/model/`. Every coefficient lives in
`parameters.py` with its unit, purpose, evidence, confidence and a
`heuristic` flag that marks engineering assumptions.

## Two separate trees

```text
Muscle model                                   Session tree (dashboard / heatmap)
------------                                   ----------------------------------
logged sets (sets, reps|seconds, kg, RPE)      doses
  -> exercise stimulus  s(RIR)                   -> hard_sets, session_training_stress_proxy,
  -> contribution weights (catalog profile)         volume_load_kg, muscle_sets
  -> muscle stimulus | muscle fatigue            -> heatmap level vs the user's typical session
  -> exposure E7/E28 | local fatigue
  -> readiness (x sleep modifier)
  -> states (hysteresis)
  -> Stage 1: muscle priority + session sets
  -> Stage 2: exercise selection
  -> prescription (sets, reps|seconds, target RIR)
```

The session tree never blocks or prioritises muscles.

## Formulas

| Step | Formula | Notes |
|---|---|---|
| Effort | `RIR = clamp(10 - RPE, 0, 10)`, missing RPE -> `DEFAULT_RIR = 3` | operational mapping; self-rated RIR has ~1 rep error |
| Set stimulus | `s(r) = sigmoid((6 - r) / 2) / sigmoid(3)` | 1.0 at failure, saturating, monotone |
| Set fatigue | `c(r) = s(r) * (1 + exp(-r))` | 2x stimulus at RIR 0, ~1.14x at RIR 2 |
| Contribution | `w = share / max_share`; secondary capped at `0.5` | catalog `muscle_load_profile`; cap from Pelland (fractional sets) |
| Novelty | `1 + 0.25 * smoothstep(7, 42, days since last done)` | heuristic repeated-bout effect, fatigue only |
| Exposure | `E(t) = 7/tau * sum(stimulus * exp(-age_days / tau))`, tau 7 and 28 | effective sets per week, no hard windows |
| Local fatigue | `L(t) = sum(fatigue * 2^(-age_h / 30))` | one half-life for everyone |
| Readiness | `exp(-L / 8) * m_sleep` | 8 is a stabilising scale, not a capacity |
| Sleep | `m = 1 - 0.15 * (1 - exp(-D / 360))`, `D = sum(deficit_k * exp(-k / 5))` vs 7 h need | readiness only; no data = 1.0 |
| Priority | `need * availability * weak * focus * opportunity` | availability = smoothstep(0.50, 0.85, readiness) |
| Session sets | `round(min(max(mid / sessions, 2), mid - E7, 8) * availability)` | weekly band never becomes one session |
| Exercise score | `target + 0.3 goal_fit + 0.15 diversity - 0.6 conflict - 0.1 recent` | greedy, marginal, tie-break difficulty then slug |

Difficulty and risk only filter exercises by experience; they never scale
stimulus. Load (kg) and reps do not change muscle stimulus (hypertrophy is
load-independent near failure); kg feeds tonnage and the e1RM trend.

## What the numbers mean

| Value | Meaning | Shown to users as |
|---|---|---|
| `weekly_sets` | 7-day mean of E7: effective sets per week (a set at RIR 0 = 1.0, RIR 2 = 0.93) | "~9 sets / week" with the target band |
| `target.lower/upper` | recommendation band for goal x experience (not physiological limits) | band |
| `readiness` | low / moderate / ready / recovered | Low readiness / Moderate readiness / Ready / Recovered |
| `readiness_score` | internal 0-1 estimate | not shown as a percentage |
| `state` | accumulated_fatigue, high_fatigue, underloaded, recovery_available, appropriate | explained with reason keys |
| `hard_sets` | sets weighted by proximity to failure | heatmap tooltip |
| `session_training_stress_proxy` | sets weighted by fatigue cost; a proxy | heatmap level only |
| `volume_load_kg` | tonnage | descriptive |

`underloaded` requires both the smoothed weekly exposure and E28 below the
lower target and at least 14 days of history; "below target this week" is a
separate, weaker signal. Neither is relative to other muscles.

## Old vs new

| Old | Problem | New |
|---|---|---|
| `internal_load` = sets x reps x 6 multipliers x capacity (BMI, FFMI, BMR, age...) | arbitrary units, mixed stimulus and fatigue | `hard_sets`, `session_training_stress_proxy`, `volume_load_kg` (legacy column still written until the dashboard score moves) |
| `muscle_loads` keyed by exercise id | read as muscles by analysers | column stores `{muscle: effective sets}`; API key `muscle_sets` |
| weak/overloaded vs the median (0.70 / 1.35) | always "weak" muscles; unstable | absolute bands + readiness with hysteresis |
| 14-day hard window, no decay | sessions dropped out abruptly | exponential exposure and fatigue |
| recovery `training_score` U-shaped from raw load | rest days scored 30 | readiness of recently trained muscles (100 when rested) |
| heatmap `percent` | load / max(chronic mean, minimum) | `level` vs the user's typical session |

## Evidence

| Decision | Evidence | Confidence |
|---|---|---|
| Sets per muscle per week as the volume unit | Schoenfeld 2017; Baz-Valle 2022; Pelland 2024/2026 | moderate |
| Indirect sets capped at 0.5 | Pelland 2024/2026 (fractional counting fits best) | moderate |
| Stimulus rises toward failure, saturating | Robinson 2024; Refalo 2023; Grgic 2022; ACSM 2026 | moderate (shape heuristic) |
| Failure costs extra recovery | Moran-Navarro 2017 | moderate (magnitude heuristic) |
| Hypertrophy load-independent; strength favours heavy loads | Schoenfeld 2017; Lopez 2021; Currier 2023 | high |
| Frequency mostly a distribution tool | Schoenfeld, Grgic & Krieger 2019; Pelland; ACSM 2026 (>= 2 days/week) | moderate |
| Low doses maintain | Spiering 2021; Bickel 2011 | moderate |
| Sleep loss has a small effect on strength | Knowles 2018; Craven 2022; Watson 2015 (>= 7 h) | moderate (magnitude heuristic) |
| No ACWR | Impellizzeri 2020/2021; Lolli 2019 | high |
| Ranges, not individual precision | Hubal 2005; Hecksteden 2015/2018 | high |
| Energy deficit: preserve rather than build | Murphy & Koehler 2022 | moderate |

## Known limitations

* One RPE per exercise; sets of different effort are averaged.
* Session RPE is not collected yet, so there is no measured systemic load;
  `fatigue_after` can carry a CR-10 rating later as an extra signal.
* Contribution weights inside the 0.5 cap come from the catalog profile,
  not from research.
* Half-life, readiness scale, novelty premium, sleep penalty and the volume
  bands are heuristics; tests check that recommendations are robust to them.
* No muscle-specific recovery rates, no eccentric emphasis, no injuries.
* Age and sex are deliberately not used.

## Pending cleanup (second pass)

Kept until every consumer has moved:

* `TrainingSession.internal_load` (dashboard session score) and the
  `services/training/load/*` engine, `load_service`, `load_index_service`.
* `PerformanceState.training_load` (shown in `/api/training/analytics`).
* `training_analysis/analyzers/*` and `_build_recommendations_legacy`.
* `dashboard/training/metrics.analyze_muscles`, `training/analytics/*`,
  `FatigueState`, empty `training/utils/*` and `data/scoring/*.json`.
* Rename the `muscle_loads` column to `muscle_sets`.
