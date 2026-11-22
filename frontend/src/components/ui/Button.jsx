import { BUTTON_BASE, BUTTON_SIZES } from '../../utils/designTokens';

const VARIANTS = {
  primary:   'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500 border border-transparent',
  secondary: 'bg-white text-gray-700 hover:bg-gray-50 focus:ring-blue-500 border border-gray-300',
  danger:    'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500 border border-transparent',
  ghost:     'bg-transparent text-gray-600 hover:bg-gray-100 focus:ring-blue-500 border border-transparent',
  link:      'bg-transparent text-blue-600 hover:text-blue-700 focus:ring-blue-500 border border-transparent underline-offset-4 hover:underline p-0',
  success:   'bg-green-600 text-white hover:bg-green-700 focus:ring-green-500 border border-transparent',
  warning:   'bg-orange-500 text-white hover:bg-orange-600 focus:ring-orange-500 border border-transparent',
};

export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  className = '',
  loading = false,
  icon: Icon,
  iconPosition = 'left',
  fullWidth = false,
  ...props
}) {
  return (
    <button
      className={[
        BUTTON_BASE,
        BUTTON_SIZES[size] || BUTTON_SIZES.md,
        VARIANTS[variant] || VARIANTS.primary,
        fullWidth ? 'w-full' : '',
        loading ? 'opacity-70 cursor-not-allowed' : '',
        className,
      ].filter(Boolean).join(' ')}
      disabled={loading || props.disabled}
      {...props}
    >
      {loading && (
        <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      )}
      {!loading && Icon && iconPosition === 'left' && <Icon size={size === 'xs' || size === 'sm' ? 14 : 16} />}
      {children}
      {!loading && Icon && iconPosition === 'right' && <Icon size={size === 'xs' || size === 'sm' ? 14 : 16} />}
    </button>
  );
}
