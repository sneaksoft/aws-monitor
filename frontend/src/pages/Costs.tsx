import { useQuery } from '@tanstack/react-query';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';
import { TrendingUp, TrendingDown, DollarSign, Calendar } from 'lucide-react';
import { costsApi } from '@/services';
import LoadingSpinner from '@/components/common/LoadingSpinner';
import { format } from 'date-fns';

const COLORS = [
  '#3b82f6',
  '#10b981',
  '#f59e0b',
  '#ef4444',
  '#8b5cf6',
  '#ec4899',
  '#06b6d4',
  '#84cc16',
];

export default function Costs() {
  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['costs', 'summary'],
    queryFn: () => costsApi.getSummary(),
  });

  const { data: breakdown, isLoading: breakdownLoading } = useQuery({
    queryKey: ['costs', 'breakdown'],
    queryFn: () => costsApi.getBreakdown(),
  });

  const { data: dailyCosts, isLoading: dailyLoading } = useQuery({
    queryKey: ['costs', 'daily'],
    queryFn: () => costsApi.getDailyCosts(30),
  });

  const { data: forecast } = useQuery({
    queryKey: ['costs', 'forecast'],
    queryFn: () => costsApi.getForecast(),
  });

  const isLoading = summaryLoading || breakdownLoading || dailyLoading;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  const mtdChange = summary
    ? ((summary.mtd_cost - summary.last_month_cost) / summary.last_month_cost) *
      100
    : 0;

  return (
    <div className="space-y-6 mt-16">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Cost Analysis</h1>
        <p className="text-gray-600">Monitor and analyze your AWS spending</p>
      </div>

      {/* Cost Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <CostCard
          title="Month to Date"
          value={summary?.mtd_cost || 0}
          change={mtdChange}
          icon={DollarSign}
        />
        <CostCard
          title="Forecasted"
          value={summary?.mtd_forecast || 0}
          subtitle="End of month"
          icon={TrendingUp}
        />
        <CostCard
          title="Last Month"
          value={summary?.last_month_cost || 0}
          icon={Calendar}
        />
        <CostCard
          title="Year to Date"
          value={summary?.ytd_cost || 0}
          icon={DollarSign}
        />
      </div>

      {/* Daily Cost Trend */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Daily Cost Trend (Last 30 Days)
        </h3>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={dailyCosts || []}>
              <defs>
                <linearGradient id="costGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tickFormatter={(date) => format(new Date(date), 'MMM d')}
              />
              <YAxis tickFormatter={(value) => `$${value}`} />
              <Tooltip
                formatter={(value: number) => [`$${value.toFixed(2)}`, 'Cost']}
                labelFormatter={(date) => format(new Date(date), 'MMM d, yyyy')}
              />
              <Area
                type="monotone"
                dataKey="cost"
                stroke="#3b82f6"
                fill="url(#costGradient)"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Cost Breakdown Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* By Service */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Cost by Service
          </h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={breakdown?.by_service.slice(0, 8) || []}
                  cx="50%"
                  cy="50%"
                  innerRadius={80}
                  outerRadius={120}
                  paddingAngle={2}
                  dataKey="cost"
                  nameKey="service"
                >
                  {breakdown?.by_service.slice(0, 8).map((_, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={COLORS[index % COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value: number) => `$${value.toFixed(2)}`}
                />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* By Region */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Cost by Region
          </h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={breakdown?.by_region.slice(0, 8) || []}
                layout="vertical"
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" tickFormatter={(value) => `$${value}`} />
                <YAxis type="category" dataKey="region" width={100} />
                <Tooltip
                  formatter={(value: number) => `$${value.toFixed(2)}`}
                />
                <Bar dataKey="cost" fill="#3b82f6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Service Breakdown Table */}
      <div className="card overflow-hidden">
        <div className="px-6 py-4 border-b">
          <h3 className="text-lg font-semibold text-gray-900">
            Detailed Cost Breakdown
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="table-header">Service</th>
                <th className="table-header text-right">Cost</th>
                <th className="table-header text-right">% of Total</th>
                <th className="table-header">Distribution</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {breakdown?.by_service.map((service, index) => (
                <tr key={service.service} className="hover:bg-gray-50">
                  <td className="table-cell font-medium">{service.service}</td>
                  <td className="table-cell text-right">
                    ${service.cost.toLocaleString(undefined, {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                  </td>
                  <td className="table-cell text-right">
                    {service.percentage.toFixed(1)}%
                  </td>
                  <td className="table-cell">
                    <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${service.percentage}%`,
                          backgroundColor: COLORS[index % COLORS.length],
                        }}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-gray-50">
              <tr>
                <td className="table-cell font-semibold">Total</td>
                <td className="table-cell text-right font-semibold">
                  ${breakdown?.total.toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}
                </td>
                <td className="table-cell text-right font-semibold">100%</td>
                <td className="table-cell"></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  );
}

function CostCard({
  title,
  value,
  change,
  subtitle,
  icon: Icon,
}: {
  title: string;
  value: number;
  change?: number;
  subtitle?: string;
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div className="card p-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">
            ${value.toLocaleString(undefined, {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </p>
          {subtitle && (
            <p className="text-xs text-gray-500 mt-1">{subtitle}</p>
          )}
          {change !== undefined && (
            <div
              className={`flex items-center gap-1 text-sm mt-2 ${
                change > 0 ? 'text-red-600' : 'text-green-600'
              }`}
            >
              {change > 0 ? (
                <TrendingUp className="h-4 w-4" />
              ) : (
                <TrendingDown className="h-4 w-4" />
              )}
              {Math.abs(change).toFixed(1)}% vs last month
            </div>
          )}
        </div>
        <div className="p-3 bg-primary-100 rounded-lg">
          <Icon className="h-6 w-6 text-primary-600" />
        </div>
      </div>
    </div>
  );
}
