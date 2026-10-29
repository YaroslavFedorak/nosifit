import { Dumbbell, HeartPulse, LayoutDashboard, UtensilsCrossed, type LucideIcon } from "lucide-react";
import type { TKey } from "../../i18n/en";
import type { Accent } from "../ui/Card";

export interface NavItem {
  to: string;
  label: TKey;
  icon: LucideIcon;
  accent?: Accent;
}

/** The four modules shown in the tab bar and the sidebar. "More" is the fifth tab. */
export const MAIN_NAV: NavItem[] = [
  { to: "/dashboard", label: "nav.dashboard", icon: LayoutDashboard },
  { to: "/training", label: "nav.training", icon: Dumbbell, accent: "training" },
  { to: "/nutrition", label: "nav.nutrition", icon: UtensilsCrossed, accent: "nutrition" },
  { to: "/recovery", label: "nav.recovery", icon: HeartPulse, accent: "recovery" },
];
