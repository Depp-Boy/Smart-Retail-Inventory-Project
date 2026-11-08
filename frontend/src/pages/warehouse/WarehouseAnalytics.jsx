import { useState, useEffect } from "react";
import { warehouseService } from "../../services/warehouseService";
import { useToast } from "../../context/ToastContext";
import PageHeader from "../../components/ui/PageHeader";
import { Card, StatCard } from "../../components/ui/Card";
import LoadingSpinner from "../../components/ui/LoadingSpinner";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  PieChart, Pie, Cell,
} from "recharts";
import { CheckCircle, TrendingUp, Clock, XCircle, Package, RotateCcw } from "lucide-react";

const REJECTION_COLORS = ["#ef4444", "#f59e0b", "#8b5cf6"];

export default function WarehouseAnalytics() {
  const { toast } = useToast();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    warehouseService.getAnalytics().then(setData).catch(() => toast.error("Failed to load analytics.")).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex justify-center py-16"><LoadingSpinner size="lg" /></div>;
  if (!data) return null;

  const { metrics, monthlyThroughput, rejectionReasons } = data;

  return (
    <div className="p-4 md:p-6 space-y-6">
      <PageHeader title="Warehouse Analytics" subtitle="Performance metrics, throughput analysis, and fulfilment insights." />

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <StatCard title="Orders Received" value={metrics.totalOrdersReceived} icon={Package} color="blue" />
        <StatCard title="Fulfilled" value={metrics.fulfilledOrders} icon={CheckCircle} color="green" />
        <StatCard title="Fulfillment Rate" value={`${metrics.fulfillmentRate}%`} icon={TrendingUp} color="green" />
        <StatCard title="Rejected" value={metrics.rejectedRequests} icon={XCircle} color="red" />
        <StatCard title="Avg Turnaround" value={`${metrics.avgTurnaroundHours}h`} icon={Clock} color="blue" />
        <StatCard title="Inventory Turnover" value="6.8x" icon={RotateCcw} color="purple" trendLabel="per year" />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Monthly throughput - large */}
        <Card className="p-6 lg:col-span-2">
          <h3 className="font-semibold text-gray-900 mb-4">Monthly Throughput — Orders Received vs Fulfilled</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={monthlyThroughput} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="month" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend />
              <Bar dataKey="received" name="Received" fill="#2563eb" radius={[4,4,0,0]} />
              <Bar dataKey="fulfilled" name="Fulfilled" fill="#10b981" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        {/* Rejection reasons */}
        <Card className="p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Rejection Reasons</h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={rejectionReasons} dataKey="count" nameKey="reason" cx="50%" cy="50%" outerRadius={80} label={({ percent }) => `${(percent * 100).toFixed(0)}%`}>
                {rejectionReasons.map((_, i) => <Cell key={i} fill={REJECTION_COLORS[i % REJECTION_COLORS.length]} />)}
              </Pie>
              <Tooltip formatter={(v, n) => [v + " requests", n]} />
            </PieChart>
          </ResponsiveContainer>
          <div className="mt-3 space-y-2">
            {rejectionReasons.map((r, i) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: REJECTION_COLORS[i % REJECTION_COLORS.length] }} />
                  <span className="text-gray-700">{r.reason}</span>
                </div>
                <span className="font-medium text-gray-900">{r.count} ({r.percentage}%)</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Turnaround trend */}
      <Card className="p-6">
        <h3 className="font-semibold text-gray-900 mb-4">Average Turnaround Time (Hours) by Month</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={monthlyThroughput} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="month" tick={{ fontSize: 12 }} />
            <YAxis domain={[0, 6]} tick={{ fontSize: 12 }} />
            <Tooltip formatter={(v) => [`${v}h`, "Avg Turnaround"]} />
            <Bar dataKey="turnaroundHrs" name="Avg Turnaround (hrs)" fill="#8b5cf6" radius={[4,4,0,0]} />
          </BarChart>
        </ResponsiveContainer>
        <p className="text-xs text-gray-400 mt-2 text-center">Lower turnaround time indicates higher operational efficiency.</p>
      </Card>

      {/* Inventory turnover note */}
      <Card className="p-4 bg-blue-50 border border-blue-200">
        <div className="flex items-start gap-3">
          <TrendingUp className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-blue-800">Inventory Turnover Rate</p>
            <p className="text-sm text-blue-700 mt-0.5">{metrics.inventoryTurnoverRate}</p>
            <p className="text-xs text-blue-600 mt-1">A higher inventory turnover rate indicates that stock is moving efficiently through the warehouse without excessive holding. This warehouse is performing above the industry benchmark.</p>
          </div>
        </div>
      </Card>
    </div>
  );
}
