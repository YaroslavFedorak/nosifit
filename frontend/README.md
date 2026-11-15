# NosiFit interface (React)

The interface of NosiFit, served by the Flask app under **`/app`**. It reads
and writes through the same JSON API and the same session cookie as the
classic pages.

| Screen | URL | Needs sign-in |
|---|---|---|
| Landing | `/app/welcome` | no |
| How it works | `/app/how-it-works` | no |
| Today | `/app/dashboard` | yes |
| Nutrition (diary, any day with `?date=`) | `/app/nutrition` | yes |
| Training (Today, Plan, History with `?tab=`) | `/app/training` | yes |
| Recovery (sleep and habits) | `/app/recovery` | yes |
| Profile | `/app/profile` | yes |
| Settings | `/app/settings` | yes |

Stack: React 19, React Router, TanStack Query, Tailwind CSS 4, Lucide icons,
Inter (variable with its optical-size axis, self-hosted), TypeScript, Vite.

## Commands

```bash
cd frontend
npm ci
npm run build       # type-check, then build into ../web/app/static/app
npm run watch       # rebuild on every change
npm run typecheck
```

The build is committed and CI fails when it does not match the sources. Flask
versions static files by a hash computed **at start-up**: after a rebuild,
restart the Flask process to see the change.

## How the source is laid out

The layers only depend downwards, so the lower ones can move to a native
client unchanged.

| Folder | What it holds | Depends on |
|---|---|---|
| `src/design/tokens.ts`, `src/tokens.css` | Colours, type scale, spacing, radii, motion | nothing |
| `src/domain/` | Rules with no React and no DOM: portions, the day's next step, workout and plan shapes, barcodes | `api/types` |
| `src/api/` | Types of the API, queries and mutations | `domain`, `lib` |
| `src/ui/` | Buttons, fields, sheets, lists, charts, calendar: no data, no business rules | `design`, `lib` |
| `src/features/` | One folder per module: the pieces that join `ui` with `api` | everything above |
| `src/app/` | The shell: sidebar, tablet rail, phone tab bar, page frame | `features`, `ui` |
| `src/pages/` | One file per route: layout only | everything above |
| `src/i18n/` | `en` (the key list), `uk`, `pl`, `ru`; server-owned texts come from `/api/i18n` | `lib` |

## Design rules

- **Tokens only.** Every colour, size and radius comes from `tokens.css`. A
  block's module colour is set with `data-tone` and read through `text-tone`,
  `bg-tone`, `bg-tone-soft`. No gradients, no glow.
- **The accent is for actions.** The brand yellow marks the primary button and
  the current selection. The module hues colour data marks only.
- **Nothing recorded is never a zero.** A part of the day with no entry is
  offered as an action, not shown as `0` or an empty chart.
- **Recording is one sheet per kind.** Screens ask `useLog()` for the food
  picker, the sleep form or the weight form; they never mount their own.
- **Controls** are 44px tall on touch screens and 40px on a desktop with a
  mouse; form fields and main actions are 48px.
- **Three widths:** phone (default), `tab:` from 768px, `desk:` from 1100px.
  Components fill their box; only pages and the shell read the breakpoints.
- **One number format:** a dot as the decimal separator in every language.

## How it is served

`web/app/routes/spa/pages.py` renders `web/app/templates/app/spa.html`: an
empty `<div id="root">`, a JSON block (`#nosi-bootstrap`) with the language,
the signed-in user and what the account may use, and the two files in
`assets/`. The profile screens read `GET /profile/summary`.

## Adding a screen

1. Create `src/pages/<Name>.tsx` with a default export and lazy-load it in `src/App.tsx`.
2. Add its path to `USER_PAGES` or `PUBLIC_PAGES` in `web/app/routes/spa/pages.py`.
3. Add its strings to all four files in `src/i18n/` (a missing key is a type error).
4. Data goes through `src/api/queries.ts` and `src/api/mutations.ts`.
