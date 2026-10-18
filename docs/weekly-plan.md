# Weekly training plan

A plan is one row of `te_training_plans`; `days` is JSON keyed by weekday
(`mon` ... `sun`). A day is `{"exercises": [...], "location": ..., "equipment": ...}`.
A missing day, or one without exercises, is a rest day.

## Location and equipment are separate

| Field | Values | Meaning |
|---|---|---|
| `location` | `home`, `gym`, `outdoors` | where the day is trained |
| `equipment` | list of slugs, or `null` | what is at hand; `null` = not limited |

`bodyweight` is always available. `outdoors` never exceeds
`plan_days.OUTDOOR_EQUIPMENT` (bar, dip bars, rings, band, jump rope), whatever
was selected. Rules live in `backend/app/services/training/plan_days.py`.

A hand-built day is checked only when it has an explicit `equipment` list:
an exercise needing anything else is refused (400 `invalid_input`). A day that
omits `location`/`equipment` in an update keeps what it had; `null` clears them.
`PUT /plans/<id>` keeps days the request does not mention.

## Completing a day

`POST /api/training/plans/<id>/days/<day>/complete` records the planned
workout as a finished `training_sessions` row (so the dashboard, heatmap and
training model see it like any logged workout).

* The row carries `plan_id`, `plan_day` and `plan_date`; a partial unique index
  on `(plan_id, plan_date)` allows one per plan and date, so repeating the
  request returns the first session (`already_completed: true`).
* Only the current week (Monday to Sunday, in the training module's local day)
  and not a future day. A past day counts on its own date.
* A rest day cannot be completed (409 `rest_day`).
* The session is a copy of what was planned. Editing the plan afterwards never
  changes it, and completed days stay completed. Deleting a plan keeps its
  sessions (`plan_id` becomes `NULL`).

`GET /api/training/plans/<id>/week` returns the seven days with `completed`.

## Premium generation

`POST /api/training/plans/generate` (Premium, enforced on the server, 403
`premium_required` otherwise) returns an **unsaved draft**; the client edits it
and saves through the ordinary plan routes. No AI service, no stored state.

Input: `training_days` (at most six; the rest are rest days; default from the
profile's workouts per week) and optional per-day `location`/`equipment`.

`plan_builder.build_week`: the split templates only decide which muscle groups
a day covers (`SEQUENCES`); the days are placed on the calendar so consecutive
days share the fewest muscles. Each day then runs the training model's
Stage 1 (`allocate_sets`, what is still missing from the weekly band) and
Stage 2 (`select_exercises`); the sets already planned this week act as the
history, so later days see them. Only exercises from
`training/data/plan_library.json` are used; at most one variant of a movement
per day (`same_exercise_groups`), at most two uses per exercise per week.

The result can be shorter than a full session. It is never padded: muscles that
cannot reach the weekly band (equipment, no pulling exercise at home) are
reported in `notes` (`volume_short`, `split_skips`), as are back-to-back days
that train the same muscles and days the weekly volume does not need.

### Limitation: injuries

`injuries` and `user_injuries` hold only a name, a description and a note. Nothing
links an injury to a muscle, movement or exercise, so generation cannot avoid
anything for an injury and never claims to. When the user has injuries the
draft carries the note `injuries_not_considered`. Real contraindications need a
mapping on the exercise catalog first.
