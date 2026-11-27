import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import { App } from "./App";
import { prefetchPage } from "./api/prefetch";
import { I18nProvider, loadDictionary } from "./i18n";
import { ApiError } from "./lib/api";
import { bootstrap } from "./lib/bootstrap";
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

// The page's data goes out now, not after the first render (api/prefetch.ts).
prefetchPage(queryClient, window.location);

// The page's language arrives as its own small file (preloaded by the server
// together with the bundle), so the first render already has its words.
void loadDictionary(bootstrap.locale).then((dictionary) =>
  createRoot(root).render(
    <StrictMode>
      <I18nProvider dictionary={dictionary}>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter basename="/app">
            <App />
          </BrowserRouter>
        </QueryClientProvider>
      </I18nProvider>
    </StrictMode>,
  ),
);
