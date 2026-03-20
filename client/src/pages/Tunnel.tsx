import { useEffect, useState, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useInfiniteQuery } from '@tanstack/react-query';
import {
  Copy, ExternalLink, RefreshCw, Shield, Globe, Clock,
  Activity, Users, Zap, AlertCircle, ArrowLeft
} from 'lucide-react';
import { tunnelApi } from '@/lib/api';
import {
  formatTime,
  cn,
  getStatusColor,
  getStatusBgColor,
  getMethodColor,
  truncatePath,
} from '@/lib/utils';
import type { WSEvent, RequestLog } from '@/types';

export default function TunnelPage() {
  const { slug } = useParams<{ slug: string }>();
  const [liveLogs, setLiveLogs] = useState<RequestLog[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [visitorCount, setVisitorCount] = useState(0);
  const [copied, setCopied] = useState(false);

  const { data: tunnel, isLoading, error, refetch } = useQuery({
    queryKey: ['tunnel', slug],
    queryFn: () => tunnelApi.getTunnelStatus(slug!),
    refetchInterval: 30000,
    enabled: !!slug,
  });

  const { data: logsData, fetchNextPage, hasNextPage } = useInfiniteQuery({
    queryKey: ['requests', slug],
    queryFn: ({ pageParam = 1 }) =>
      tunnelApi.getRequestLogs(slug!, { page: pageParam, limit: 50 }),
    initialPageParam: 1,
    getNextPageParam: (lastPage) =>
      lastPage.page * lastPage.limit < lastPage.total ? lastPage.page + 1 : undefined,
    enabled: !!slug,
  });

  useEffect(() => {
    if (!slug) return;

    const wsUrl = `${import.meta.env.VITE_API_WS_URL || import.meta.env.VITE_API_URL || 'https://api.tunnel.dev'}/tunnels/${slug}/live`.replace(/^http/, 'ws');
    const token = localStorage.getItem('tunnel_token');
    
    const ws = new WebSocket(wsUrl);
    
    if (token) {
      ws.onopen = () => {
        ws.send(JSON.stringify({ token }));
        setWsConnected(true);
      };
    } else {
      ws.onopen = () => setWsConnected(true);
    }

    ws.onmessage = (event) => {
      try {
        const msg: WSEvent = JSON.parse(event.data);
        
        if (msg.type === 'connected') {
          setWsConnected(true);
        } else if (msg.type === 'request') {
          const req = msg.data as unknown as RequestLog;
          setLiveLogs((prev) => [req, ...prev.slice(0, 499)]);
        } else if (msg.type === 'visitor_count') {
          setVisitorCount((msg.data as { count: number }).count);
        } else if (msg.type === 'expired') {
          setWsConnected(false);
        }
      } catch (e) {
        console.error('WS parse error', e);
      }
    };

    ws.onclose = () => setWsConnected(false);
    ws.onerror = () => setWsConnected(false);

    return () => ws.close();
  }, [slug]);

  const copyUrl = useCallback(() => {
    if (tunnel?.url) {
      navigator.clipboard.writeText(tunnel.url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [tunnel?.url]);

  const allLogs = [
    ...liveLogs,
    ...(logsData?.pages.flatMap((p) => p.requests) || []),
  ];

  const statusColors: Record<string, string> = {
    active: 'bg-green-500',
    idle: 'bg-yellow-500',
    pending: 'bg-blue-500',
    expired: 'bg-red-500',
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error || !tunnel) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <AlertCircle className="w-12 h-12 text-red-500" />
        <h2 className="text-xl font-semibold text-gray-900">Tunnel not found</h2>
        <p className="text-gray-500">This tunnel may have expired or doesn't exist.</p>
        <Link to="/" className="flex items-center gap-2 text-blue-600 hover:text-blue-700">
          <ArrowLeft className="w-4 h-4" />
          Back to home
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <div className={cn('w-3 h-3 rounded-full', statusColors[tunnel.status] || 'bg-gray-500')} />
            <span className="text-sm font-medium text-gray-600 uppercase tracking-wide">
              {tunnel.status}
            </span>
            {wsConnected && (
              <span className="flex items-center gap-1 text-xs text-green-600">
                <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                Live
              </span>
            )}
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <h1 className="text-2xl font-bold text-gray-900 mb-2">
                  Tunnel — {tunnel.slug}
                </h1>
                <div className="flex items-center gap-4 text-sm text-gray-600">
                  <span className="flex items-center gap-1">
                    <Globe className="w-4 h-4" />
                    {tunnel.url}
                  </span>
                  {tunnel.expires_at && (
                    <span className="flex items-center gap-1">
                      <Clock className="w-4 h-4" />
                      Expires {new Date(tunnel.expires_at).toLocaleString()}
                    </span>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={copyUrl}
                  className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm font-medium transition-colors"
                >
                  <Copy className="w-4 h-4" />
                  {copied ? 'Copied!' : 'Copy URL'}
                </button>
                <a
                  href={tunnel.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
                >
                  <ExternalLink className="w-4 h-4" />
                  Open
                </a>
                <button
                  onClick={() => refetch()}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <RefreshCw className="w-4 h-4 text-gray-600" />
                </button>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { label: 'Total Requests', value: tunnel.stats?.total_requests || liveLogs.length || 0, icon: Activity },
            { label: 'Live Visitors', value: visitorCount, icon: Users },
            { label: 'Avg Latency', value: '45ms', icon: Zap },
            { label: 'Status', value: tunnel.status, icon: Shield },
          ].map((stat, i) => (
            <div key={i} className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
              <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
                <stat.icon className="w-4 h-4" />
                {stat.label}
              </div>
              <div className="text-2xl font-bold text-gray-900">{stat.value}</div>
            </div>
          ))}
        </div>

        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">Request Log</h2>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              {liveLogs.length > 0 && (
                <span className="flex items-center gap-1">
                  <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                  +{liveLogs.length} live
                </span>
              )}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Time</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Method</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Path</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Latency</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Country</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {allLogs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                      No requests yet. Share your tunnel URL to start receiving traffic.
                    </td>
                  </tr>
                ) : (
                  allLogs.slice(0, 100).map((log) => (
                    <tr
                      className="hover:bg-gray-50 cursor-pointer transition-colors"
                    >
                      <td className="px-6 py-3 text-sm text-gray-600 font-mono">
                        {formatTime(log.created_at)}
                      </td>
                      <td className="px-6 py-3">
                        <span className={cn('inline-flex px-2 py-0.5 rounded text-xs font-medium', getMethodColor(log.method))}>
                          {log.method}
                        </span>
                      </td>
                      <td className="px-6 py-3 text-sm text-gray-900 font-mono max-w-xs truncate">
                        {truncatePath(log.path)}
                      </td>
                      <td className="px-6 py-3">
                        <span className={cn('inline-flex px-2 py-0.5 rounded text-xs font-medium', getStatusBgColor(log.status_code), getStatusColor(log.status_code))}>
                          {log.status_code || '-'}
                        </span>
                      </td>
                      <td className="px-6 py-3 text-sm text-gray-600">
                        {log.latency_ms ? `${log.latency_ms}ms` : '-'}
                      </td>
                      <td className="px-6 py-3 text-sm text-gray-600">
                        {log.country_code || '??'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {hasNextPage && (
            <div className="px-6 py-4 border-t border-gray-100 text-center">
              <button
                onClick={() => fetchNextPage()}
                className="text-sm text-blue-600 hover:text-blue-700 font-medium"
              >
                Load more
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
