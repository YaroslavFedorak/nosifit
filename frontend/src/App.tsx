import { lazy, Suspense } from "react";
import { Navigate, Outlet, Route, Routes } from "react-router";
import { AppShell } from "./components/layout/AppShell";
import { Skeleton } from "./components/ui/States";
import { bootstrap } from "./lib/bootstrap";

// One chunk per page: a phone only downloads what it opens.
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Training = lazy(() => import("./pages/Training"));
const Nutrition = lazy(() => import("./pages/Nutrition"));
const Recovery = lazy(() => import("./pages/Recovery"));
const Landing = lazy(() => import("./pages/Landing"));
const HowItWorks = lazy(() => import("./pages/HowItWorks"));

function PageFallback() {
  return (
    <div className="mx-auto max-w-5xl space-y-4 px-4 pt-6" aria-busy="true">
      <Skeleton className="h-12 w-2/3" />
      <Skeleton className="h-64" />
      <Skeleton className="h-28" />
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
          <Route path="training" element={<Training />} />
          <Route path="nutrition" element={<Nutrition />} />
          <Route path="recovery" element={<Recovery />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
