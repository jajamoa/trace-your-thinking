'use client';
import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { CheckCircle, XCircle, AlertCircle, RefreshCw, Database, Server } from 'lucide-react';

interface SystemStatus {
  database: {
    connected: boolean;
    error?: string;
    details?: {
      version?: string;
      collections?: string[];
      connectionString?: string;
    }
  };
  backend: {
    connected: boolean;
    error?: string;
    details?: {
      version?: string;
      url?: string;
      status?: string;
    }
  };
  timestamp: string;
}

export default function AdminSystemStatus() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchSystemStatus = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/admin/system/status');
      if (!response.ok) throw new Error('Failed to fetch system status');
      const data = await response.json();
      setStatus(data);
      setError('');
    } catch (err: any) {
      setError(err.message || 'Unable to load system status');
      console.error('System status fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSystemStatus();
  }, []);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-semibold">System Status</h2>
        <Button 
          variant="outline"
          onClick={fetchSystemStatus}
          disabled={loading}
          className="border-[#e0ddd5] hover:bg-[#f5f2eb] hover:text-[#333333]"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh Status
        </Button>
      </div>

      {error && (
        <div className="bg-red-100 text-red-800 p-4 mb-4 rounded-md flex items-center">
          <AlertCircle className="mr-2 h-5 w-5" />
          {error}
        </div>
      )}

      {loading && !status ? (
        <div className="text-center py-10">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-800"></div>
          <p className="mt-2">Loading system status...</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Database Status Card */}
          <Card className={status?.database.connected ? 'border-green-200' : 'border-red-200'}>
            <CardHeader className={status?.database.connected ? 'bg-green-50' : 'bg-red-50'}>
              <div className="flex justify-between items-center">
                <CardTitle className="flex items-center">
                  <Database className="h-5 w-5 mr-2" />
                  Database Status
                </CardTitle>
                {status?.database.connected ? (
                  <CheckCircle className="h-6 w-6 text-green-600" />
                ) : (
                  <XCircle className="h-6 w-6 text-red-600" />
                )}
              </div>
              <CardDescription>
                MongoDB Database Connection Status
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              {status?.database.connected ? (
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="font-medium">Connection Status:</span>
                    <span className="text-green-600">Connected</span>
                  </div>
                  {status.database.details?.version && (
                    <div className="flex justify-between">
                      <span className="font-medium">Database Version:</span>
                      <span>{status.database.details.version}</span>
                    </div>
                  )}
                  {status.database.details?.collections && (
                    <div className="flex justify-between">
                      <span className="font-medium">Collections Count:</span>
                      <span>{status.database.details.collections.length}</span>
                    </div>
                  )}
                  <div className="mt-4">
                    <h4 className="font-medium mb-2">Collections List:</h4>
                    <ul className="list-disc list-inside space-y-1 text-sm">
                      {status.database.details?.collections?.map((collection, index) => (
                        <li key={index}>{collection}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              ) : (
                <div className="bg-red-50 p-4 rounded-md text-red-800">
                  <div className="font-medium mb-2">Connection Error:</div>
                  <div>{status?.database.error || 'Unable to connect to database'}</div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Python Backend Status Card */}
          <Card className={status?.backend.connected ? 'border-green-200' : 'border-red-200'}>
            <CardHeader className={status?.backend.connected ? 'bg-green-50' : 'bg-red-50'}>
              <div className="flex justify-between items-center">
                <CardTitle className="flex items-center">
                  <Server className="h-5 w-5 mr-2" />
                  Python Backend Status
                </CardTitle>
                {status?.backend.connected ? (
                  <CheckCircle className="h-6 w-6 text-green-600" />
                ) : (
                  <XCircle className="h-6 w-6 text-red-600" />
                )}
              </div>
              <CardDescription>
                Python API Service Connection Status
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
              {status?.backend.connected ? (
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="font-medium">Connection Status:</span>
                    <span className="text-green-600">Connected</span>
                  </div>
                  {status.backend.details?.version && (
                    <div className="flex justify-between">
                      <span className="font-medium">API Version:</span>
                      <span>{status.backend.details.version}</span>
                    </div>
                  )}
                  {status.backend.details?.url && (
                    <div className="flex justify-between">
                      <span className="font-medium">API URL:</span>
                      <span className="font-mono text-sm">{status.backend.details.url}</span>
                    </div>
                  )}
                  {status.backend.details?.status && (
                    <div className="flex justify-between">
                      <span className="font-medium">Status Message:</span>
                      <span>{status.backend.details.status}</span>
                    </div>
                  )}
                </div>
              ) : (
                <div className="bg-red-50 p-4 rounded-md text-red-800">
                  <div className="font-medium mb-2">Connection Error:</div>
                  <div>{status?.backend.error || 'Unable to connect to Python backend'}</div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {status && (
        <div className="text-right text-sm text-gray-500 mt-4">
          Last Updated: {new Date(status.timestamp).toLocaleString('en-US')}
        </div>
      )}
    </div>
  );
} 