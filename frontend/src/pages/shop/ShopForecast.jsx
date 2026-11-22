import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  TrendingUp, AlertTriangle, Clock, ShoppingCart, HelpCircle,
  BarChart2, Info, ArrowUpRight, ArrowDownRight, Minus
} from 'lucide-react';
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip,
  CartesianGrid, Legend
} from 'recharts';
import { shopService } from '../../services/shopService';
import PageHeader from '../../components/ui/PageHeader';
import DataTable from '../../components/common/DataTable';
import Badge from '../../components/ui/Badge';
import Button from '../../components/ui/Button';
import LoadingSpinner from '../../components/ui/LoadingSpinner';

export default function ShopForecast() {
  const navigate = useNavigate();
  const [forecastData, setForecastData] = useState(null);
  const [forecastPeriod, setForecastPeriod] = useState('7d'); // '7d', '14d', '30d'
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const data = await shopService.getForecastData();
        setForecastData(data);
      } catch (err) {
        console.error(err);
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

  const { products, historicalVsForecast } = forecastData;

  const stockoutWarningsCount = products.filter((p) => p.daysUntilStockout <= 5).length;
  const slowMovingCount = products.filter((p) => p.isSlowMoving).length;

  const columns = [
    {
      key: 'productName',
      label: 'Commodity',
      sortable: true,
      render: (val, row) => (
        <div>
          <div className="flex items-center gap-1.5">
            <span className="font-semibold text-gray-900 text-xs sm:text-sm">{val}</span>
            {row.isSlowMoving && (
              <span className="text-[10px] bg-amber-50 text-amber-700 border border-amber-200 px-1 rounded font-medium">
                Slow-moving
              </span>
            )}
          </div>
          <p className="text-[11px] font-mono text-gray-400">SKU: {row.sku} · {row.category}</p>
        </div>
      ),
    },
    {
      key: 'currentStock',
      label: 'Current Stock',
      sortable: true,
      render: (val, row) => (
        <span className={[
          'font-bold text-xs',
          val === 0 ? 'text-red-600' : val < 30 ? 'text-orange-600' : 'text-gray-800',
        ].join(' ')}>
          {val} {row.unit}
        </span>
      ),
    },
    {
      key: forecastPeriod === '7d' ? 'predictedDemand7d' : forecastPeriod === '14d' ? 'predictedDemand14d' : 'predictedDemand30d',
      label: `Predicted Demand (${forecastPeriod === '7d' ? '7 Days' : forecastPeriod === '14d' ? '14 Days' : '30 Days'})`,
      sortable: true,
      render: (val, row) => (
        <span className="font-bold text-blue-700 text-xs sm:text-sm">
          ~{val} {row.unit}
        </span>
      ),
    },
    {
      key: 'daysUntilStockout',
      label: 'Days to Stockout',
      sortable: true,
      render: (val, row) => {
        if (val === 0) {
          return (
            <span className="inline-flex items-center gap-1 text-xs font-bold text-red-600 bg-red-50 border border-red-200 px-2 py-0.5 rounded-full">
              <AlertTriangle size={12} /> Stocked Out
            </span>
          );
        }
        if (val <= 4) {
          return (
            <span className="inline-flex items-center gap-1 text-xs font-bold text-orange-600 bg-orange-50 border border-orange-200 px-2 py-0.5 rounded-full">
              <AlertTriangle size={12} /> {val} days left
            </span>
          );
        }
        return <span className="text-xs text-gray-700 font-medium">{val} days</span>;
      },
    },
    {
      key: 'recommendedReorder',
      label: 'Reorder Suggestion',
      sortable: true,
      render: (val, row) => (
        val > 0 ? (
          <span className="font-bold text-green-700 text-xs">
            +{val} {row.unit}
          </span>
        ) : (
          <span className="text-gray-400 text-xs">Sufficient</span>
        )
      ),
    },
    {
      key: 'seasonalFactor',
      label: 'Demand Influencer',
      render: (val) => <span className="text-gray-500 text-[11px]">{val}</span>,
    },
  ];

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title="Demand Forecasting & Reorder Intelligence"
        subtitle="Predictive commodity demand trends, potential stockout warnings, and proactive replenishment suggestions."
        breadcrumbs={[{ label: 'Shop', href: '/shop/dashboard' }, { label: 'Demand Forecast' }]}
        action={
          <div className="flex items-center gap-1 bg-gray-100 p-1 rounded-xl">
            {[
              { id: '7d', label: '7-Day View' },
              { id: '14d', label: '14-Day View' },
              { id: '30d', label: '30-Day View' },
            ].map((p) => (
              <button
                key={p.id}
                onClick={() => setForecastPeriod(p.id)}
                className={[
                  'px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors',
                  forecastPeriod === p.id ? 'bg-white text-blue-700 shadow-2xs' : 'text-gray-600 hover:text-gray-900',
                ].join(' ')}
              >
                {p.label}
              </button>
            ))}
          </div>
        }
      />

      {/* Mandatory Illustrative Demonstration Notice */}
      <div className="p-3.5 bg-amber-50/70 border border-amber-200/60 rounded-xl text-xs text-amber-900 flex items-start gap-2.5">
        <Info size={16} className="text-amber-600 flex-shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <strong>Illustrative Model Disclosure:</strong> All forecasts presented in this dashboard are generated from simulated historical sales run rates for educational DBMS demonstration. In Phase 3, this frontend will interface with backend machine-learning demand regression pipelines.
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-xs">
          <p className="text-xs text-gray-400 font-semibold uppercase tracking-wider">Imminent Stockouts</p>
          <p className="text-2xl font-bold text-red-600 mt-1">{stockoutWarningsCount} SKUs</p>
          <span className="text-[11px] text-gray-500">Projected depletion within ≤ 5 days</span>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-xs">
          <p className="text-xs text-gray-400 font-semibold uppercase tracking-wider">Slow-Moving SKUs</p>
          <p className="text-2xl font-bold text-amber-600 mt-1">{slowMovingCount} SKUs</p>
          <span className="text-[11px] text-gray-500">&gt;40 days of supply remaining</span>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-xs">
          <p className="text-xs text-gray-400 font-semibold uppercase tracking-wider">Model Confidence</p>
          <p className="text-2xl font-bold text-blue-600 mt-1">89.4%</p>
          <span className="text-[11px] text-gray-500">Back-tested historical alignment</span>
        </div>
      </div>

      {/* Historical Sales vs Projected Demand Chart */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-4 gap-1">
          <div>
            <h3 className="text-sm font-bold text-gray-900">
              Aggregated Historical vs. Projected Demand Curve
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Weekly physical units sold across top 10 staple commodities (Rice, Atta, Oil, Sugar, Dal)
            </p>
          </div>
          <span className="text-xs text-blue-600 font-semibold bg-blue-50 px-2.5 py-1 rounded-md w-fit">
            Next 4 Weeks Projected Trend
          </span>
        </div>

        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={historicalVsForecast} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="period" stroke="#94a3b8" fontSize={11} tickLine={false} />
              <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} tickFormatter={(v) => `${v}u`} />
              <Tooltip
                contentStyle={{ backgroundColor: '#fff', borderColor: '#e2e8f0', borderRadius: '8px', fontSize: '12px' }}
              />
              <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
              <Line
                type="monotone"
                dataKey="historicalSales"
                name="Historical Actuals (Units)"
                stroke="#64748b"
                strokeWidth={2}
                dot={{ r: 4 }}
              />
              <Line
                type="monotone"
                dataKey="predictedDemand"
                name="Forecasted Trend (Units)"
                stroke="#2563eb"
                strokeWidth={2.5}
                strokeDasharray="4 4"
                dot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Product-Wise Demand Breakdown Table */}
      <div>
        <h3 className="text-sm font-bold text-gray-900 mb-3">
          Commodity-Wise Predictive Matrix
        </h3>
        <DataTable
          columns={columns}
          data={products}
          searchPlaceholder="Search commodity..."
          searchKeys={['productName', 'sku', 'category']}
          pageSize={8}
          actions={(row) => (
            row.recommendedReorder > 0 ? (
              <Button
                size="xs"
                variant="primary"
                onClick={() => navigate('/shop/orders')}
              >
                Reorder Now
              </Button>
            ) : null
          )}
        />
      </div>
    </div>
  );
}
