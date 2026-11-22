// Central design token exports for consistent styling across components

export const BADGE_VARIANTS = {
  success:  'bg-green-100 text-green-700 border border-green-200',
  warning:  'bg-orange-100 text-orange-700 border border-orange-200',
  danger:   'bg-red-100 text-red-700 border border-red-200',
  info:     'bg-blue-100 text-blue-700 border border-blue-200',
  neutral:  'bg-gray-100 text-gray-600 border border-gray-200',
  purple:   'bg-purple-100 text-purple-700 border border-purple-200',
};

export const INPUT_BASE =
  'w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 placeholder-gray-400 ' +
  'transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ' +
  'disabled:bg-gray-50 disabled:text-gray-400 disabled:cursor-not-allowed';

export const BUTTON_BASE =
  'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed';

export const BUTTON_SIZES = {
  xs:  'px-2.5 py-1.5 text-xs',
  sm:  'px-3 py-2 text-sm',
  md:  'px-4 py-2.5 text-sm',
  lg:  'px-5 py-3 text-base',
  xl:  'px-6 py-3.5 text-base',
};
