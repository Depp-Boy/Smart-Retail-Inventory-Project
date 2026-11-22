import { Link } from 'react-router-dom';
import { Construction, ArrowLeft } from 'lucide-react';

export default function PlaceholderPage({ title = 'Page', description = 'This section is coming in the next development phase.' }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-64 py-16 text-center">
      <div className="p-4 bg-blue-50 rounded-full mb-4">
        <Construction size={32} className="text-blue-400" />
      </div>
      <h2 className="text-lg font-bold text-gray-900 mb-2">{title}</h2>
      <p className="text-sm text-gray-500 max-w-sm mb-6 leading-relaxed">{description}</p>
      <div className="flex items-center gap-2 text-xs text-gray-400 bg-gray-50 px-4 py-2.5 rounded-xl border border-gray-200">
        <span className="w-2 h-2 rounded-full bg-orange-400 animate-pulse" />
        Scheduled for Phase 2 development
      </div>
    </div>
  );
}
