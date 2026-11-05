import { useState, useEffect } from "react";
import { Bell, CheckCheck, Package, Truck, AlertTriangle, Info, RefreshCw } from "lucide-react";
import { warehouseService } from "../../services/warehouseService";
import { useToast } from "../../context/ToastContext";
import PageHeader from "../../components/ui/PageHeader";
import { Card } from "../../components/ui/Card";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";

const CATEGORY_CONFIG = {
  low_stock: { icon: AlertTriangle, color: "text-orange-600", bg: "bg-orange-50", label: "Low Stock" },
  out_of_stock: { icon: AlertTriangle, color: "text-red-600", bg: "bg-red-50", label: "Out of Stock" },
  order: { icon: Package, color: "text-blue-600", bg: "bg-blue-50", label: "Order" },
  dispatch: { icon: Truck, color: "text-purple-600", bg: "bg-purple-50", label: "Dispatch" },
  info: { icon: Info, color: "text-gray-600", bg: "bg-gray-50", label: "Info" },
  system: { icon: Bell, color: "text-gray-600", bg: "bg-gray-50", label: "System" },
};

const CATEGORIES = ["All", "low_stock", "out_of_stock", "order", "dispatch", "info", "system"];

function NotificationCard({ notif, onMarkRead }) {
  const cfg = CATEGORY_CONFIG[notif.category] || CATEGORY_CONFIG.info;
  const Icon = cfg.icon;

  return (
    <div className={`flex items-start gap-3 p-4 rounded-xl border transition-all ${notif.read ? "bg-white border-gray-100" : "bg-blue-50/50 border-blue-200"}`}>
      <div className={`p-2 rounded-lg shrink-0 ${cfg.bg}`}>
        <Icon className={`w-4 h-4 ${cfg.color}`} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className={`text-sm font-medium ${notif.read ? "text-gray-700" : "text-gray-900"}`}>{notif.title}</p>
            <p className="text-sm text-gray-600 mt-0.5">{notif.message}</p>
            <p className="text-xs text-gray-400 mt-1">{notif.timestamp}</p>
          </div>
          {!notif.read && (
            <div className="flex items-center gap-2 shrink-0">
              <div className="w-2 h-2 rounded-full bg-blue-500" />
              <button onClick={() => onMarkRead(notif.id)} className="text-xs text-blue-600 hover:text-blue-800 font-medium whitespace-nowrap">Mark read</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function WarehouseNotifications() {
  const { toast } = useToast();
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [categoryFilter, setCategoryFilter] = useState("All");

  const load = () => {
    setLoading(true);
    warehouseService.getNotifications().then(setNotifications).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const filtered = categoryFilter === "All" ? notifications : notifications.filter((n) => n.category === categoryFilter);
  const unreadCount = notifications.filter((n) => !n.read).length;

  const handleMarkRead = async (id) => {
    const updated = await warehouseService.markNotificationRead(id);
    setNotifications(updated);
  };

  const handleMarkAllRead = async () => {
    const allRead = notifications.map((n) => ({ ...n, read: true }));
    // Use warehouseService to mark each one
    for (const n of notifications.filter((n) => !n.read)) {
      await warehouseService.markNotificationRead(n.id);
    }
    setNotifications(allRead);
    toast.success("All notifications marked as read.");
  };

  return (
    <div className="p-4 md:p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <PageHeader
          title="Notifications"
          subtitle="View all system and operational notifications for your warehouse."
          badge={unreadCount > 0 ? { label: `${unreadCount} unread`, variant: "warning" } : null}
        />
        <div className="flex gap-3">
          <Button variant="ghost" size="sm" icon={RefreshCw} onClick={load}>Refresh</Button>
          {unreadCount > 0 && (
            <Button variant="ghost" size="sm" icon={CheckCheck} onClick={handleMarkAllRead}>Mark All Read</Button>
          )}
        </div>
      </div>

      {/* Category filter pills */}
      <div className="flex flex-wrap gap-2">
        {CATEGORIES.map((cat) => {
          const cfg = CATEGORY_CONFIG[cat];
          const label = cfg ? cfg.label : "All";
          const count = cat === "All" ? notifications.length : notifications.filter((n) => n.category === cat).length;
          return (
            <button key={cat} onClick={() => setCategoryFilter(cat)}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${categoryFilter === cat ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>
              {label} {count > 0 && <span className="ml-1 text-xs opacity-75">({count})</span>}
            </button>
          );
        })}
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1,2,3].map((i) => <div key={i} className="h-20 bg-gray-100 rounded-xl animate-pulse" />)}
        </div>
      ) : filtered.length === 0 ? (
        <Card className="p-16 text-center">
          <Bell className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No notifications in this category.</p>
        </Card>
      ) : (
        <div className="space-y-2">
          {filtered.map((n) => (
            <NotificationCard key={n.id} notif={n} onMarkRead={handleMarkRead} />
          ))}
        </div>
      )}
    </div>
  );
}
