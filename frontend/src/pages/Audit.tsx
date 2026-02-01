import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FileText, ChevronLeft, ChevronRight, Search, Download } from 'lucide-react';
import { auditApi, type AuditFilters } from '@/services/audit';
import LoadingSpinner from '@/components/common/LoadingSpinner';
import { format } from 'date-fns';
import clsx from 'clsx';

const statusColors: Record<string, string> = {
  success: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
  dry_run: 'bg-blue-100 text-blue-800',
};

export default function Audit() {
  const [filters, setFilters] = useState<AuditFilters>({});
  const [page, setPage] = useState(1);
  const [expandedLog, setExpandedLog] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['audit', filters, page],
    queryFn: () => auditApi.list(filters, page, 50),
  });

  const handleExport = async (format: 'csv' | 'json') => {
    setIsExporting(true);
    try {
      await auditApi.export(filters, format);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="space-y-6 mt-16">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Audit Log</h1>
          <p className="text-gray-600">
            Track all actions performed on AWS resources
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => handleExport('csv')}
            disabled={isExporting}
            className="btn-secondary flex items-center gap-2"
          >
            <Download className="h-4 w-4" />
            {isExporting ? 'Exporting...' : 'Export CSV'}
          </button>
          <button
            onClick={() => handleExport('json')}
            disabled={isExporting}
            className="btn-secondary flex items-center gap-2"
          >
            <Download className="h-4 w-4" />
            {isExporting ? 'Exporting...' : 'Export JSON'}
          </button>
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
                placeholder="Search by user email..."
                className="w-full pl-10 pr-4 py-2 border rounded-md"
                value={filters.user_email || ''}
                onChange={(e) =>
                  setFilters((prev) => ({ ...prev, user_email: e.target.value }))
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
            <option value="">All Resources</option>
            <option value="ec2">EC2</option>
            <option value="rds">RDS</option>
            <option value="ecs">ECS</option>
            <option value="s3">S3</option>
            <option value="ebs">EBS</option>
            <option value="auth">Auth</option>
            <option value="aws_account">AWS Account</option>
          </select>
          <select
            className="border rounded-md px-3 py-2"
            value={filters.action || ''}
            onChange={(e) =>
              setFilters((prev) => ({
                ...prev,
                action: e.target.value || undefined,
              }))
            }
          >
            <option value="">All Actions</option>
            <option value="ec2:start">EC2 Start</option>
            <option value="ec2:stop">EC2 Stop</option>
            <option value="ec2:terminate">EC2 Terminate</option>
            <option value="rds:start">RDS Start</option>
            <option value="rds:stop">RDS Stop</option>
            <option value="rds:delete">RDS Delete</option>
            <option value="ecs:scale">ECS Scale</option>
            <option value="s3:delete">S3 Delete</option>
            <option value="ebs:delete">EBS Delete</option>
            <option value="auth:login">Auth Login</option>
            <option value="auth:logout">Auth Logout</option>
            <option value="auth:refresh">Auth Refresh</option>
            <option value="account:create">Account Create</option>
            <option value="account:update">Account Update</option>
            <option value="account:delete">Account Delete</option>
            <option value="account:verify">Account Verify</option>
          </select>
          <select
            className="border rounded-md px-3 py-2"
            value={filters.status || ''}
            onChange={(e) =>
              setFilters((prev) => ({
                ...prev,
                status: e.target.value || undefined,
              }))
            }
          >
            <option value="">All Statuses</option>
            <option value="success">Success</option>
            <option value="failed">Failed</option>
            <option value="dry_run">Dry Run</option>
          </select>
          <input
            type="date"
            className="border rounded-md px-3 py-2"
            value={filters.start_date || ''}
            onChange={(e) =>
              setFilters((prev) => ({
                ...prev,
                start_date: e.target.value || undefined,
              }))
            }
          />
          <input
            type="date"
            className="border rounded-md px-3 py-2"
            value={filters.end_date || ''}
            onChange={(e) =>
              setFilters((prev) => ({
                ...prev,
                end_date: e.target.value || undefined,
              }))
            }
          />
        </div>
      </div>

      {/* Audit Log Table */}
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
                    <th className="table-header">Timestamp</th>
                    <th className="table-header">User</th>
                    <th className="table-header">Action</th>
                    <th className="table-header">Resource</th>
                    <th className="table-header">Region</th>
                    <th className="table-header">Status</th>
                    <th className="table-header"></th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {data?.items.map((log) => (
                    <>
                      <tr
                        key={log.id}
                        className="hover:bg-gray-50 cursor-pointer"
                        onClick={() =>
                          setExpandedLog(expandedLog === log.id ? null : log.id)
                        }
                      >
                        <td className="table-cell">
                          <span className="text-sm">
                            {format(
                              new Date(log.created_at),
                              'MMM d, yyyy HH:mm:ss'
                            )}
                          </span>
                        </td>
                        <td className="table-cell">
                          <span className="text-sm">
                            {log.user_email || 'System'}
                          </span>
                        </td>
                        <td className="table-cell">
                          <span className="font-mono text-sm bg-gray-100 px-2 py-1 rounded">
                            {log.action}
                          </span>
                        </td>
                        <td className="table-cell">
                          <div>
                            <span className="text-sm font-medium">
                              {log.resource_id}
                            </span>
                            <span className="text-xs text-gray-500 ml-2">
                              ({log.resource_type})
                            </span>
                          </div>
                        </td>
                        <td className="table-cell">
                          <span className="text-sm">{log.region || '-'}</span>
                        </td>
                        <td className="table-cell">
                          <span
                            className={clsx(
                              'px-2 py-1 rounded-full text-xs font-medium',
                              statusColors[log.status] ||
                                'bg-gray-100 text-gray-800'
                            )}
                          >
                            {log.status}
                          </span>
                        </td>
                        <td className="table-cell">
                          <button className="text-gray-400 hover:text-gray-600">
                            <FileText className="h-4 w-4" />
                          </button>
                        </td>
                      </tr>
                      {expandedLog === log.id && (log.request_data || log.response_data) && (
                        <tr>
                          <td colSpan={7} className="bg-gray-50 px-6 py-4">
                            <div className="space-y-4">
                              {log.request_data && (
                                <div>
                                  <p className="text-sm font-medium text-gray-700 mb-2">
                                    Request Data:
                                  </p>
                                  <pre className="text-xs bg-gray-800 text-gray-100 p-4 rounded-lg overflow-x-auto">
                                    {JSON.stringify(log.request_data, null, 2)}
                                  </pre>
                                </div>
                              )}
                              {log.response_data && (
                                <div>
                                  <p className="text-sm font-medium text-gray-700 mb-2">
                                    Response Data:
                                  </p>
                                  <pre className="text-xs bg-gray-800 text-gray-100 p-4 rounded-lg overflow-x-auto">
                                    {JSON.stringify(log.response_data, null, 2)}
                                  </pre>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>
            </div>

            {data?.items.length === 0 && (
              <div className="p-12 text-center">
                <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900">
                  No audit logs found
                </h3>
                <p className="text-gray-500 mt-2">
                  Try adjusting your filters or check back after some actions
                  are performed.
                </p>
              </div>
            )}

            {/* Pagination */}
            {(data?.items.length || 0) > 0 && (
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
            )}
          </>
        )}
      </div>
    </div>
  );
}
