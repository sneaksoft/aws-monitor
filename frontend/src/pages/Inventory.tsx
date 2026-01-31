import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Search,
  Filter,
  Download,
  Play,
  Square,
  Trash2,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { resourcesApi, actionsApi } from '@/services';
import { useUIStore, useAuthStore } from '@/store';
import LoadingSpinner from '@/components/common/LoadingSpinner';
import ConfirmDialog from '@/components/common/ConfirmDialog';
import type { Resource, ResourceFilters } from '@/types';
import clsx from 'clsx';

const RESOURCE_TYPES = [
  { value: '', label: 'All Types' },
  { value: 'ec2', label: 'EC2 Instances' },
  { value: 'ebs', label: 'EBS Volumes' },
  { value: 'rds', label: 'RDS Databases' },
  { value: 's3', label: 'S3 Buckets' },
  { value: 'ecs', label: 'ECS Services' },
  { value: 'lambda', label: 'Lambda Functions' },
];

const STATES = [
  { value: '', label: 'All States' },
  { value: 'running', label: 'Running' },
  { value: 'stopped', label: 'Stopped' },
  { value: 'available', label: 'Available' },
  { value: 'ACTIVE', label: 'Active' },
];

export default function Inventory() {
  const queryClient = useQueryClient();
  const { addToast } = useUIStore();
  const { user } = useAuthStore();

  const [filters, setFilters] = useState<ResourceFilters>({});
  const [page, setPage] = useState(1);
  const [selectedResources, setSelectedResources] = useState<string[]>([]);
  const [confirmDialog, setConfirmDialog] = useState<{
    isOpen: boolean;
    action: string;
    resourceId: string;
  }>({ isOpen: false, action: '', resourceId: '' });

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['resources', filters, page],
    queryFn: () => resourcesApi.list(filters, page, 50),
  });

  const startMutation = useMutation({
    mutationFn: (instanceIds: string[]) => actionsApi.ec2Start(instanceIds, false),
    onSuccess: () => {
      addToast({ type: 'success', message: 'Instances starting...' });
      queryClient.invalidateQueries({ queryKey: ['resources'] });
    },
    onError: () => {
      addToast({ type: 'error', message: 'Failed to start instances' });
    },
  });

  const stopMutation = useMutation({
    mutationFn: (instanceIds: string[]) => actionsApi.ec2Stop(instanceIds, false),
    onSuccess: () => {
      addToast({ type: 'success', message: 'Instances stopping...' });
      queryClient.invalidateQueries({ queryKey: ['resources'] });
    },
    onError: () => {
      addToast({ type: 'error', message: 'Failed to stop instances' });
    },
  });

  const terminateMutation = useMutation({
    mutationFn: (instanceIds: string[]) =>
      actionsApi.ec2Terminate(instanceIds, false),
    onSuccess: () => {
      addToast({ type: 'success', message: 'Instances terminated' });
      queryClient.invalidateQueries({ queryKey: ['resources'] });
      setConfirmDialog({ isOpen: false, action: '', resourceId: '' });
    },
    onError: () => {
      addToast({ type: 'error', message: 'Failed to terminate instances' });
    },
  });

  const handleExport = async (format: 'csv' | 'json') => {
    try {
      const blob =
        format === 'csv'
          ? await resourcesApi.exportCsv(filters)
          : await resourcesApi.exportJson(filters);

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `aws_resources.${format}`;
      a.click();
      window.URL.revokeObjectURL(url);

      addToast({ type: 'success', message: `Exported as ${format.toUpperCase()}` });
    } catch {
      addToast({ type: 'error', message: 'Export failed' });
    }
  };

  const toggleResourceSelection = (resourceId: string) => {
    setSelectedResources((prev) =>
      prev.includes(resourceId)
        ? prev.filter((id) => id !== resourceId)
        : [...prev, resourceId]
    );
  };

  const canPerformActions = user?.role === 'admin' || user?.role === 'operator';

  return (
    <div className="space-y-6 mt-16">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Resource Inventory</h1>
          <p className="text-gray-600">
            {data?.total || 0} resources across your AWS account
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => refetch()}
            className="btn-secondary flex items-center gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          <div className="relative group">
            <button className="btn-secondary flex items-center gap-2">
              <Download className="h-4 w-4" />
              Export
            </button>
            <div className="absolute right-0 mt-1 w-32 bg-white border rounded-md shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
              <button
                onClick={() => handleExport('csv')}
                className="block w-full px-4 py-2 text-left text-sm hover:bg-gray-100"
              >
                Export CSV
              </button>
              <button
                onClick={() => handleExport('json')}
                className="block w-full px-4 py-2 text-left text-sm hover:bg-gray-100"
              >
                Export JSON
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search by name or ID..."
                className="w-full pl-10 pr-4 py-2 border rounded-md"
                value={filters.search || ''}
                onChange={(e) =>
                  setFilters((prev) => ({ ...prev, search: e.target.value }))
                }
              />
            </div>
          </div>
          <select
            className="border rounded-md px-3 py-2"
            value={filters.resource_type || ''}
            onChange={(e) =>
              setFilters((prev) => ({
                ...prev,
                resource_type: e.target.value || undefined,
              }))
            }
          >
            {RESOURCE_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
          <select
            className="border rounded-md px-3 py-2"
            value={filters.state || ''}
            onChange={(e) =>
              setFilters((prev) => ({
                ...prev,
                state: e.target.value || undefined,
              }))
            }
          >
            {STATES.map((state) => (
              <option key={state.value} value={state.value}>
                {state.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Bulk Actions */}
      {selectedResources.length > 0 && canPerformActions && (
        <div className="card p-4 bg-primary-50 border-primary-200">
          <div className="flex items-center justify-between">
            <span className="text-sm text-primary-700">
              {selectedResources.length} resource(s) selected
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => startMutation.mutate(selectedResources)}
                className="btn-secondary flex items-center gap-1"
              >
                <Play className="h-4 w-4" />
                Start
              </button>
              <button
                onClick={() => stopMutation.mutate(selectedResources)}
                className="btn-secondary flex items-center gap-1"
              >
                <Square className="h-4 w-4" />
                Stop
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Resource Table */}
      <div className="card overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <LoadingSpinner size="lg" />
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    {canPerformActions && (
                      <th className="table-header w-12">
                        <input
                          type="checkbox"
                          className="rounded border-gray-300"
                          checked={
                            selectedResources.length === data?.items.length &&
                            data?.items.length > 0
                          }
                          onChange={(e) =>
                            setSelectedResources(
                              e.target.checked
                                ? data?.items.map((r) => r.resource_id) || []
                                : []
                            )
                          }
                        />
                      </th>
                    )}
                    <th className="table-header">Name / ID</th>
                    <th className="table-header">Type</th>
                    <th className="table-header">Region</th>
                    <th className="table-header">State</th>
                    <th className="table-header">Tags</th>
                    {canPerformActions && (
                      <th className="table-header">Actions</th>
                    )}
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {data?.items.map((resource) => (
                    <ResourceRow
                      key={resource.resource_id}
                      resource={resource}
                      isSelected={selectedResources.includes(resource.resource_id)}
                      onToggleSelect={() =>
                        toggleResourceSelection(resource.resource_id)
                      }
                      canPerformActions={canPerformActions}
                      onStart={() => startMutation.mutate([resource.resource_id])}
                      onStop={() => stopMutation.mutate([resource.resource_id])}
                      onTerminate={() =>
                        setConfirmDialog({
                          isOpen: true,
                          action: 'terminate',
                          resourceId: resource.resource_id,
                        })
                      }
                    />
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="px-6 py-4 border-t flex items-center justify-between">
              <span className="text-sm text-gray-600">
                Showing {(page - 1) * 50 + 1} to{' '}
                {Math.min(page * 50, data?.total || 0)} of {data?.total || 0}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="btn-secondary"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={!data?.has_more}
                  className="btn-secondary"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Confirm Dialog */}
      <ConfirmDialog
        isOpen={confirmDialog.isOpen}
        onClose={() =>
          setConfirmDialog({ isOpen: false, action: '', resourceId: '' })
        }
        onConfirm={() => terminateMutation.mutate([confirmDialog.resourceId])}
        title="Terminate Instance"
        description="This action cannot be undone. The instance and its data will be permanently deleted."
        confirmText={confirmDialog.resourceId}
        isDestructive
      />
    </div>
  );
}

function ResourceRow({
  resource,
  isSelected,
  onToggleSelect,
  canPerformActions,
  onStart,
  onStop,
  onTerminate,
}: {
  resource: Resource;
  isSelected: boolean;
  onToggleSelect: () => void;
  canPerformActions: boolean;
  onStart: () => void;
  onStop: () => void;
  onTerminate: () => void;
}) {
  const stateColors: Record<string, string> = {
    running: 'bg-green-100 text-green-800',
    stopped: 'bg-gray-100 text-gray-800',
    available: 'bg-green-100 text-green-800',
    ACTIVE: 'bg-green-100 text-green-800',
    pending: 'bg-yellow-100 text-yellow-800',
    stopping: 'bg-yellow-100 text-yellow-800',
  };

  const typeLabels: Record<string, string> = {
    ec2: 'EC2 Instance',
    ebs: 'EBS Volume',
    rds: 'RDS Database',
    s3: 'S3 Bucket',
    ecs: 'ECS Service',
    lambda: 'Lambda Function',
  };

  return (
    <tr className="hover:bg-gray-50">
      {canPerformActions && (
        <td className="table-cell">
          <input
            type="checkbox"
            className="rounded border-gray-300"
            checked={isSelected}
            onChange={onToggleSelect}
          />
        </td>
      )}
      <td className="table-cell">
        <div>
          <p className="font-medium text-gray-900">
            {resource.name || resource.resource_id}
          </p>
          {resource.name && (
            <p className="text-xs text-gray-500">{resource.resource_id}</p>
          )}
        </div>
      </td>
      <td className="table-cell">
        <span className="text-sm">{typeLabels[resource.resource_type]}</span>
      </td>
      <td className="table-cell">
        <span className="text-sm">{resource.region}</span>
      </td>
      <td className="table-cell">
        {resource.state && (
          <span
            className={clsx(
              'px-2 py-1 rounded-full text-xs font-medium',
              stateColors[resource.state] || 'bg-gray-100 text-gray-800'
            )}
          >
            {resource.state}
          </span>
        )}
      </td>
      <td className="table-cell">
        <div className="flex gap-1 flex-wrap max-w-xs">
          {Object.entries(resource.tags)
            .slice(0, 3)
            .map(([key, value]) => (
              <span
                key={key}
                className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded"
                title={`${key}: ${value}`}
              >
                {key}: {value.slice(0, 15)}
              </span>
            ))}
          {Object.keys(resource.tags).length > 3 && (
            <span className="text-xs text-gray-500">
              +{Object.keys(resource.tags).length - 3}
            </span>
          )}
        </div>
      </td>
      {canPerformActions && (
        <td className="table-cell">
          <div className="flex gap-1">
            {resource.resource_type === 'ec2' && (
              <>
                {resource.state === 'stopped' && (
                  <button
                    onClick={onStart}
                    className="p-1 rounded hover:bg-green-100 text-green-600"
                    title="Start"
                  >
                    <Play className="h-4 w-4" />
                  </button>
                )}
                {resource.state === 'running' && (
                  <button
                    onClick={onStop}
                    className="p-1 rounded hover:bg-yellow-100 text-yellow-600"
                    title="Stop"
                  >
                    <Square className="h-4 w-4" />
                  </button>
                )}
                <button
                  onClick={onTerminate}
                  className="p-1 rounded hover:bg-red-100 text-red-600"
                  title="Terminate"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </>
            )}
          </div>
        </td>
      )}
    </tr>
  );
}
