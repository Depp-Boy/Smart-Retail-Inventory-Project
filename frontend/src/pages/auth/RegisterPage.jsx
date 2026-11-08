import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Package2, Store, Warehouse } from 'lucide-react';
import { Input, PasswordInput } from '../../components/ui/Input';
import Button from '../../components/ui/Button';
import { validateRegistrationForm } from '../../utils/validators';

const ACCOUNT_TYPES = [
  {
    value: 'shop',
    label: 'Shop Owner',
    icon: Store,
    desc: 'Manage retail inventory & place replenishment orders',
  },
  {
    value: 'warehouse',
    label: 'Warehouse Manager',
    icon: Warehouse,
    desc: 'Manage warehouse stock & fulfill shop requests',
  },
];

export default function RegisterPage() {
  const [form, setForm] = useState({
    fullName: '', email: '', phone: '', password: '', confirmPassword: '',
    accountType: '',
    shopName: '', shopAddress: '', shopLocation: '',
    warehouseName: '', warehouseAddress: '', warehouseLocation: '',
  });
  const [errors, setErrors] = useState({});
  const [submitted, setSubmitted] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
    setErrors((err) => ({ ...err, [name]: '' }));
  };

  const selectAccountType = (type) => {
    setForm((f) => ({ ...f, accountType: type }));
    setErrors((err) => ({ ...err, accountType: '' }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const errs = validateRegistrationForm(form);
    if (Object.keys(errs).length > 0) {
      setErrors(errs);
      // Scroll to first error
      const firstError = document.querySelector('[data-error="true"]');
      firstError?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div
        className="min-h-screen flex items-center justify-center p-4"
        style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%)' }}
      >
        <div className="bg-white rounded-2xl p-10 text-center max-w-md w-full shadow-2xl">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Registration submitted!</h2>
          <p className="text-sm text-gray-500 mb-6 leading-relaxed">
            Thank you for registering. In the live system your account would be verified and
            activated. This is a frontend-only demo — backend integration comes in the next phase.
          </p>
          <Link to="/login">
            <Button fullWidth>Go to Login</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4 py-10"
      style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%)' }}
    >
      <div className="w-full max-w-lg">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-blue-600 rounded-2xl mb-4">
            <Package2 size={24} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">Create your account</h1>
          <p className="text-slate-400 text-sm mt-1">Join StockSense and manage your inventory smarter</p>
        </div>

        <div className="bg-white rounded-2xl shadow-2xl p-8">
          <form onSubmit={handleSubmit} className="space-y-6" noValidate>

            {/* Personal Info */}
            <section>
              <h3 className="text-sm font-semibold text-gray-700 mb-3 pb-2 border-b border-gray-100">
                Personal Information
              </h3>
              <div className="space-y-4">
                <Input
                  label="Full Name" name="fullName" placeholder="John Doe"
                  value={form.fullName} onChange={handleChange} error={errors.fullName} required
                />
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Input
                    label="Email" name="email" type="email" placeholder="you@example.com"
                    value={form.email} onChange={handleChange} error={errors.email} required
                  />
                  <Input
                    label="Phone Number" name="phone" type="tel" placeholder="+91 98765 43210"
                    value={form.phone} onChange={handleChange} error={errors.phone} required
                  />
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <PasswordInput
                    label="Password" id="reg-password" name="password" placeholder="Min 8 characters"
                    value={form.password} onChange={handleChange} error={errors.password} required
                  />
                  <PasswordInput
                    label="Confirm Password" id="reg-confirm" name="confirmPassword" placeholder="Repeat password"
                    value={form.confirmPassword} onChange={handleChange} error={errors.confirmPassword} required
                  />
                </div>
              </div>
            </section>

            {/* Account Type */}
            <section>
              <h3 className="text-sm font-semibold text-gray-700 mb-1 pb-2 border-b border-gray-100">
                Account Type
              </h3>
              <p className="text-xs text-gray-500 mb-3">
                Warehouse workers are added by their warehouse manager — they cannot self-register.
              </p>
              <div className="grid grid-cols-2 gap-3" data-error={!!errors.accountType}>
                {ACCOUNT_TYPES.map((type) => {
                  const Icon = type.icon;
                  const selected = form.accountType === type.value;
                  return (
                    <button
                      key={type.value}
                      type="button"
                      onClick={() => selectAccountType(type.value)}
                      className={[
                        'p-4 rounded-xl border-2 text-left transition-all',
                        selected
                          ? 'border-blue-600 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50',
                      ].join(' ')}
                    >
                      <Icon
                        size={20}
                        className={['mb-2', selected ? 'text-blue-600' : 'text-gray-400'].join(' ')}
                      />
                      <p className={['text-sm font-semibold', selected ? 'text-blue-700' : 'text-gray-700'].join(' ')}>
                        {type.label}
                      </p>
                      <p className="text-xs text-gray-500 mt-1 leading-relaxed">{type.desc}</p>
                    </button>
                  );
                })}
              </div>
              {errors.accountType && (
                <p className="text-xs text-red-600 mt-1">{errors.accountType}</p>
              )}
            </section>

            {/* Shop fields */}
            {form.accountType === 'shop' && (
              <section>
                <h3 className="text-sm font-semibold text-gray-700 mb-3 pb-2 border-b border-gray-100">
                  Shop Details
                </h3>
                <div className="space-y-4">
                  <Input
                    label="Shop Name" name="shopName" placeholder="My Retail Store"
                    value={form.shopName} onChange={handleChange} error={errors.shopName} required
                  />
                  <Input
                    label="Shop Address" name="shopAddress" placeholder="123 Main Street, City"
                    value={form.shopAddress} onChange={handleChange} error={errors.shopAddress} required
                  />
                  <Input
                    label="Location / City" name="shopLocation" placeholder="Bangalore, Karnataka"
                    value={form.shopLocation} onChange={handleChange}
                  />
                </div>
              </section>
            )}

            {/* Warehouse fields */}
            {form.accountType === 'warehouse' && (
              <section>
                <h3 className="text-sm font-semibold text-gray-700 mb-3 pb-2 border-b border-gray-100">
                  Warehouse Details
                </h3>
                <div className="space-y-4">
                  <Input
                    label="Warehouse Name" name="warehouseName" placeholder="Central Warehouse"
                    value={form.warehouseName} onChange={handleChange} error={errors.warehouseName} required
                  />
                  <Input
                    label="Warehouse Address" name="warehouseAddress" placeholder="Industrial Area, Sector 5"
                    value={form.warehouseAddress} onChange={handleChange} error={errors.warehouseAddress} required
                  />
                  <Input
                    label="Location / City" name="warehouseLocation" placeholder="Bangalore, Karnataka"
                    value={form.warehouseLocation} onChange={handleChange}
                  />
                </div>
              </section>
            )}

            <Button type="submit" fullWidth size="lg">Create Account</Button>
          </form>

          <div className="mt-5 text-center">
            <p className="text-sm text-gray-500">
              Already have an account?{' '}
              <Link to="/login" className="text-blue-600 font-medium hover:text-blue-700 transition-colors">
                Sign in
              </Link>
            </p>
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
