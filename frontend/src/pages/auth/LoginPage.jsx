import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Package2, ArrowRight } from 'lucide-react';
import { Input, PasswordInput } from '../../components/ui/Input';
import Button from '../../components/ui/Button';
import { Alert } from '../../components/ui/Notification';
import { useAuth } from '../../context/AuthContext';
import { validateLoginForm } from '../../utils/validators';

const DEMO_ACCOUNTS = [
  { label: 'Shop Owner',        email: 'shop@demo.com',    role: 'shop' },
  { label: 'Warehouse Manager', email: 'manager@demo.com', role: 'warehouse' },
  { label: 'Warehouse Worker',  email: 'worker@demo.com',  role: 'worker' },
];

export default function LoginPage() {
  const navigate = useNavigate();
  const { login, loading } = useAuth();

  const [form, setForm] = useState({ email: '', password: '', remember: false });
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState('');

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((f) => ({ ...f, [name]: type === 'checkbox' ? checked : value }));
    setErrors((err) => ({ ...err, [name]: '' }));
  };

  const redirectByRole = (role) => {
    if (role === 'shop') navigate('/shop/dashboard');
    else if (role === 'warehouse') navigate('/warehouse/dashboard');
    else if (role === 'worker') navigate('/worker/dashboard');
    else navigate('/');
  };

  const handleDemoLogin = async (demo) => {
    setServerError('');
    const result = await login(demo.email, 'demo123', demo.role);
    if (result.success) {
      redirectByRole(result.user.role);
    } else {
      setServerError(result.error || 'Failed to sign in to demo account.');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setServerError('');
    const validationErrors = validateLoginForm(form);
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }
    const result = await login(form.email, form.password);
    if (result.success) {
      redirectByRole(result.user.role);
    } else {
      setServerError(result.error || 'Invalid credentials.');
    }
  };


  return (
    <div className="min-h-screen flex items-center justify-center p-4"
      style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%)' }}>
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-blue-600 rounded-2xl mb-4">
            <Package2 size={24} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">Welcome back</h1>
          <p className="text-slate-400 text-sm mt-1">Sign in to your StockSense account</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-2xl p-8">
          {serverError && (
            <Alert
              variant="error"
              message={serverError}
              className="mb-5"
              onClose={() => setServerError('')}
            />
          )}

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <Input
              label="Email address"
              name="email"
              type="email"
              placeholder="you@example.com"
              value={form.email}
              onChange={handleChange}
              error={errors.email}
              required
              autoComplete="email"
            />
            <PasswordInput
              label="Password"
              id="login-password"
              name="password"
              placeholder="Enter your password"
              value={form.password}
              onChange={handleChange}
              error={errors.password}
              required
              autoComplete="current-password"
            />

            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none">
                <input
                  type="checkbox"
                  name="remember"
                  checked={form.remember}
                  onChange={handleChange}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                Remember me
              </label>
              <Link
                to="/forgot-password"
                className="text-sm text-blue-600 hover:text-blue-700 font-medium transition-colors"
              >
                Forgot password?
              </Link>
            </div>

            <Button type="submit" fullWidth loading={loading} size="lg" icon={ArrowRight} iconPosition="right">
              Sign in
            </Button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm text-gray-500">
              Don&apos;t have an account?{' '}
              <Link to="/register" className="text-blue-600 font-medium hover:text-blue-700 transition-colors">
                Create account
              </Link>
            </p>
          </div>
        </div>

        {/* Demo quick-login */}
        <div className="mt-6">
          <p className="text-center text-xs text-slate-500 mb-3">Quick demo — click to log in instantly</p>
          <div className="grid grid-cols-3 gap-2">
            {DEMO_ACCOUNTS.map((d) => (
              <button
                key={d.role}
                onClick={() => handleDemoLogin(d)}
                disabled={loading}
                className="bg-white/10 hover:bg-white/20 text-white text-xs font-medium px-3 py-2.5 rounded-xl border border-white/20 transition-colors text-center leading-snug"
              >
                {d.label}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-6 text-center">
          <Link to="/" className="text-sm text-slate-400 hover:text-slate-300 transition-colors">
            ← Back to home
          </Link>
        </div>
      </div>
    </div>
  );
}
