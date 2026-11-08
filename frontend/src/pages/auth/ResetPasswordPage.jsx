import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Package2, CheckCircle } from 'lucide-react';
import { PasswordInput } from '../../components/ui/Input';
import Button from '../../components/ui/Button';
import { isStrongPassword } from '../../utils/validators';

export default function ResetPasswordPage() {
  const [form, setForm] = useState({ password: '', confirmPassword: '' });
  const [errors, setErrors] = useState({});
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
    setErrors((err) => ({ ...err, [name]: '' }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const errs = {};
    if (!form.password) errs.password = 'Password is required';
    else if (!isStrongPassword(form.password))
      errs.password = 'Password must be at least 8 characters with uppercase, lowercase, and a number';
    if (!form.confirmPassword) errs.confirmPassword = 'Please confirm your password';
    else if (form.password !== form.confirmPassword) errs.confirmPassword = 'Passwords do not match';
    if (Object.keys(errs).length > 0) { setErrors(errs); return; }
    setLoading(true);
    await new Promise((r) => setTimeout(r, 1000));
    setLoading(false);
    setDone(true);
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4"
      style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%)' }}
    >
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-blue-600 rounded-2xl mb-4">
            <Package2 size={24} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">Reset password</h1>
          <p className="text-slate-400 text-sm mt-1">Enter your new password below</p>
        </div>

        <div className="bg-white rounded-2xl shadow-2xl p-8">
          {done ? (
            <div className="text-center py-4">
              <div className="w-14 h-14 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle size={24} className="text-green-600" />
              </div>
              <h3 className="text-base font-semibold text-gray-900 mb-2">Password updated!</h3>
              <p className="text-sm text-gray-500 mb-6">
                Your password has been successfully reset.
              </p>
              <Link to="/login">
                <Button fullWidth>Go to Login</Button>
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4" noValidate>
              <PasswordInput
                label="New Password"
                id="new-password"
                name="password"
                placeholder="Min 8 characters"
                value={form.password}
                onChange={handleChange}
                error={errors.password}
                required
                autoComplete="new-password"
              />
              <PasswordInput
                label="Confirm New Password"
                id="confirm-new-password"
                name="confirmPassword"
                placeholder="Repeat new password"
                value={form.confirmPassword}
                onChange={handleChange}
                error={errors.confirmPassword}
                required
                autoComplete="new-password"
              />
              <Button type="submit" fullWidth loading={loading} size="lg">
                Reset Password
              </Button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
