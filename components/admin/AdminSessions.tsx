'use client';
import { useState, useEffect } from 'react';
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogHeader, 
  DialogTitle, 
  DialogFooter 
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AlertCircle, CheckCircle, Trash, Search, RefreshCw, Edit } from "lucide-react";
import Link from 'next/link';

type SessionStatus = 'in_progress' | 'completed' | 'abandoned';

interface Session {
  id: string;
  prolificId: string;
  status: SessionStatus;
  progress: {
    current: number;
    total: number;
  };
  createdAt: string;
  updatedAt: string;
  completedAt?: string;
}

export default function AdminSessions() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [confirmSession, setConfirmSession] = useState<Session | null>(null);
  const [actionType, setActionType] = useState<'delete' | 'reset' | 'complete' | null>(null);

  const fetchSessions = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/admin/sessions');
      if (!response.ok) throw new Error('Failed to fetch session data');
      const data = await response.json();
      setSessions(data.sessions);
    } catch (err: any) {
      setError(err.message || 'Unable to load session data');
      console.error('Session fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  const handleAction = async () => {
    if (!confirmSession || !actionType) return;
    
    try {
      const endpoint = `/api/admin/sessions/${confirmSession.id}/${actionType}`;
      const response = await fetch(endpoint, { method: 'POST' });
      
      if (!response.ok) throw new Error(`Operation failed: ${actionType}`);
      
      await fetchSessions(); // Refetch sessions list
      setConfirmSession(null);
      setActionType(null);
    } catch (err: any) {
      setError(err.message || 'Operation failed');
      console.error('Session action error:', err);
    }
  };

  // Filter sessions
  const filteredSessions = sessions.filter(session => {
    return session.id.includes(searchTerm) || 
           session.prolificId.includes(searchTerm) ||
           session.status.includes(searchTerm);
  });

  const getStatusBadge = (status: SessionStatus) => {
    switch(status) {
      case 'in_progress':
        return <Badge variant="outline" className="bg-blue-100 text-blue-800">In Progress</Badge>;
      case 'completed':
        return <Badge variant="outline" className="bg-green-100 text-green-800">Completed</Badge>;
      case 'abandoned':
        return <Badge variant="outline" className="bg-red-100 text-red-800">Abandoned</Badge>;
      default:
        return <Badge variant="outline">Unknown</Badge>;
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US');
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center">
          <h2 className="text-2xl font-semibold">Session Management</h2>
          <Button 
            variant="ghost" 
            size="icon" 
            onClick={fetchSessions} 
            className="ml-2" 
            title="Refresh"
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
        <div className="relative">
          <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="Search sessions..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-8 w-64 bg-[#f5f2eb] border-[#e0ddd5] focus:ring-blue-400"
          />
        </div>
      </div>

      {error && (
        <div className="bg-red-100 text-red-800 p-4 mb-4 rounded-md flex items-center">
          <AlertCircle className="mr-2 h-5 w-5" />
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-center py-10">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-800"></div>
          <p className="mt-2">Loading...</p>
        </div>
      ) : filteredSessions.length === 0 ? (
        <div className="text-center py-10 text-gray-500">
          {searchTerm ? 'No matching sessions' : 'No session data available'}
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>ID</TableHead>
              <TableHead>Prolific ID</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Progress</TableHead>
              <TableHead>Created At</TableHead>
              <TableHead>Updated At</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredSessions.map((session) => (
              <TableRow key={session.id}>
                <TableCell className="font-mono">{session.id.substring(0, 8)}...</TableCell>
                <TableCell>{session.prolificId}</TableCell>
                <TableCell>{getStatusBadge(session.status)}</TableCell>
                <TableCell>
                  {session.progress.current} / {session.progress.total}
                </TableCell>
                <TableCell>{formatDate(session.createdAt)}</TableCell>
                <TableCell>{formatDate(session.updatedAt)}</TableCell>
                <TableCell>
                  <div className="flex space-x-1">
                    <Button 
                      variant="ghost" 
                      size="icon"
                      asChild
                    >
                      <Link href={`/admin/sessions/${session.id}`}>
                        <Edit className="h-4 w-4" />
                      </Link>
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      onClick={() => {
                        setConfirmSession(session);
                        setActionType('reset');
                      }}
                    >
                      <RefreshCw className="h-4 w-4" />
                    </Button>
                    {session.status !== 'completed' && (
                      <Button 
                        variant="ghost" 
                        size="icon" 
                        onClick={() => {
                          setConfirmSession(session);
                          setActionType('complete');
                        }}
                      >
                        <CheckCircle className="h-4 w-4" />
                      </Button>
                    )}
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      onClick={() => {
                        setConfirmSession(session);
                        setActionType('delete');
                      }}
                    >
                      <Trash className="h-4 w-4" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {/* Confirmation Dialog */}
      <Dialog open={!!confirmSession} onOpenChange={(open) => !open && setConfirmSession(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {actionType === 'delete' ? 'Delete Session' : 
               actionType === 'reset' ? 'Reset Session' : 
               actionType === 'complete' ? 'Complete Session' : 'Confirm Action'}
            </DialogTitle>
            <DialogDescription>
              {actionType === 'delete' && 'This action will permanently delete the session and all its data. This cannot be undone.'}
              {actionType === 'reset' && 'This action will reset the session to its initial state. All progress will be cleared.'}
              {actionType === 'complete' && 'This action will mark the session as completed.'}
            </DialogDescription>
          </DialogHeader>
          
          {confirmSession && (
            <div className="py-4">
              <p><strong>Session ID:</strong> {confirmSession.id}</p>
              <p><strong>Prolific ID:</strong> {confirmSession.prolificId}</p>
              <p><strong>Current Status:</strong> {confirmSession.status}</p>
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmSession(null)}>
              Cancel
            </Button>
            <Button 
              variant={actionType === 'delete' ? 'destructive' : 'default'}
              onClick={handleAction}
              className={actionType !== 'delete' ? "bg-[#333333] hover:bg-[#222222]" : ""}
            >
              {actionType === 'delete' ? 'Delete' : actionType === 'reset' ? 'Reset' : 'Complete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
} 