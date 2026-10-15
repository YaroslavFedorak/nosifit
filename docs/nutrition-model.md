# Nutrition model

How NosiFit calculates targets, fluids, diet quality, recommendations and
statistics. Each rule says whether its numbers come from a published
reference or are a product decision. Nothing here is medical advice: the
numbers are estimates meant to support decisions, not clinical requirements.

Code: `backend/app/services/nutrition/`. Time: `backend/app/utils/clock.py`.
Numbers that can be checked on the real catalog: `python -m
web.scripts.nutrition_verification --baseline-ref <git revision>`.

## Principles

* **Unknown is not zero.** Fibre, sugar, saturated fat and salt can be
  unknown (`NULL`). Totals keep `*_complete` flags; scores and advice leave a
  nutrient out when it is unknown for most of the energy; nothing converts
  `NULL` into `0`.
* **No target is not a target of zero.** Goals carry `available`. A day
  without calorie target has `balance_status = "unavailable"`, `kcal_balance`
  and percentages `null`; it is never "over".
* **Reading never writes.** `get_goals` and every stats call are read-only.
* **One path per metric.** The water goal, the diet-quality score, the
  targets and the day are each computed in one place and reused by the page,
  the history, the statistics, the dashboard and the recommendations.
* **History is history.** A past day is compared with the targets stored for
  it and the weight of that day.

## The day (time zone)

"Today" is the calendar day in `APP_TIMEZONE` (default `Europe/Kyiv`; falls
back to `NOSI_FIT_TIMEZONE`, which the Telegram bot already uses). The
server's own clock and `TZ` no longer decide it. There is one zone for the
whole application because users have no zone of their own yet: a user far
from it sees their day change at the wrong hour. Meals, water, weights,
targets, statistics, the dashboard and the recommendations all use
`clock.today()`.

## Calorie and macro targets

Profile -> `calories_service` -> stored (when changed) -> read by `goals_service`.

1. **Validity.** Weight 30-300 kg, height 120-230 cm, age 15-100 are the range
   the adult formula is meant for. The profile form and API accept wider
   ranges (weight 20-400 kg, height 50-272 cm, age 10-120); outside the
   formula range there are simply **no targets** (`available: false`).
2. **BMR** (Mifflin-St Jeor): `10 kg + 6.25 cm - 5 age + s`, `s = +5` men,
   `-161` women, `-78` otherwise (the midpoint).
3. **TDEE** = BMR x activity factor: sedentary 1.20, light 1.375, moderate
   1.55, active 1.725, very active 1.90. The stored activity has two
   formats: the profile editor saves a label (`sedentary` ... `active`), the
   registration and complete-profile forms save the factor itself (`"1.2"`,
   `"1.375"`, `"1.55"`, `"1.725"`, `"1.9"`). `activity_level` reads both into
   one level, and targets and water both go through it. The label
   `very_active` is 11 characters and cannot be stored in the 10-character
   column, but `"1.9"` can, so that level exists only as the number. Unknown or
   missing activity: 1.55 for the targets (a documented fallback), no
   adjustment for water.
4. **Calories** = TDEE x goal factor: fat loss -15%, maintenance and
   recomposition 0, strength +5%, lean gain +8%, muscle gain +10%; floors
   1200 (women), 1500 (men), 1350 (otherwise); ceiling 6000. The factors are
   product decisions.
5. **Protein** = 2.0 g/kg (fat loss), 1.8 (recomposition, strength, lean
   gain), 1.6 (otherwise) of total body weight, capped at **35% of energy**
   (the upper bound of the US National Academies range). Total body weight
   overstates the need of a heavy person; the cap is the safeguard, a lean-mass
   based factor would be a product change.
6. **Fat** 28% of energy, kept within 20-35%; **carbohydrate** the rest, kept
   within 45-65% by moving energy between fat and carbohydrate. These are the
   same US ranges. Macro energy matches the calorie target within the rounding
   of 0.1 g per macro (under 1 kcal; checked for 5,000+ profiles in the tests).
7. **Fibre** target: the stored `fiber_goal`, default 30 g (about 14 g per
   1000 kcal at 2100 kcal).

There is no manual goal editing in the app: stored targets are a record of the
calculated ones, and the calculation is the authority. (The old branches that
supposed custom fat/carbohydrate targets, and the 70 kg weight they invented
for incomplete profiles, are gone.)

### Goal history

`nutrition_goal_history(user_id, effective_from, calories, protein, fat,
carbs, fiber)`. A row is written inside the flush that saves a profile whose
weight, height, age, sex, activity or goal changed (and the targets changed):
the profile form, onboarding and a new weight all go through it. Several changes
on one day keep the last: the row is written with one atomic
`INSERT ... ON CONFLICT (user_id, effective_from) DO UPDATE`, so two saves of the
same user at the same moment cannot collide on the unique key.

Concurrent saves follow one locking protocol (`goal_history.py`): a transaction
that writes a user's profile row first takes a transaction-scoped advisory lock
for that user (before the first UPDATE of the row, whichever column it changes),
so writers queue on the lock and never wait for each other's row lock while
holding it (no deadlock). The targets are then calculated from the committed
profile row plus this transaction's own changes - not from the possibly stale
in-memory object - so the history row always describes the state that is
saved, even when two saves change different fields (height by one, weight by
the other). This relies on PostgreSQL's READ COMMITTED isolation (the
project's default; a test checks it): under a snapshot isolation level the fresh
read would need to be a locking read instead.

A past day uses the last row on or before it. Days before the first row have nothing stored; they are **not**
reconstructed: today's targets are shown and the day is flagged
`goal_estimated`. The migration only creates the table.

## Calorie balance

`balance_status`: `unavailable` (no target), `no_data` (nothing logged),
`under` / `normal` / `over` with a tolerance of **10%** of the target either
way (a product decision: logged portions are never exact; the earlier
absolute 150 kcal was 5-12% depending on the target). `kcal_balance` =
consumed - target, `kcal_remaining` = max(target - consumed, 0), both `null`
without a target.

## Fluids (water)

Meaning: a **fluid goal for drinks** in litres, plus intake = manual water +
the fluid of logged drinks (`MealItem.liquid_ml`). It is not total water
including food, and not a requirement: needs vary with food, climate, exercise
and health.

`weight x ml/kg(age) / 1000`, with ml/kg 45 (up to 12 y), falling to about 38 at 17-18,
36 at 25, 35 at 40-41, 33 at 60, 30 from 100 y (35 when the age is unknown or
implausible; the common "30-40 ml per kg" rule of thumb), then x 1.03 for men,
x the activity factor (sedentary 1.00, light 1.025, moderate 1.05, active
1.10; a heuristic for sweat losses), clamped to 1.5-3.5 L (the floor is near
the EFSA adequate intake for drinks, about 1.6 L for women and 2.0 L for men).
Fat-loss and muscle-gain goals no longer change it: nothing supports that.
A missing or out-of-range weight gives **no goal** (`null`), not 0. Water may
be logged for a past day (up to 365 days back, not the future). The goal of a
past day uses the last weight recorded on or before it.

## Diet quality

`quality_service.calculate_quality(items, goals)` -> `score` 0-100 or `null`.

### Classification (one class per food)

Based on the canonical `Product.category`, stored in `MealItem.basis` when an
entry is logged (older entries read the product's category in one batched
query), never on names - so it is the same in uk, en, pl and ru. The category
does not decide alone:

| Class | Rule |
|---|---|
| **whole** | fruits, vegetables, berries, legumes, nuts, seeds, fish, seafood, poultry, meat, eggs, dairy - unless a guard below trips; cereal foods (grains, pasta, bread) with at least **1.5 g fibre per 100 kcal** (EU "source of fibre", a whole-grain proxy) |
| **processed** | sweets, snacks, fast food; any guarded whole food whose **salt is above 1.5 g/100 g** (meat, poultry, fish, seafood, legumes, vegetables, nuts, seeds - cured, smoked, canned, pickled, salted), dairy with **sugars above 5 g/100 g** (sweetened), cereal foods and sauces with sugars above 22.5 g or salt above 1.5 g/100 g |
| **neutral** | oils, cheese, sauces, culinary ingredients, prepared (mixed) dishes, drinks, refined cereal foods, milk fats (dairy with at least 80 g fat/100 g) |
| **unknown** | category `other`/missing, or a nutrient the rule needs is unknown (salt for guarded categories, sugar for dairy, fibre for cereal foods) |

Salt 1.5 g and sugars 22.5 g are the "high" bands of the UK front-of-pack
criteria (2016); 5 g sugars is their "low" band, which separates plain
milk/yoghurt (at most 5 g in the catalog) from sweetened (11 g and more).

**Where the category comes from.** Catalog products have one. A user's own
product has the one chosen in the product form (create and edit; the same ids
the server validates, `other` by default and for older products). Open Food
Facts products get a category only when the source's `categories_tags` point to
exactly one of ours through the table in `off_categories.py` (exact tags such as
`en:chocolates` -> `sweets`); no tags, no tag in the table, or tags that point to
two categories leave it `other`. Only string tags are considered; any other
value in the list (a damaged cache, an unexpected answer) is ignored rather than an
error. Generic tags (`en:beverages`, `en:meats`,
`en:fruits`, `en:snacks` ...) are not in the table, and nothing is guessed from a
name or from nutrients. Existing products are never re-categorised in bulk.
Products left in `other` are `unknown`; their fibre, sugar, saturated fat and
salt still count in the nutrient components of the score.

An entry keeps the category it was logged with, except `other`: that says
nothing, so the product's current category is used instead. Choosing a category
for a product therefore also classifies the entries logged before, while an
entry logged as `poultry` stays `poultry` if the product is later changed.

### Score

Shares are of the **energy** logged, so the amount of food does not matter,
the composition does. Each component is 0-100; the score is the weighted mean
of the components that can be measured.

| Component | Weight | 100 when | 0 when |
|---|---:|---|---|
| whole foods | 30 | whole share of classified energy >= 50% | 0% |
| processed foods | 15 | 0% | >= 50% |
| fibre | 20 | g per 1000 kcal >= the user's `fiber_goal / calorie_goal x 1000` (14 g default) | 0 |
| added sugar (proxy) | 15 | <= 10% of energy (WHO free sugars) | >= 20% |
| saturated fat | 10 | <= 10% of energy (WHO) | >= 20% |
| salt | 10 | <= 2.5 g per 1000 kcal (WHO 5 g/day at 2000 kcal) | >= 5 g |

Weights and the 50% targets are product decisions; the sugar, saturated fat
and salt limits are WHO guidelines. Between full and zero the score is linear.

* **Added sugar** is a proxy because only total sugars are known: sugars of
  fruit, berries, vegetables, legumes, nuts and seeds count as 0, dairy keeps
  5 g/100 g, everything else counts in full.
* A component is **left out** (weights renormalised) when its nutrient is
  known for less than half the energy; the shares are left out when more than
  half the energy is unclassified. If nothing is measurable, `score` is `null`
  with `reason: "insufficient_data"`.
* The day is **not scored** (`null`, `reason: "low_energy"`) below 25% of the
  calorie target (500 kcal without one), so a snack does not stand for a day.
  `no_data` / `no_energy` likewise. Percentages are still reported.
* `quality` = `{score, reason, whole_foods_percent, processed_foods_percent,
  neutral_percent, unclassified_percent, fiber, fiber_complete, energy_kcal,
  components}` - the same everywhere it appears (nutrition day, day details,
  recommendations summary `quality_score`, dashboard `nutrition.score`).

### Limits of the classification

Rules, not ingredient lists. Known weaknesses: cooked white pasta whose
catalog fibre is high reads as whole grain; brown rice and millet (about 1.4
g per 100 kcal) read as neutral; a plain meat or fish with an unknown salt
value is `unknown`; an unusual home recipe in a "whole" category is trusted.
`neutral` food is not penalised, only not credited. The dashboard's daily score
averages the training, nutrition and recovery scores, and the nutrition score
is **diet quality only** - it does not say whether the targets were met.

## Recommendations

`GET /api/nutrition/recommendations`; i18n keys + parameters, at most 5,
ordered by priority (stable, deterministic). Phases by local hour: morning
(<12), day (12-18), evening (18-21), late (21+). End-of-day rules fire in the
evening and late only. A "short" total is more than **20%** under target, "on
target" is within **10%**; these two and the phase hours are product decisions.

| Rule | Fires when | Priority |
|---|---|---|
| empty | nothing logged | low |
| profile incomplete | food logged, no targets | low |
| protein pacing | afternoon, more than 40% of the protein target still to go | low |
| calories low | evening+, under 70% of target | medium |
| calories remaining | evening+, 70-90% of target (not on a fat-loss goal) | low |
| calories excess | evening+, over 110% | medium |
| protein short | evening+, under 80% of target | medium (high late) |
| salt | any time, known salt above 5 g (WHO) | medium |
| fibre | evening+, fibre known for **every** entry and under 80% of target | low |
| added sugar | evening+, above 10% of energy (WHO) | low |
| saturated fat | evening+, above 10% of energy (WHO) | low |
| processed foods | evening+, more than half the classified energy | medium |
| few whole foods | evening+, under 25% of classified energy (half the 50% target) | low |
| hydration | evening+, fluid under 80% of the estimate | low |
| macro split | evening+, calories on target, no protein flag, fat or carbohydrate share 12 points off the target split | low |

Composition rules (fibre, sugar, saturated fat, quality, split) need at least
3 entries, a scorable day and calories not under 70% of the target, so a
barely eaten day gets the calorie message, not five more. Fat and
carbohydrate shortfalls are not advised: their targets are the energy left
after protein, not requirements of their own. The old catch-all "score < 45"
rule is gone; it fired on missing data, and the specific rules replace it.

## Statistics

* **Chart** (`/api/nutrition/stats?days=N`, 1-365): `kcal.values[i]` is
  `null` on a day without entries, `kcal.logged[i]` says so, a logged day
  with 0 kcal stays 0.
* **Average** `avg_kcal` = mean over days with logged energy; today is left
  out while earlier logged days exist (a day in progress is not an intake);
  `avg_kcal_days` counts them; `null` without any.
* **Weight series** covers the requested window only; `current_weight` is the
  latest weighing anywhere.
* **Weight trend** `weight_trend` is a code (`insufficient_data`, `stable`,
  `increasing`, `decreasing`) with `weight_trend_detail` (`change_kg`,
  `kg_per_week`, `span_days`, `measurements`). Over the last max(N, 14) days
  the Theil-Sen slope (median of the slopes between all pairs, so a single
  odd weighing does not move it; irregular dates are fine). Needs 3 weighings
  over 7 days. It reports a direction only if the fitted change is at least
  0.5 kg (about a day's normal fluctuation) and at least 0.1 kg a week.
* **Heatmap** percent and level use the targets of that day.
* **BMI**: `weight / height^2`, only for plausible values. `bmi_category` is
  the WHO adult class from age 18 (underweight < 18.5, normal < 25,
  overweight < 30, obese); under 18 or without an age it is `null` and
  `bmi_classified` is false - the number is shown without a class because
  children and adolescents are judged against growth charts.

## Entries and imports

* One entry weighs at most 5000 g in total (also for pieces and millilitres),
  next to the existing per-unit limits. `NaN`, infinite, zero and negative
  amounts are refused.
* Open Food Facts: kJ -> kcal (/4.184), sodium -> salt (x2.5), per-serving ->
  per 100 g with the label serving size, per-100 ml kept as such. Missing
  values stay unknown. Energy that differs from 4/9/4 arithmetic is a
  `energy_mismatch` **warning**, never a refusal (polyols, erythritol,
  alcohol, organic acids and fibre change the energy). Physical impossibilities
  (parts above their whole, more than 100 g of macros per 100 g) are still
  refused. Fibre is added to the macro mass because EU labels give available
  carbohydrate.

## API changes (compatible)

New or nullable fields: `goals.available`/`source`, `goals_available`,
`kcal_remaining`, `water_goal`/`water_percent`/`recommended` may be `null`,
`balance_status` also `unavailable` / `no_data`, `quality` is an object with
`score` possibly `null`, `weight_trend` is a code, `bmi_category`,
`bmi_classified`, heatmap `goal_estimated`, `/water` accepts `date`.
`docs/openapi.json` describes them.
