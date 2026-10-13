import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  ShieldAlert,
  LayoutDashboard,
  Shield,
  Network,
  Briefcase,
  History,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  UserCheck,
} from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { DEMO_ACCOUNTS } from '../../lib/constants';
import { mockStore } from '../../mocks/mockStore';
import { Button } from '../ui/button';
import { UserRole } from '../../types';

export const Navbar: React.FC = () => {
  const { user, role, isBackendConnected, switchRole, activeBrand } = useAuth();
  const navigate = useNavigate();

  const handleResetData = () => {
    if (window.confirm('Reset demo data to clean initial state?')) {
      mockStore.resetToDefaults();
      window.location.reload();
    }
  };

  const navItems = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/entities', label: 'Surface & Threats', icon: ShieldAlert },
    { to: '/graph', label: 'Risk Graph', icon: Network },
    { to: '/cases', label: 'Cases', icon: Briefcase },
    { to: '/brands', label: 'Brand Protection', icon: Shield },
    { to: '/audit', label: 'Audit Trail', icon: History },
  ];

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800 bg-[#070a12]/90 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Brand & Logo */}
        <div className="flex items-center gap-6">
          <NavLink to="/" className="flex items-center gap-3 group">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-teal-500 to-cyan-400 p-2 shadow-lg shadow-teal-500/20 group-hover:shadow-teal-500/40 transition-all">
              <ShieldAlert className="h-6 w-6 text-slate-950" />
            </div>
            <div>
              <span className="text-base font-bold tracking-tight text-white flex items-center gap-1.5">
                Nimbus Ninjas
                <span className="text-[10px] font-mono font-medium uppercase px-1.5 py-0.5 rounded bg-teal-500/20 text-teal-300 border border-teal-500/30">
                  DRP
                </span>
              </span>
              <span className="text-[11px] text-slate-400 block -mt-0.5">
                Digital Risk Protection
              </span>
            </div>
          </NavLink>

          {/* Navigation links */}
          <nav className="hidden md:flex items-center space-x-1">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-slate-800 text-teal-400 shadow-sm'
                      : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'
                  }`
                }
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>

        {/* Right Section: Status, Brand, Role */}
        <div className="flex items-center gap-3">
          {/* Backend Connection Indicator */}
          <div
            className={`hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono border ${
              isBackendConnected
                ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800/60'
                : 'bg-amber-950/60 text-amber-300 border-amber-800/60'
            }`}
            title={
              isBackendConnected
                ? 'Connected to live FastAPI backend'
                : 'Using synthetic mock demo data store (Backend offline)'
            }
          >
            {isBackendConnected ? (
              <>
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 animate-pulse" />
                <span>Live API</span>
              </>
            ) : (
              <>
                <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
                <span>Mock Mode</span>
              </>
            )}
          </div>

          {/* Monitored Brand Pill */}
          <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300">
            <span className="text-slate-500">Brand:</span>
            <span className="font-semibold text-teal-400">{activeBrand?.name || 'AcmeBank'}</span>
          </div>

          {/* Role Switcher */}
          <div className="flex items-center gap-2 bg-slate-900/90 border border-slate-800 rounded-lg p-1">
            <UserCheck className="h-4 w-4 text-slate-400 ml-1.5" />
            <select
              value={role}
              onChange={(e) => switchRole(e.target.value as UserRole)}
              className="bg-transparent text-xs font-medium text-slate-200 outline-none cursor-pointer py-1 pr-2"
              title="Switch demo user role"
            >
              {DEMO_ACCOUNTS.map((acc) => (
                <option key={acc.role} value={acc.role} className="bg-slate-900 text-slate-200">
                  {acc.label} ({acc.role})
                </option>
              ))}
            </select>
          </div>

          {/* Reset Demo button */}
          <Button
            variant="ghost"
            size="icon"
            onClick={handleResetData}
            title="Reset synthetic demo data"
            className="text-slate-400 hover:text-white hover:bg-slate-800 h-8 w-8"
          >
            <RotateCcw className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </header>
  );
};

