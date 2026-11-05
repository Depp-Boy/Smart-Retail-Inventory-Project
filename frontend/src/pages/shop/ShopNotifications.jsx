import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Bell, CheckCircle2, AlertTriangle, Truck, Package, XCircle,
  TrendingUp, Check, ExternalLink
} from 'lucide-react';
import { shopService } from '../../services/shopService';
import PageHeader from '../../components/ui/PageHeader';
import Button from '../../components/ui/Button';
import LoadingSpinner from '../../components/ui/LoadingSpinner';
import EmptyState from '../../components/ui/EmptyState';
import { useToast } from '../../context/ToastContext';

const CATEGORY_ICONS = {
  'Low stock': { icon: AlertTriangle, color: 'text-red-500', bg: 'bg-red-50' },
  'Order accepted': { icon: CheckCircle2, color: 'text-blue-500', bg: 'bg-blue-50' },
  'Order rejected': { icon: XCircle, color: 'text-red-500', bg: 'bg-red-50' },
  'Order dispatched': { icon: Truck, color: 'text-indigo-500', bg: 'bg-indigo-50' },
  'Order delivered': { icon: CheckCircle2, color: 'text-green-500', bg: 'bg-green-50' },
  'Forecast alerts': { icon: TrendingUp, color: 'text-purple-500', bg: 'bg-purple-50' },
};

export default function ShopNotifications() {
  const { toast } = useToast();
  const [notifications, setNotifications] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [loading, setLoading] = useState(true);

  const loadNotifications = async () => {
    try {
      setLoading(true);
      const data = await shopService.getNotifications();
      setNotifications(data);
    } catch (err) {
      console.error(err);
      toast.error('Failed to load notifications.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadNotifications();
  }, []);

  const handleMarkRead = async (id) => {
    try {
      const updated = await shopService.markNotificationRead(id);
      setNotifications(updated);
      toast.info('Notification marked as read.');
    } catch (err) {
      toast.error('Failed to mark notification.');
    }
  };

  const handleMarkAllRead = async () => {
    try {
      const updated = await shopService.markAllNotificationsRead();
      setNotifications(updated);
      toast.success('All notifications marked as read.');
    } catch (err) {
      toast.error('Failed to update notifications.');
    }
  };

  const categories = ['All', 'Low stock', 'Order accepted', 'Order rejected', 'Order dispatched', 'Order delivered', 'Forecast alerts'];

  const filtered = notifications.filter((n) =>
    selectedCategory === 'All' ? true : n.category === selectedCategory
  );

  const unreadCount = notifications.filter((n) => !n.read).length;

  return (
    <div className="space-y-6 pb-12 max-w-4xl mx-auto">
      <PageHeader
        title="Notifications Center"
        subtitle="Operational alerts, stock depletion warnings, and restock delivery status."
        breadcrumbs={[{ label: 'Shop', href: '/shop/dashboard' }, { label: 'Notifications' }]}
        action={
          unreadCount > 0 ? (
            <Button
              size="sm"
              variant="secondary"
              icon={Check}
              onClick={handleMarkAllRead}
            >
              Mark all as read ({unreadCount})
            </Button>
          ) : null
        }
      />

      {/* Category Pills */}
      <div className="flex flex-wrap items-center gap-1.5 pb-2">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={[
              'px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors',
              selectedCategory === cat
                ? 'bg-blue-600 text-white'
                : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50',
            ].join(' ')}
          >
            {cat}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="py-24 flex justify-center">
          <LoadingSpinner size="lg" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <EmptyState
            icon={Bell}
            title="No notifications in this category"
            description="You are fully up to date with your inventory alerts."
          />
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((item) => {
            const config = CATEGORY_ICONS[item.category] || { icon: Bell, color: 'text-gray-500', bg: 'bg-gray-50' };
            const Icon = config.icon;

            return (
              <div
                key={item.id}
                className={[
                  'p-4 rounded-xl border transition-all flex flex-col sm:flex-row items-start justify-between gap-3 text-xs',
                  item.read
                    ? 'bg-white border-gray-200 text-gray-600'
                    : 'bg-blue-50/40 border-blue-200 shadow-2xs text-gray-900',
                ].join(' ')}
              >
                <div className="flex items-start gap-3">
                  <div className={['w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0', config.bg, config.color].join(' ')}>
                    <Icon size={18} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-bold text-sm text-gray-900">{item.title}</span>
                      {!item.read && (
                        <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse" />
                      )}
                    </div>
                    <p className="text-gray-600 leading-relaxed max-w-xl">{item.message}</p>
                    <div className="flex items-center gap-3 mt-2 text-[11px] text-gray-400">
                      <span className="font-semibold text-gray-600 bg-gray-100 px-2 py-0.5 rounded">
                        {item.category}
                      </span>
                      <span>{item.timestamp}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 self-end sm:self-center">
                  {item.link && (
                    <Link
                      to={item.link}
                      className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1 px-2.5 py-1.5 rounded-lg hover:bg-blue-50 transition-colors"
                    >
                      View Details <ExternalLink size={12} />
                    </Link>
                  )}
                  {!item.read && (
                    <button
                      onClick={() => handleMarkRead(item.id)}
                      className="text-xs text-gray-400 hover:text-gray-700 p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
                      title="Mark as read"
                    >
                      <Check size={16} />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
