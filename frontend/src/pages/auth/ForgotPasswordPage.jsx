import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Package2, Mail, ArrowLeft } from 'lucide-react';
import { Input } from '../../components/ui/Input';
import Button from '../../components/ui/Button';
import { isValidEmail } from '../../utils/validators';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!email.trim()) { setError('Email is required'); return; }
    if (!isValidEmail(email)) { setError('Please enter a valid email address'); return; }
    setLoading(true);
    await new Promise((r) => setTimeout(r, 1000)); // simulate API call
    setLoading(false);
    setSent(true);
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
          <h1 className="text-2xl font-bold text-white">Forgot password</h1>
          <p className="text-slate-400 text-sm mt-1">{"We'll send you a reset link"}</p>
        </div>

        <div className="bg-white rounded-2xl shadow-2xl p-8">
          {sent ? (
            <div className="text-center py-4">
              <div className="w-14 h-14 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Mail size={24} className="text-green-600" />
              </div>
              <h3 className="text-base font-semibold text-gray-900 mb-2">Check your email</h3>
              <p className="text-sm text-gray-500 mb-6 leading-relaxed">
                In the live system, a password reset link would be sent to{' '}
                <strong className="text-gray-700">{email}</strong>. This is a frontend demo.
              </p>
              <Link to="/login">
                <Button fullWidth variant="secondary">Back to Login</Button>
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4" noValidate>
              <p className="text-sm text-gray-600 leading-relaxed">
                Enter your registered email address and we&apos;ll send you a link to reset your password.
              </p>
              <Input
                label="Email address"
                name="email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => { setEmail(e.target.value); setError(''); }}
                error={error}
                required
                autoComplete="email"
              />
              <Button type="submit" fullWidth loading={loading} size="lg">
                Send reset link
              </Button>
              <Link
                to="/login"
                className="flex items-center justify-center gap-2 text-sm text-gray-500 hover:text-gray-700 transition-colors mt-2"
              >
                <ArrowLeft size={14} /> Back to login
              </Link>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
