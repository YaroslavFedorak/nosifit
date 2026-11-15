import { Dumbbell, HeartPulse, Sun, UtensilsCrossed, type LucideIcon } from "lucide-react";
import type { TKey } from "../i18n/en";

export interface NavItem {
  to: string;
  label: TKey;
  icon: LucideIcon;
}

/** The four places of the app. The profile and the settings hang off the user's own corner. */
export const MAIN_NAV: NavItem[] = [
  { to: "/dashboard", label: "nav.today", icon: Sun },
  { to: "/nutrition", label: "nav.nutrition", icon: UtensilsCrossed },
  { to: "/training", label: "nav.training", icon: Dumbbell },
  { to: "/recovery", label: "nav.recovery", icon: HeartPulse },
];
