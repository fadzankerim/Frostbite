import { createBrowserRouter } from 'react-router';

import { GuestOnly, RequireAuth } from './components/guards';
import { Layout } from './components/Layout';
import { LoginPage, RegisterPage } from './pages/AuthPages';
import { ClubDetailPage, ClubsPage } from './pages/ClubPages';
import { HomePage } from './pages/HomePage';
import { ProfilePage } from './pages/ProfilePage';
import { ErrorPage, ForbiddenPage, NotFoundPage } from './pages/StatusPages';
import { TourDetailPage } from './pages/TourDetailPage';
import { ToursPage } from './pages/ToursPage';

// Rute su relativne na /novo/ (vite.config.ts: base). Stare Django stranice su obični linkovi.
export const router = createBrowserRouter(
  [
    {
      path: '/',
      element: <Layout />,
      errorElement: <ErrorPage />,
      children: [
        { index: true, element: <HomePage /> },
        { path: 'ture', element: <ToursPage /> },
        { path: 'ture/:id', element: <TourDetailPage /> },
        { path: 'drustva', element: <ClubsPage /> },
        { path: 'drustva/:id', element: <ClubDetailPage /> },
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
