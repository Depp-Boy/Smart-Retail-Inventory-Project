import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Package, ShoppingCart, AlertTriangle, Clock, TrendingUp, Plus,
  FileText, ArrowRight, CheckCircle2, ChevronRight, BarChart3
} from 'lucide-react';
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip,
  CartesianGrid, PieChart, Pie, Cell, Legend
} from 'recharts';
import { shopService } from '../../services/shopService';
import Button from '../../components/ui/Button';
import Badge from '../../components/ui/Badge';
import { Card, StatCard } from '../../components/ui/Card';
import PageHeader from '../../components/ui/PageHeader';
import LoadingSpinner from '../../components/ui/LoadingSpinner';

export default function ShopDashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const summary = await shopService.getDashboardSummary();
        setData(summary);
      } catch (err) {
        console.error('Failed to load shop dashboard data:', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="py-24 flex justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  const {
    totalProducts,
    totalInventoryUnits,
    lowStockCount,
    pendingOrdersCount,
    monthlySalesTotal,
    salesChartData,
    categoryDistribution,
    lowStockAlerts,
    recentSales,
    recentOrders,
    reorderRecommendations,
  } = data;

  return (
    <div className="space-y-6 pb-12">
      {/* Page Header with Quick Actions */}
      <PageHeader
        title="Shop Management Dashboard"
        subtitle="Real-time retail inventory overview, restocking status, and sales velocity."
        breadcrumbs={[{ label: 'Shop', href: '/shop/dashboard' }, { label: 'Dashboard' }]}
        action={
          <div className="flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              variant="secondary"
              icon={Plus}
              onClick={() => navigate('/shop/products')}
            >
              Add Product
            </Button>
            <Button
              size="sm"
              variant="secondary"
              icon={FileText}
              onClick={() => navigate('/shop/sales')}
            >
              Record Sale
            </Button>
            <Button
              size="sm"
              variant="primary"
              icon={ShoppingCart}
              onClick={() => navigate('/shop/orders')}
            >
              Create Restock Order
            </Button>
          </div>
        }
      />

      {/* Demonstration Banner */}
      <div className="p-3 bg-blue-50/70 border border-blue-200/60 rounded-xl text-xs text-blue-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
          <span>
            <strong>Demonstration Mode:</strong> Illustrative sample records simulating retail grocery inventory. Data actions are persisted locally for testing.
          </span>
        </div>
        <span className="text-[11px] font-mono text-blue-600 hidden sm:inline">DBMS Mini-Project</span>
      </div>

      {/* Summary Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3.5 sm:gap-4">
        <StatCard
          title="Total Products"
          value={totalProducts}
          icon={Package}
          color="blue"
          trend={+4}
          trendLabel="this month"
        />
        <StatCard
          title="Inventory Items"
          value={totalInventoryUnits.toLocaleString()}
          icon={BarChart3}
          color="purple"
          trendLabel="units in stock"
        />
        <StatCard
          title="Low Stock SKUs"
          value={lowStockCount}
          icon={AlertTriangle}
          color="orange"
          trendLabel="needs replenishment"
          trend={lowStockCount > 0 ? -15 : 0}
        />
        <StatCard
          title="Pending Orders"
          value={pendingOrdersCount}
          icon={Clock}
          color="blue"
          trendLabel="active restocks"
        />
        <StatCard
          title="Monthly Sales"
          value={`₹${monthlySalesTotal.toLocaleString()}`}
          icon={TrendingUp}
          color="green"
          trend={+12}
          trendLabel="vs last month"
          className="col-span-2 lg:col-span-1"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sales Overview Chart (2 cols) */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-5 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-gray-900">Sales Velocity & Forecast</h3>
              <p className="text-xs text-gray-500 mt-0.5">Monthly revenue trends and active sales volume (₹)</p>
            </div>
            <Link to="/shop/sales" className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1">
              View Sales <ChevronRight size={13} />
            </Link>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={salesChartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorSales" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#2563eb" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#2563eb" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="month" stroke="#94a3b8" fontSize={11} tickLine={false} />
                <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} tickFormatter={(val) => `₹${val / 1000}k`} />
                <Tooltip
                  formatter={(val) => [`₹${val.toLocaleString()}`, 'Revenue']}
                  contentStyle={{ backgroundColor: '#fff', borderColor: '#e2e8f0', borderRadius: '8px', fontSize: '12px' }}
                />
                <Area type="monotone" dataKey="sales" stroke="#2563eb" strokeWidth={2.5} fillOpacity={1} fill="url(#colorSales)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Category Distribution Pie Chart (1 col) */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-bold text-gray-900">Category Mix</h3>
              <span className="text-[11px] text-gray-400">By sales share</span>
            </div>
            <div className="h-52 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={categoryDistribution}
                    innerRadius={50}
                    outerRadius={75}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {categoryDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(val) => [`${val}%`, 'Share']}
                    contentStyle={{ backgroundColor: '#fff', borderColor: '#e2e8f0', borderRadius: '8px', fontSize: '12px' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
          {/* Legend */}
          <div className="grid grid-cols-2 gap-1.5 pt-2 border-t border-gray-100 text-[11px]">
            {categoryDistribution.map((cat) => (
              <div key={cat.name} className="flex items-center gap-1.5 text-gray-600">
                <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: cat.color }} />
                <span className="truncate">{cat.name}</span>
                <span className="font-semibold text-gray-800 ml-auto">{cat.value}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Critical Stock Alerts & Reorder Recommendations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Low Stock Alerts */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-xs">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="p-1.5 bg-orange-100 rounded-lg text-orange-600">
                <AlertTriangle size={16} />
              </div>
              <h3 className="text-sm font-bold text-gray-900">Low-Stock Alerts</h3>
            </div>
            <Link to="/shop/inventory" className="text-xs font-semibold text-blue-600 hover:text-blue-700">
              Manage All ({lowStockAlerts.length})
            </Link>
          </div>
          <div className="divide-y divide-gray-100">
            {lowStockAlerts.map((item) => (
              <div key={item.id} className="py-2.5 flex items-center justify-between text-xs">
                <div>
                  <p className="font-semibold text-gray-900">{item.productName}</p>
                  <p className="text-[11px] text-gray-400">SKU: {item.sku} · Threshold: {item.reorderThreshold} {item.unit}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="font-bold text-red-600 text-sm">
                    {item.quantity} {item.unit}
                  </span>
                  <Button
                    size="xs"
                    variant="secondary"
                    onClick={() => navigate('/shop/orders')}
                  >
                    Restock
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recommended Reorders from Demand Forecast */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-xs">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="p-1.5 bg-blue-100 rounded-lg text-blue-600">
                <TrendingUp size={16} />
              </div>
              <h3 className="text-sm font-bold text-gray-900">Recommended Reorders</h3>
            </div>
            <Link to="/shop/forecast" className="text-xs font-semibold text-blue-600 hover:text-blue-700">
              Forecasting Model →
            </Link>
          </div>
          <div className="divide-y divide-gray-100">
            {reorderRecommendations.map((prod) => (
              <div key={prod.productId} className="py-2.5 flex items-center justify-between text-xs">
                <div>
                  <p className="font-semibold text-gray-900">{prod.productName}</p>
                  <p className="text-[11px] text-gray-400">
                    Est. Stockout in: <span className="text-amber-600 font-bold">{prod.daysUntilStockout} days</span>
                  </p>
                </div>
                <div className="flex items-center gap-2 text-right">
                  <div>
                    <span className="font-bold text-blue-700 text-xs block">
                      +{prod.recommendedReorder} {prod.unit}
                    </span>
                    <span className="text-[10px] text-gray-400">Suggested Order</span>
                  </div>
                  <Button
                    size="xs"
                    variant="primary"
                    onClick={() => navigate('/shop/orders')}
                  >
                    Order
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Activity: Sales & Restock Orders */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Sales Table */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-gray-900">Recent Customer Sales</h3>
            <Link to="/shop/sales" className="text-xs font-semibold text-blue-600 hover:text-blue-700">
              View All History →
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-gray-50 text-gray-500 font-semibold uppercase text-[10px]">
                <tr>
                  <th className="p-2">Invoice</th>
                  <th className="p-2">Customer</th>
                  <th className="p-2">Payment</th>
                  <th className="p-2 text-right">Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {recentSales.map((s) => (
                  <tr key={s.id} className="hover:bg-gray-50/50">
                    <td className="p-2 font-mono font-medium text-gray-900">{s.saleNumber}</td>
                    <td className="p-2 text-gray-600 truncate max-w-32">{s.customerName}</td>
                    <td className="p-2 text-gray-500">{s.paymentMethod}</td>
                    <td className="p-2 text-right font-bold text-gray-900">₹{s.total.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Recent Replenishment Orders */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-gray-900">Recent Replenishment Orders</h3>
            <Link to="/shop/tracking" className="text-xs font-semibold text-blue-600 hover:text-blue-700">
              Order Tracking →
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-gray-50 text-gray-500 font-semibold uppercase text-[10px]">
                <tr>
                  <th className="p-2">Order ID</th>
                  <th className="p-2">Warehouse</th>
                  <th className="p-2">Status</th>
                  <th className="p-2 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {recentOrders.map((ord) => (
                  <tr key={ord.id} className="hover:bg-gray-50/50">
                    <td className="p-2 font-mono font-medium text-gray-900">{ord.orderNumber}</td>
                    <td className="p-2 text-gray-600 truncate max-w-36">{ord.destinationWarehouseName}</td>
                    <td className="p-2">
                      <Badge
                        variant={
                          ord.status === 'Delivered' ? 'success' :
                          ord.status === 'Dispatched' ? 'info' :
                          ord.status === 'Partially Allocated' ? 'warning' :
                          ord.status === 'Rejected' ? 'danger' : 'neutral'
                        }
                        dot
                      >
                        {ord.status}
                      </Badge>
                    </td>
                    <td className="p-2 text-right">
                      <button
                        onClick={() => navigate('/shop/tracking')}
                        className="text-xs text-blue-600 hover:text-blue-700 font-semibold"
                      >
                        Track
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
