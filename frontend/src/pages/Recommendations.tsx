import { useQuery } from '@tanstack/react-query';
import {
  Lightbulb,
  DollarSign,
  AlertTriangle,
  Server,
  HardDrive,
  Camera,
} from 'lucide-react';
import { costsApi } from '@/services';
import LoadingSpinner from '@/components/common/LoadingSpinner';
import clsx from 'clsx';

const recommendationIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  idle_instance: Server,
  unattached_volume: HardDrive,
  old_snapshot: Camera,
};

const priorityColors = {
  high: 'border-red-200 bg-red-50',
  medium: 'border-yellow-200 bg-yellow-50',
  low: 'border-blue-200 bg-blue-50',
};

const priorityBadges = {
  high: 'bg-red-100 text-red-800',
  medium: 'bg-yellow-100 text-yellow-800',
  low: 'bg-blue-100 text-blue-800',
};

export default function Recommendations() {
  const { data, isLoading } = useQuery({
    queryKey: ['costs', 'recommendations'],
    queryFn: () => costsApi.getRecommendations(),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  const recommendations = data?.recommendations || [];
  const groupedByType = recommendations.reduce(
    (acc, rec) => {
      if (!acc[rec.recommendation_type]) {
        acc[rec.recommendation_type] = [];
      }
      acc[rec.recommendation_type].push(rec);
      return acc;
    },
    {} as Record<string, typeof recommendations>
  );

  const totalSavings = data?.total_potential_savings || 0;

  return (
    <div className="space-y-6 mt-16">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Cost Optimization Recommendations
          </h1>
          <p className="text-gray-600">
            Actionable insights to reduce your AWS spending
          </p>
        </div>
      </div>

      {/* Summary Card */}
      <div className="card p-6 bg-gradient-to-r from-primary-500 to-primary-600 text-white">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-primary-100">Total Potential Monthly Savings</p>
            <p className="text-4xl font-bold mt-2">
              ${totalSavings.toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </p>
            <p className="text-primary-100 mt-2">
              {recommendations.length} optimization{' '}
              {recommendations.length === 1 ? 'opportunity' : 'opportunities'}{' '}
              found
            </p>
          </div>
          <div className="p-4 bg-white/20 rounded-full">
            <Lightbulb className="h-12 w-12" />
          </div>
        </div>
      </div>

      {/* Priority Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <PrioritySummary
          priority="high"
          count={recommendations.filter((r) => r.priority === 'high').length}
          savings={recommendations
            .filter((r) => r.priority === 'high')
            .reduce((sum, r) => sum + r.estimated_monthly_savings, 0)}
        />
        <PrioritySummary
          priority="medium"
          count={recommendations.filter((r) => r.priority === 'medium').length}
          savings={recommendations
            .filter((r) => r.priority === 'medium')
            .reduce((sum, r) => sum + r.estimated_monthly_savings, 0)}
        />
        <PrioritySummary
          priority="low"
          count={recommendations.filter((r) => r.priority === 'low').length}
          savings={recommendations
            .filter((r) => r.priority === 'low')
            .reduce((sum, r) => sum + r.estimated_monthly_savings, 0)}
        />
      </div>

      {/* Recommendations by Type */}
      {Object.entries(groupedByType).map(([type, recs]) => (
        <div key={type} className="card overflow-hidden">
          <div className="px-6 py-4 border-b bg-gray-50">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              {getRecommendationIcon(type)}
              {getRecommendationTitle(type)}
              <span className="text-sm font-normal text-gray-500">
                ({recs.length})
              </span>
            </h3>
          </div>
          <div className="divide-y divide-gray-200">
            {recs.map((rec) => (
              <RecommendationRow key={rec.resource_id} recommendation={rec} />
            ))}
          </div>
        </div>
      ))}

      {recommendations.length === 0 && (
        <div className="card p-12 text-center">
          <Lightbulb className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900">
            No recommendations found
          </h3>
          <p className="text-gray-500 mt-2">
            Your AWS resources appear to be well-optimized. Check back later for
            new recommendations.
          </p>
        </div>
      )}
    </div>
  );
}

function PrioritySummary({
  priority,
  count,
  savings,
}: {
  priority: 'high' | 'medium' | 'low';
  count: number;
  savings: number;
}) {
  const colors = {
    high: 'text-red-600',
    medium: 'text-yellow-600',
    low: 'text-blue-600',
  };

  return (
    <div className="card p-6">
      <div className="flex items-center gap-3">
        <AlertTriangle className={`h-5 w-5 ${colors[priority]}`} />
        <span className="text-sm font-medium text-gray-500 capitalize">
          {priority} Priority
        </span>
      </div>
      <p className="text-2xl font-bold text-gray-900 mt-2">{count}</p>
      <p className="text-sm text-gray-500">
        ${savings.toFixed(2)} potential savings
      </p>
    </div>
  );
}

function RecommendationRow({
  recommendation,
}: {
  recommendation: {
    resource_id: string;
    resource_type: string;
    recommendation_type: string;
    description: string;
    estimated_monthly_savings: number;
    current_monthly_cost: number;
    priority: 'high' | 'medium' | 'low';
  };
}) {
  const Icon = recommendationIcons[recommendation.recommendation_type] || Server;

  return (
    <div
      className={clsx(
        'px-6 py-4 border-l-4',
        priorityColors[recommendation.priority]
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-4">
          <div className="p-2 bg-white rounded-lg shadow-sm">
            <Icon className="h-5 w-5 text-gray-600" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="font-medium text-gray-900">
                {recommendation.resource_id}
              </h4>
              <span
                className={clsx(
                  'px-2 py-0.5 rounded-full text-xs font-medium capitalize',
                  priorityBadges[recommendation.priority]
                )}
              >
                {recommendation.priority}
              </span>
            </div>
            <p className="text-sm text-gray-600 mt-1">
              {recommendation.description}
            </p>
            <p className="text-xs text-gray-500 mt-2">
              Type: {recommendation.resource_type}
            </p>
          </div>
        </div>
        <div className="text-right">
          <div className="flex items-center gap-1 text-green-600">
            <DollarSign className="h-4 w-4" />
            <span className="font-semibold">
              {recommendation.estimated_monthly_savings.toFixed(2)}/mo
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Current: ${recommendation.current_monthly_cost.toFixed(2)}/mo
          </p>
        </div>
      </div>
    </div>
  );
}

function getRecommendationIcon(type: string) {
  const Icon = recommendationIcons[type] || Lightbulb;
  return <Icon className="h-5 w-5 text-gray-600" />;
}

function getRecommendationTitle(type: string): string {
  const titles: Record<string, string> = {
    idle_instance: 'Idle EC2 Instances',
    unattached_volume: 'Unattached EBS Volumes',
    old_snapshot: 'Old EBS Snapshots',
  };
  return titles[type] || type;
}
