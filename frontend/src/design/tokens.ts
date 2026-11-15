/**
 * The design tokens as data, mirroring `tokens.css`. The web interface reads
 * the CSS variables; a native client can read the same roles from here.
 */
export const color = {
  paper: "oklch(16.5% 0.012 260)",
  paper2: "oklch(20.5% 0.014 260)",
  paper3: "oklch(24.5% 0.016 260)",
  paper4: "oklch(29.5% 0.018 260)",
  rule: "oklch(29% 0.014 260)",
  edge: "oklch(52% 0.016 260)",
  ink: "oklch(95% 0.006 260)",
  ink2: "oklch(83% 0.012 260)",
  muted: "oklch(69% 0.016 260)",
  accent: "oklch(83% 0.13 88)",
  accentInk: "oklch(22% 0.035 88)",
  training: "oklch(83% 0.13 88)",
  nutrition: "oklch(73% 0.115 298)",
  recovery: "oklch(77% 0.085 200)",
  water: "oklch(72% 0.1 245)",
  success: "oklch(77% 0.11 158)",
  warn: "oklch(79% 0.11 65)",
  error: "oklch(71% 0.14 22)",
} as const;

/** Spacing steps in px: the only distances layouts use. */
export const space = { "3xs": 2, "2xs": 4, xs: 8, sm: 12, md: 16, lg: 24, xl: 40, "2xl": 64 } as const;

/** Type sizes in px at a 16px root, on a 1.2 scale. */
export const text = { xs: 12, sm: 14, md: 16, lg: 19.2, xl: 23, "2xl": 27.6, "3xl": 33.2, figure: 39.8 } as const;

export const radius = { control: 8, card: 12, pill: 999 } as const;

/** Heights of controls and touch targets in px. */
export const size = { control: 40, controlLarge: 48, tap: 44 } as const;

export const motion = { micro: 120, short: 220, long: 420 } as const;

/** The module or state a block's data marks are coloured for. */
export type Tone = "training" | "nutrition" | "recovery" | "water" | "success" | "warn" | "error";
