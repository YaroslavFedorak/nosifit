import type { ReactNode } from "react";
import { Link } from "react-router";
import type { Tone } from "../design/tokens";
import { useT } from "../i18n";
import { bootstrap } from "../lib/bootstrap";
import { useTitle } from "../lib/useTitle";
import { PageHeader } from "../ui/Layout";
import { Avatar } from "./Sidebar";

/**
 * One screen of the app: its title, its own actions and, on a phone, the
 * way to the profile (the sidebar carries it on wider screens).
 */
export function Page({
  title,
  subtitle,
  action,
  tone,
  children,
}: {
  title: string;
  subtitle?: ReactNode;
  action?: ReactNode;
  tone?: Tone;
  children: ReactNode;
}) {
  const { t } = useT();
  useTitle(title);
  const name = bootstrap.user?.name ?? "";
  return (
    <div data-tone={tone}>
      <PageHeader
        title={title}
        subtitle={subtitle}
        action={
          <>
            {action}
            <Link to="/profile" aria-label={t("nav.profile")} className="press grid size-tap place-items-center rounded-pill tab:hidden">
              <Avatar name={name} />
            </Link>
          </>
        }
      />
      {children}
    </div>
  );
}
