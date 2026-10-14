import React, { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Eye, EyeOff, Shield, Search, Radar, Zap, AlertCircle, ArrowRight } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { Button } from '../components/ui/button';
import { Input, Field } from '../components/ui/input';
import { useToast } from '../components/ui/toast';
import { ApiError } from '../services/apiClient';
import { cn } from '../lib/utils';

const FEATURES = [
  {
    icon: <Search className="h-4 w-4" />,
    title: 'Detect',
    sub: 'Investigate. Protect.',
    color: 'from-brand-500 to-brand-600',
  },
  {
    icon: <Radar className="h-4 w-4" />,
    title: 'Monitor',
    sub: 'Digital assets & threats.',
    color: 'from-cyanx-500 to-cyanx-600',
  },
  {
    icon: <Zap className="h-4 w-4" />,
    title: 'Respond',
    sub: 'Turn insights into action.',
    color: 'from-violet-500 to-violet-600',
  },
];

const BrandPanel: React.FC = () => (
  <div className="relative hidden overflow-hidden bg-hero-gradient lg:flex lg:w-[46%] xl:w-[42%]">
    {/* soft decorative shapes */}
    <div className="absolute -left-24 -top-24 h-96 w-96 rounded-full bg-white/10 blur-2xl" />
    <div className="absolute -bottom-32 -right-24 h-[28rem] w-[28rem] rounded-full bg-cyanx-500/20 blur-3xl" />
    <svg
      className="absolute inset-0 h-full w-full opacity-[0.14]"
      viewBox="0 0 800 900"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="lg1" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#ffffff" stopOpacity="0.7" />
          <stop offset="100%" stopColor="#ffffff" stopOpacity="0" />
        </linearGradient>
      </defs>
      {/* abstract mountain / network landscape */}
      <path d="M0 640 L160 470 L290 590 L430 400 L560 540 L700 380 L800 500 L800 900 L0 900 Z" fill="url(#lg1)" opacity="0.35" />
      <path d="M0 720 L140 600 L300 700 L470 560 L640 690 L800 580 L800 900 L0 900 Z" fill="url(#lg1)" opacity="0.5" />
      {[
        [140, 470], [290, 590], [430, 400], [560, 540], [700, 380],
      ].map(([x, y], i) => (
        <g key={i}>
          <circle cx={x} cy={y} r="6" fill="#fff" opacity="0.9" />
          <circle cx={x} cy={y} r="16" fill="#fff" opacity="0.18" />
        </g>
      ))}
      <path d="M140 470 L290 590 L430 400 L560 540 L700 380" stroke="#fff" strokeOpacity="0.4" strokeWidth="1.5" fill="none" />
    </svg>

    <div className="relative z-10 flex w-full flex-col justify-between p-10 xl:p-14">
      <div className="flex items-center gap-3">
        <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/15 backdrop-blur">
          <Shield className="h-6 w-6 text-white" />
        </span>
        <div className="leading-tight">
          <p className="text-lg font-extrabold tracking-[0.16em] text-white">NIMBUS</p>
          <p className="-mt-0.5 text-[11px] font-bold uppercase tracking-[0.34em] text-white/70">Ninjas</p>
        </div>
      </div>

      <div>
        <h1 className="max-w-sm text-3xl font-extrabold leading-tight tracking-tight text-white xl:text-[34px]">
          Make digital trust visible, explainable, and actionable.
        </h1>
        <div className="mt-8 space-y-3.5">
          {FEATURES.map((f) => (
            <div key={f.title} className="flex items-center gap-3.5">
              <span className={cn('flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br text-white shadow-lg', f.color)}>
                {f.icon}
              </span>
              <div>
                <p className="text-[15px] font-bold text-white">{f.title}</p>
                <p className="text-[13px] text-white/70">{f.sub}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <p className="text-[12px] font-semibold uppercase tracking-[0.22em] text-white/60">
        Stronger Intelligence &nbsp;•&nbsp; Safer Tomorrow
      </p>
    </div>
  </div>
);

export const LoginPage: React.FC = () => {
  const { login, isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { toast } = useToast();

  const [mode, setMode] = useState<'signin' | 'signup'>('signin');
  const [email, setEmail] = useState(() => localStorage.getItem('nimbus_remember_email') || '');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [remember, setRemember] = useState(() => !!localStorage.getItem('nimbus_remember_email'));
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate((location.state as any)?.from || '/dashboard', { replace: true });
    }
  }, [isLoading, isAuthenticated, navigate, location]);

  const validate = (): boolean => {
    const errs: Record<string, string> = {};
    if (!email.trim()) errs.email = 'Email is required';
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) errs.email = 'Enter a valid email address';
    if (!password) errs.password = 'Password is required';
    else if (mode === 'signup' && password.length < 8) errs.password = 'Password must be at least 8 characters';
    if (mode === 'signup' && !fullName.trim()) errs.fullName = 'Name is required';
    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!validate()) return;
    setSubmitting(true);
    try {
      if (mode === 'signin') {
        await login(email.trim(), password);
        if (remember) localStorage.setItem('nimbus_remember_email', email.trim());
        else localStorage.removeItem('nimbus_remember_email');
        toast.success('Welcome back', 'Signed in to Nimbus Ninjas.');
        navigate((location.state as any)?.from || '/dashboard', { replace: true });
      } else {
        const { authService } = await import('../services/authService');
        await authService.register({ email: email.trim(), password, full_name: fullName.trim() });
        await login(email.trim(), password);
        toast.success('Account created', 'Your workspace account is ready.');
        navigate('/dashboard', { replace: true });
      }
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.message
          : 'Could not sign in. Check your connection and try again.';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-bg">
      <BrandPanel />
      <div className="flex w-full items-center justify-center px-5 py-10 lg:w-[54%] xl:w-[58%]">
        <div className="w-full max-w-[400px]">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-gradient text-white">
              <Shield className="h-5 w-5" />
            </span>
            <p className="text-base font-extrabold tracking-[0.14em] text-ink">NIMBUS NINJAS</p>
          </div>

          <h2 className="text-2xl font-extrabold tracking-tight text-ink">
            {mode === 'signin' ? 'Welcome back' : 'Create your account'}
          </h2>
          <p className="mt-1.5 text-sm text-muted">
            {mode === 'signin'
              ? 'Sign in to your Nimbus Ninjas account'
              : 'Start monitoring your digital surface in minutes'}
          </p>

          {error && (
            <div className="mt-5 flex items-start gap-2.5 rounded-xl border border-danger-100 bg-danger-100/60 px-3.5 py-3">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-danger" />
              <p className="text-[13px] font-medium leading-snug text-danger-600">{error}</p>
            </div>
          )}

          <form onSubmit={onSubmit} className="mt-6 space-y-4" noValidate>
            {mode === 'signup' && (
              <Field label="Full name" error={fieldErrors.fullName} required>
                <Input
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Alex Vance"
                  autoComplete="name"
                />
              </Field>
            )}
            <Field label="Email address" error={fieldErrors.email} required>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
              />
            </Field>
            <Field label="Password" error={fieldErrors.password} required>
              <div className="relative">
                <Input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  autoComplete={mode === 'signin' ? 'current-password' : 'new-password'}
                  className="pr-11"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  className="absolute right-3 top-1/2 -translate-y-1/2 rounded p-1 text-faint transition-colors hover:text-ink"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </Field>

            <div className="flex items-center justify-between pt-1">
              <label className="flex cursor-pointer items-center gap-2.5">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={(e) => setRemember(e.target.checked)}
                  className="h-4 w-4 rounded border-line accent-[#4778F5]"
                />
                <span className="text-[13px] font-medium text-ink-700">Remember me</span>
              </label>
              {mode === 'signin' && (
                <Link to="/forgot-password" className="text-[13px] font-semibold text-brand-600 hover:text-brand-700">
                  Forgot password?
                </Link>
              )}
            </div>

            <Button type="submit" size="lg" loading={submitting} className="w-full">
              {mode === 'signin' ? 'Sign In' : 'Create Account'}
              {!submitting && <ArrowRight className="ml-1 h-4 w-4" />}
            </Button>
          </form>

          <p className="mt-6 text-center text-[13px] text-muted">
            {mode === 'signin' ? "Don't have an account? " : 'Already have an account? '}
            <button
              onClick={() => {
                setMode(mode === 'signin' ? 'signup' : 'signin');
                setError(null);
                setFieldErrors({});
              }}
              className="font-semibold text-brand-600 hover:text-brand-700"
            >
              {mode === 'signin' ? 'Create one' : 'Sign in'}
            </button>
          </p>

          <div className="mt-8 rounded-xl border border-line bg-surface p-3.5">
            <p className="text-[11px] font-bold uppercase tracking-wider text-faint">Demo accounts</p>
            <p className="mt-1.5 text-[12px] leading-relaxed text-muted">
              <code className="rounded bg-line-soft px-1.5 py-0.5 font-semibold text-ink-700">admin@nimbus.example</code>{' '}
              / <code className="rounded bg-line-soft px-1.5 py-0.5 font-semibold text-ink-700">ChangeMe-Admin-123</code>
              <br />
              Investigators:{' '}
              <code className="rounded bg-line-soft px-1.5 py-0.5 font-semibold text-ink-700">investigator@nimbus.example</code>{' '}
              / <code className="rounded bg-line-soft px-1.5 py-0.5 font-semibold text-ink-700">Demo-Passw0rd!</code>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
