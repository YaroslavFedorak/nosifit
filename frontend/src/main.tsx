import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import { App } from "./App";
import { I18nProvider } from "./i18n";
import { ApiError } from "./lib/api";
import "./styles.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 20_000,
      // Coming back to the tab refreshes the data, as the classic pages do.
      refetchOnWindowFocus: true,
      retry: (failures, error) => !(error instanceof ApiError && error.status < 500) && failures < 2,
    },
  },
});

const root = document.getElementById("root");
if (!root) throw new Error("#root is missing from the page");

createRoot(root).render(
  <StrictMode>
    <I18nProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter basename="/app">
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </I18nProvider>
  </StrictMode>,
);
