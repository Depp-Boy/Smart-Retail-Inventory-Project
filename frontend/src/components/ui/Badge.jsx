import { BADGE_VARIANTS } from '../../utils/designTokens';

export default function Badge({ children, variant = 'neutral', className = '', dot = false }) {
  const dotColors = {
    success: 'bg-green-500',
    warning: 'bg-orange-500',
    danger:  'bg-red-500',
    info:    'bg-blue-500',
    neutral: 'bg-gray-400',
    purple:  'bg-purple-500',
  };

  return (
    <span
      className={[
        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
        BADGE_VARIANTS[variant] || BADGE_VARIANTS.neutral,
        className,
      ].filter(Boolean).join(' ')}
    >
      {dot && (
        <span className={['h-1.5 w-1.5 rounded-full flex-shrink-0', dotColors[variant] || 'bg-gray-400'].join(' ')} />
      )}
      {children}
    </span>
  );
}
