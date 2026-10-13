import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './hooks/useAuth';
import { useToast } from './hooks/useToast';
import { Navbar } from './components/layout/Navbar';
import { DashboardPage } from './pages/DashboardPage';
import { EntitiesPage } from './pages/EntitiesPage';
import { RiskGraphPage } from './pages/RiskGraphPage';
import { CasesPage } from './pages/CasesPage';
import { BrandProtectionPage } from './pages/BrandProtectionPage';
import { AuditPage } from './pages/AuditPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

const ToastContainer: React.FC = () => {
  const { toasts, dismiss } = useToast();
  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
      {toasts.map((t) => (
        <div
          key={t.id}
          className="flex items-start justify-between rounded-xl border border-slate-700 bg-slate-900/95 p-3.5 shadow-2xl backdrop-blur-md transition-all"
        >
          <div>
            <h5 className="text-sm font-semibold text-slate-100">{t.title}</h5>
            {t.description && <p className="text-xs text-slate-400 mt-0.5">{t.description}</p>}
          </div>
          <button
            onClick={() => dismiss(t.id)}
            className="text-slate-500 hover:text-slate-300 ml-3 text-xs"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <div className="min-h-screen bg-[#070a12] text-slate-100 flex flex-col font-sans selection:bg-teal-500/20 selection:text-teal-300">
            <Navbar />
            <main className="flex-1 mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8 pt-6">
              <Routes>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/entities" element={<EntitiesPage />} />
                <Route path="/graph" element={<RiskGraphPage />} />
                <Route path="/cases" element={<CasesPage />} />
                <Route path="/brands" element={<BrandProtectionPage />} />
                <Route path="/audit" element={<AuditPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </main>
            <ToastContainer />
          </div>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
};

export default App;

