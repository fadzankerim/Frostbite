import { createBrowserRouter } from 'react-router';

import { GuestOnly, RequireAuth, RequireHiker, RequireRole } from './components/guards';
import { Layout } from './components/Layout';
import { LoginPage, RegisterPage } from './pages/AuthPages';
import { ClubDetailPage, ClubsPage } from './pages/ClubPages';
import { GuideDashboardPage, GuideTourPage } from './pages/GuidePages';
import {
  ManageDashboardTab, ManageGuidesTab, ManageIndexPage, ManageLayout, ManageMembersTab, ManageProfileTab,
  ManageTourCreate, ManageTourDetail, ManageTourEdit, ManageToursTab,
} from './pages/ManagePages';
import { SystemAuditTab, SystemClubsTab, SystemDashboardTab, SystemLayout, SystemUsersTab } from './pages/SystemPages';
import { MyMembershipsPage, MyRegistrationsPage, SelectionPage } from './pages/HikerPages';
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
        { path: 'odabir', element: <SelectionPage /> },
        { path: 'moje-prijave', element: <RequireHiker><MyRegistrationsPage /></RequireHiker> },
        { path: 'moja-clanstva', element: <RequireHiker><MyMembershipsPage /></RequireHiker> },
        { path: 'vodic', element: <RequireRole role="guide"><GuideDashboardPage /></RequireRole> },
        { path: 'vodic/ture/:id', element: <RequireRole role="guide"><GuideTourPage /></RequireRole> },
        { path: 'upravljanje', element: <RequireRole role="clubAdmin"><ManageIndexPage /></RequireRole> },
        {
          path: 'upravljanje/:clubId',
          element: <RequireRole role="clubAdmin"><ManageLayout /></RequireRole>,
          children: [
            { index: true, element: <ManageDashboardTab /> },
            { path: 'ture', element: <ManageToursTab /> },
            { path: 'ture/nova', element: <ManageTourCreate /> },
            { path: 'ture/:tourId', element: <ManageTourDetail /> },
            { path: 'ture/:tourId/uredi', element: <ManageTourEdit /> },
            { path: 'vodici', element: <ManageGuidesTab /> },
            { path: 'clanovi', element: <ManageMembersTab /> },
            { path: 'profil', element: <ManageProfileTab /> },
          ],
        },
        {
          path: 'sistem',
          element: <RequireRole role="systemAdmin"><SystemLayout /></RequireRole>,
          children: [
            { index: true, element: <SystemDashboardTab /> },
            { path: 'drustva', element: <SystemClubsTab /> },
            { path: 'korisnici', element: <SystemUsersTab /> },
            { path: 'evidencija', element: <SystemAuditTab /> },
          ],
        },
        { path: 'zabranjeno', element: <ForbiddenPage /> },
        { path: '*', element: <NotFoundPage /> },
      ],
    },
  ],
  { basename: import.meta.env.BASE_URL.replace(/\/$/, '') },
);
