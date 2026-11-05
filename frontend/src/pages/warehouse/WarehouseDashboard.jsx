import { useState, useEffect } from "react";
import { Package, BarChart2, TrendingUp, AlertTriangle, Truck, Users, RefreshCw } from "lucide-react";
import { warehouseService } from "../../services/warehouseService";
import { useToast } from "../../context/ToastContext";
import PageHeader from "../../components/ui/PageHeader";
import { Card, StatCard } from "../../components/ui/Card";
import Badge from "../../components/ui/Badge";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Legend,
} from "recharts";

const STATUS_BADGE = {
  "Pending": "warning",
  "Partially Allocated": "info",
  "Accepted": "success",
  "Dispatched": "info",
  "Delivered": "success",
  "Rejected": "danger",
  "Staged": "info",
  "Ready for Dispatch": "warning",
  "In Transit": "info",
};

export default function WarehouseDashboard() {
  const { toast } = useToast();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const d = await warehouseService.getDashboardSummary();
      setData(d);
    } catch {
      toast.error("Failed to load dashboard data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading) return <div className="flex justify-center items-center h-64"><LoadingSpinner size="lg" /></div>;
  if (!data) return null;

  return (
    <div className="p-4 md:p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <PageHeader title="Warehouse Dashboard" subtitle="Apex Central Logistics Hub — Peenya Industrial Area, Bengaluru" />
        <button onClick={load} className="flex items-center gap-2 text-sm text-gray-600 hover:text-blue-600 border border-gray-300 hover:border-blue-400 px-3 py-1.5 rounded-lg transition-colors">
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <StatCard title="Total Products" value={data.totalProducts} icon={Package} color="blue" />
        <StatCard title="Total Stock" value={data.totalStock.toLocaleString()} icon={BarChart2} color="purple" trendLabel="units" />
        <StatCard title="Available Stock" value={data.availableStock.toLocaleString()} icon={TrendingUp} color="green" trendLabel="units" />
        <StatCard title="Reserved Stock" value={data.reservedStock.toLocaleString()} icon={Package} color="orange" trendLabel="units" />
        <StatCard title="New Requests" value={data.incomingRequestsCount} icon={AlertTriangle} color="orange" trendLabel="pending" />
        <StatCard title="Pending Dispatch" value={data.pendingDispatchesCount} icon={Truck} color="blue" trendLabel="loads" />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Inventory Distribution by Category</h3>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={data.inventoryDistribution} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label={({ name, percent }) => `${name.split(" ")[0]}: ${(percent * 100).toFixed(0)}%`} labelLine>
                {data.inventoryDistribution.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip formatter={(v) => [v.toLocaleString() + " units", "Stock"]} />
            </PieChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Stock Movement (Units) — Last 6 Months</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={data.stockMovementChart} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="month" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend />
              <Bar dataKey="inbound" name="Inbound" fill="#2563eb" radius={[4,4,0,0]} />
              <Bar dataKey="outbound" name="Outbound" fill="#10b981" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Tables */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Incoming Requests</h3>
          {data.recentRequests.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-8">No pending requests.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-2 text-gray-500 font-medium">Order #</th>
                    <th className="text-left py-2 text-gray-500 font-medium">Shop</th>
                    <th className="text-left py-2 text-gray-500 font-medium">Items</th>
                    <th className="text-left py-2 text-gray-500 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recentRequests.map((r) => (
                    <tr key={r.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-2 font-mono text-blue-700">{r.orderNumber}</td>
                      <td className="py-2 text-gray-700 truncate max-w-[120px]">{r.shopName}</td>
                      <td className="py-2 text-gray-600">{r.items?.length ?? 0} items</td>
                      <td className="py-2"><Badge variant={STATUS_BADGE[r.status] || "neutral"}>{r.status}</Badge></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card className="p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Low Stock Products</h3>
          {data.lowStockProducts.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-8">All stock levels are healthy.</p>
          ) : (
            <div className="space-y-3">
              {data.lowStockProducts.map((p) => (
                <div key={p.id} className="flex items-center justify-between p-3 bg-orange-50 rounded-lg border border-orange-100">
                  <div>
                    <p className="text-sm font-medium text-gray-800">{p.productName}</p>
                    <p className="text-xs text-gray-500">{p.sku}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-orange-700">{p.availableQuantity} {p.unit}</p>
                    <p className="text-xs text-gray-500">available</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Recent Dispatches */}
      <Card className="p-6">
        <h3 className="font-semibold text-gray-900 mb-4">Recent Dispatches</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-2 text-gray-500 font-medium">Dispatch ID</th>
                <th className="text-left py-2 text-gray-500 font-medium">Order #</th>
                <th className="text-left py-2 text-gray-500 font-medium">Shop</th>
                <th className="text-left py-2 text-gray-500 font-medium">Carrier</th>
                <th className="text-left py-2 text-gray-500 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {data.recentDispatches.map((d) => (
                <tr key={d.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-2 font-mono text-gray-700">{d.id}</td>
                  <td className="py-2 font-mono text-blue-700">{d.orderNumber}</td>
                  <td className="py-2 text-gray-700 truncate max-w-[140px]">{d.shopName}</td>
                  <td className="py-2 text-gray-600">{d.carrierName}</td>
                  <td className="py-2"><Badge variant={STATUS_BADGE[d.status] || "neutral"}>{d.status}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
