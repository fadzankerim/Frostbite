import '@fontsource-variable/geist';
import '@fontsource-variable/geist-mono';
import './styles/tokens.css';
import './styles/global.css';

import { MutationCache, QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router';

import { MY_BADGES_KEY } from './api/badges';
import { ApiError } from './api/client';
import { router } from './router';

const queryClient: QueryClient = new QueryClient({
  // svaka uspješna radnja može donijeti bedž (dodjeljuje ga server), pa se vlastiti bedževi osvježe
  mutationCache: new MutationCache({
    onSuccess: (_data, _vars, _ctx, mutation) => {
      if (!mutation.meta?.skipBadgeRefresh) void queryClient.invalidateQueries({ queryKey: MY_BADGES_KEY });
    },
  }),
  defaultOptions: {
    queries: {
      // ponovni pokušaj samo za mrežne/serverske greške, ne za 4xx (npr. 403 ostaje 403)
      retry: (count, err) => count < 2 && !(err instanceof ApiError && err.status >= 400 && err.status < 500),
      refetchOnWindowFocus: false,
    },
    mutations: { retry: false },
  },
});

const root = document.getElementById('root');
if (!root) throw new Error('Nedostaje #root');

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
);
