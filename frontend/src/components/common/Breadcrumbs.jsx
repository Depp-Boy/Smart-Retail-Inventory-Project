import { ChevronRight, Home } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function Breadcrumbs({ items = [], className = '' }) {
  if (!items || items.length === 0) return null;

  return (
    <nav className={['flex items-center space-x-2 text-xs text-gray-500', className].filter(Boolean).join(' ')} aria-label="Breadcrumb">
      <Link to="/" className="hover:text-blue-600 transition-colors flex items-center">
        <Home size={13} className="mr-1 text-gray-400" />
        <span className="sr-only">Home</span>
      </Link>
      {items.map((item, index) => {
        const isLast = index === items.length - 1;
        return (
          <div key={index} className="flex items-center space-x-2">
            <ChevronRight size={12} className="text-gray-400 flex-shrink-0" />
            {isLast || !item.href ? (
              <span className={['font-medium', isLast ? 'text-gray-800' : 'text-gray-500'].join(' ')}>
                {item.label}
              </span>
            ) : (
              <Link to={item.href} className="hover:text-blue-600 transition-colors">
                {item.label}
              </Link>
            )}
          </div>
        );
      })}
    </nav>
  );
}
