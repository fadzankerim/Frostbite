import { createBrowserRouter } from 'react-router';

import { GuestOnly, RequireAuth } from './components/guards';
import { Layout } from './components/Layout';
import { LoginPage, RegisterPage } from './pages/AuthPages';
import { HomePage } from './pages/HomePage';
import { ProfilePage } from './pages/ProfilePage';
import { ErrorPage, ForbiddenPage, NotFoundPage } from './pages/StatusPages';

// Rute su relativne na /novo/ (vite.config.ts: base). Stare Django stranice su obični linkovi.
export const router = createBrowserRouter(
  [
    {
      path: '/',
      element: <Layout />,
      errorElement: <ErrorPage />,
      children: [
        { index: true, element: <HomePage /> },
        { path: 'prijava', element: <GuestOnly><LoginPage /></GuestOnly> },
        { path: 'registracija', element: <GuestOnly><RegisterPage /></GuestOnly> },
        { path: 'profil', element: <RequireAuth><ProfilePage /></RequireAuth> },
        { path: 'zabranjeno', element: <ForbiddenPage /> },
        { path: '*', element: <NotFoundPage /> },
      ],
    },
  ],
  { basename: import.meta.env.BASE_URL.replace(/\/$/, '') },
);
