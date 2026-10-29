# NosiFit interface (React)

A mobile-first interface for NosiFit, served by the Flask app under **`/app`**.
It reads and writes through the same JSON API and the same session cookie as
the classic pages, which stay untouched until the owner decides to switch.

| Page | URL | Needs sign-in |
|---|---|---|
| Landing (4 screens) | `/app/welcome` | no |
| How it works | `/app/how-it-works` | no |
| Today | `/app/dashboard` | yes |
| Training (Today / History / Tips) | `/app/training` | yes |
| Nutrition | `/app/nutrition` | yes |
| Recovery | `/app/recovery` | yes |

Stack: React 19, React Router, TanStack Query, Tailwind CSS 4, Lucide icons,
Inter (variable, self-hosted), TypeScript, Vite.

## Commands

```bash
cd frontend
npm ci
npm run build       # type-check, then build into ../web/app/static/app
npm run watch       # rebuild on every change
npm run typecheck
```

The build is committed (like the compiled TypeScript of the classic pages) and
CI fails when it does not match the sources. Flask versions static files by a
hash computed **at start-up**, and the browser caches those URLs for a year:
after a rebuild, restart the Flask process (or hard-reload) to see the change.

## How it is served

`web/app/routes/spa/pages.py` renders `web/app/templates/app/spa.html`: an
empty `<div id="root">`, the language and the signed-in user as a JSON block
(`#nosi-bootstrap`), and the two files in `assets/` (`app.js`, `app.css`).
Signed-out visitors are sent to the sign-in page for the four app pages.
Recommendation texts arrive from the API as translation keys; they are resolved
with the namespaces the server already serves at `/api/i18n/<locale>/<ns>`.

## Design rules (enforced in `src/styles.css` and the shared components)

- **Three breakpoints**, nothing else: mobile (default), `tab:` ≥ 768px, `desk:` ≥ 1100px.
- **Text is never below 12px.** `text-badge` (11px) exists for tiny badge labels only.
- **Touch targets are at least 44px** (`min-h-tap`, `size-tap`; 52px for the main action).
- **Depth is rare**: gradients, glass and glow are reserved for the hero action
  button and one or two status cards per page (`tone="hero"`, `tone="glass"`).
  Lists stay flat; a thin top strip in the module colour marks the module.
- **Nothing inside a card scrolls.** Long lists grow the page and end in a
  "Show more" button; full history opens in a bottom sheet (`Sheet`).
- **One number format**: a dot as the decimal separator in every language (`lib/format.ts`).
- **Colour comes from `data-accent`** (`training`, `nutrition`, `recovery`, `water`).

## Adding a page

1. Create `src/pages/<Name>.tsx` with a default export and lazy-load it in `src/App.tsx`.
2. Add its path to `USER_PAGES` or `PUBLIC_PAGES` in `web/app/routes/spa/pages.py`.
3. Put strings in `src/i18n/en.ts` and `src/i18n/uk.ts` (the Ukrainian file must have every key).
4. Data goes through `src/api/queries.ts` and `src/api/mutations.ts`.

## Known gaps

- Polish and Russian fall back to English for the new interface's own strings;
  server-provided texts (recommendations, exercise and muscle names) are localized.
- The barcode scanner and the weekly plan editor still live in the classic
  interface; the app links to them.
