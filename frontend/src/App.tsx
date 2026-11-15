import { lazy, Suspense } from "react";
import { Navigate, Outlet, Route, Routes } from "react-router";
import { AppShell } from "./app/AppShell";
import { bootstrap } from "./lib/bootstrap";
import { Skeleton } from "./ui/Feedback";

// One chunk per page: a phone only downloads what it opens.
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Nutrition = lazy(() => import("./pages/Nutrition"));
const Training = lazy(() => import("./pages/Training"));
const Recovery = lazy(() => import("./pages/Recovery"));
const Profile = lazy(() => import("./pages/Profile"));
const Settings = lazy(() => import("./pages/Settings"));
const Landing = lazy(() => import("./pages/Landing"));
const HowItWorks = lazy(() => import("./pages/HowItWorks"));

function PageFallback() {
  return (
    <div className="space-y-4 pt-2" aria-busy="true">
      <Skeleton className="h-9 w-1/2 max-w-xs" />
      <Skeleton className="h-40" />
      <Skeleton className="h-24" />
    </div>
  );
}

/** The server already redirects signed-out visitors; this covers a stale tab. */
function RequireUser() {
  return bootstrap.user ? <AppShell /> : <Navigate to="/welcome" replace />;
}

function HowItWorksFrame() {
  return bootstrap.user ? <AppShell /> : <Outlet />;
}

export function App() {
  return (
    <Suspense fallback={<PageFallback />}>
      <Routes>
        <Route index element={<Navigate to={bootstrap.user ? "/dashboard" : "/welcome"} replace />} />
        <Route path="welcome" element={<Landing />} />
        <Route element={<HowItWorksFrame />}>
          <Route path="how-it-works" element={<HowItWorks />} />
        </Route>
        <Route element={<RequireUser />}>
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="nutrition" element={<Nutrition />} />
          <Route path="training" element={<Training />} />
          <Route path="recovery" element={<Recovery />} />
          <Route path="profile" element={<Profile />} />
          <Route path="settings" element={<Settings />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
