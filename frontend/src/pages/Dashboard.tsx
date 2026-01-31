import { useQuery } from '@tanstack/react-query';
import {
  Server,
  Database,
  FolderOpen,
  Cloud,
  DollarSign,
  TrendingUp,
  TrendingDown,
  AlertCircle,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { resourcesApi, costsApi } from '@/services';
import LoadingSpinner from '@/components/common/LoadingSpinner';
import { format } from 'date-fns';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

export default function Dashboard() {
  const { data: resources, isLoading: resourcesLoading } = useQuery({
    queryKey: ['resources', 'summary'],
    queryFn: () => resourcesApi.list({}, 1, 1000),
  });

  const { data: costSummary, isLoading: costsLoading } = useQuery({
    queryKey: ['costs', 'summary'],
    queryFn: () => costsApi.getSummary(),
  });

  const { data: dailyCosts } = useQuery({
    queryKey: ['costs', 'daily'],
    queryFn: () => costsApi.getDailyCosts(30),
  });

  const { data: costBreakdown } = useQuery({
    queryKey: ['costs', 'breakdown'],
    queryFn: () => costsApi.getBreakdown(),
  });

  const isLoading = resourcesLoading || costsLoading;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  // Calculate resource counts by type
  const resourceCounts = resources?.items.reduce(
    (acc, r) => {
      acc[r.resource_type] = (acc[r.resource_type] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  ) || {};

  const mtdChange = costSummary
    ? ((costSummary.mtd_cost - costSummary.last_month_cost) /
        costSummary.last_month_cost) *
      100
    : 0;

  return (
    <div className="space-y-6 mt-16">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600">Overview of your AWS resources and costs</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="EC2 Instances"
          value={resourceCounts.ec2 || 0}
          icon={Server}
          color="blue"
        />
        <StatCard
          title="RDS Databases"
          value={resourceCounts.rds || 0}
          icon={Database}
          color="green"
        />
        <StatCard
          title="S3 Buckets"
          value={resourceCounts.s3 || 0}
          icon={FolderOpen}
          color="yellow"
        />
        <StatCard
          title="Lambda Functions"
          value={resourceCounts.lambda || 0}
          icon={Cloud}
          color="purple"
        />
      </div>

      {/* Cost Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Month to Date</p>
              <p className="text-2xl font-bold text-gray-900">
                ${costSummary?.mtd_cost.toLocaleString() || '0'}
              </p>
            </div>
            <div
              className={`flex items-center gap-1 text-sm ${
                mtdChange > 0 ? 'text-red-600' : 'text-green-600'
              }`}
            >
              {mtdChange > 0 ? (
                <TrendingUp className="h-4 w-4" />
              ) : (
                <TrendingDown className="h-4 w-4" />
              )}
              {Math.abs(mtdChange).toFixed(1)}%
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div>
            <p className="text-sm text-gray-500">Forecasted This Month</p>
            <p className="text-2xl font-bold text-gray-900">
              ${costSummary?.mtd_forecast.toLocaleString() || '0'}
            </p>
          </div>
        </div>

        <div className="card p-6">
          <div>
            <p className="text-sm text-gray-500">Year to Date</p>
            <p className="text-2xl font-bold text-gray-900">
              ${costSummary?.ytd_cost.toLocaleString() || '0'}
            </p>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Daily Cost Trend */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Daily Cost Trend
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={dailyCosts || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  tickFormatter={(date) => format(new Date(date), 'MMM d')}
                />
                <YAxis tickFormatter={(value) => `$${value}`} />
                <Tooltip
                  formatter={(value: number) => [`$${value.toFixed(2)}`, 'Cost']}
                  labelFormatter={(date) =>
                    format(new Date(date), 'MMM d, yyyy')
                  }
                />
                <Area
                  type="monotone"
                  dataKey="cost"
                  stroke="#3b82f6"
                  fill="#93c5fd"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Cost by Service */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Cost by Service
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={costBreakdown?.by_service.slice(0, 6) || []}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="cost"
                  nameKey="service"
                  label={({ service, percentage }) =>
                    `${service}: ${percentage}%`
                  }
                >
                  {costBreakdown?.by_service.slice(0, 6).map((_, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={COLORS[index % COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value: number) => `$${value.toFixed(2)}`}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Resource Health */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Resource Health
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <HealthCard
            title="Running EC2"
            count={
              resources?.items.filter(
                (r) => r.resource_type === 'ec2' && r.state === 'running'
              ).length || 0
            }
            total={resourceCounts.ec2 || 0}
          />
          <HealthCard
            title="Available RDS"
            count={
              resources?.items.filter(
                (r) => r.resource_type === 'rds' && r.state === 'available'
              ).length || 0
            }
            total={resourceCounts.rds || 0}
          />
          <HealthCard
            title="Active ECS Services"
            count={
              resources?.items.filter(
                (r) => r.resource_type === 'ecs' && r.state === 'ACTIVE'
              ).length || 0
            }
            total={resourceCounts.ecs || 0}
          />
          <HealthCard
            title="Unattached EBS"
            count={
              resources?.items.filter(
                (r) =>
                  r.resource_type === 'ebs' &&
                  r.metadata.attachment_state === 'unattached'
              ).length || 0
            }
            total={resourceCounts.ebs || 0}
            isWarning
          />
        </div>
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  icon: Icon,
  color,
}: {
  title: string;
  value: number;
  icon: React.ComponentType<{ className?: string }>;
  color: 'blue' | 'green' | 'yellow' | 'purple';
}) {
  const colorClasses = {
    blue: 'bg-blue-100 text-blue-600',
    green: 'bg-green-100 text-green-600',
    yellow: 'bg-yellow-100 text-yellow-600',
    purple: 'bg-purple-100 text-purple-600',
  };

  return (
    <div className="card p-6">
      <div className="flex items-center gap-4">
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          <Icon className="h-6 w-6" />
        </div>
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
        </div>
      </div>
    </div>
  );
}

function HealthCard({
  title,
  count,
  total,
  isWarning = false,
}: {
  title: string;
  count: number;
  total: number;
  isWarning?: boolean;
}) {
  const percentage = total > 0 ? (count / total) * 100 : 0;

  return (
    <div className="p-4 bg-gray-50 rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700">{title}</span>
        {isWarning && count > 0 && (
          <AlertCircle className="h-4 w-4 text-yellow-500" />
        )}
      </div>
      <p className="text-xl font-bold text-gray-900">
        {count} / {total}
      </p>
      <div className="mt-2 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${
            isWarning ? 'bg-yellow-500' : 'bg-green-500'
          }`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
