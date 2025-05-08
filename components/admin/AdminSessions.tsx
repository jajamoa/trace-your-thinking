'use client';
import { useState, useEffect, useRef } from 'react';
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
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AlertCircle, CheckCircle, Trash, Search, RefreshCw, Edit, Copy, MoveHorizontal, Download, FileJson, Network, ChevronLeft, ChevronRight } from "lucide-react";
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
  order?: number; // For drag-and-drop ordering
}

interface PaginationInfo {
  currentPage: number;
  totalPages: number;
  totalItems: number;
  itemsPerPage: number;
}

export default function AdminSessions() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [confirmSession, setConfirmSession] = useState<Session | null>(null);
  const [actionType, setActionType] = useState<'delete' | 'reset' | 'complete' | null>(null);
  const [draggingSession, setDraggingSession] = useState<Session | null>(null);
  const [dragOverSession, setDragOverSession] = useState<Session | null>(null);
  const [showOrderControls, setShowOrderControls] = useState(false);
  // Pagination states
  const [pagination, setPagination] = useState<PaginationInfo>({
    currentPage: 1,
    totalPages: 1,
    totalItems: 0,
    itemsPerPage: 30
  });

  const fetchSessions = async (page = 1) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/admin/sessions?page=${page}&limit=${pagination.itemsPerPage}`);
      if (!response.ok) throw new Error('Failed to fetch session data');
      const data = await response.json();
      
      // Add order property to sessions if not already present
      const orderedSessions = data.sessions.map((session: Session, index: number) => ({
        ...session,
        order: session.order || index
      }));
      
      setSessions(orderedSessions);
      setPagination({
        ...pagination,
        currentPage: data.pagination.currentPage,
        totalPages: data.pagination.totalPages,
        totalItems: data.pagination.totalItems
      });
    } catch (err: any) {
      setError(err.message || 'Unable to load session data');
      console.error('Session fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions(pagination.currentPage);
  }, [pagination.currentPage, pagination.itemsPerPage]);

  const handleAction = async () => {
    if (!confirmSession || !actionType) return;
    
    try {
      const endpoint = `/api/admin/sessions/${confirmSession.id}/${actionType}`;
      const response = await fetch(endpoint, { method: 'POST' });
      
      if (!response.ok) throw new Error(`Operation failed: ${actionType}`);
      
      await fetchSessions(pagination.currentPage); // Refetch sessions list
      setConfirmSession(null);
      setActionType(null);
    } catch (err: any) {
      setError(err.message || 'Operation failed');
      console.error('Session action error:', err);
    }
  };

  // Go to specific page
  const goToPage = (page: number) => {
    if (page < 1 || page > pagination.totalPages) return;
    setPagination(prev => ({...prev, currentPage: page}));
  };

  // Filter sessions handled on server-side with pagination,
  // but we still need local filtering for search functionality
  const filteredSessions = searchTerm ? sessions.filter(session => {
    return session.id.includes(searchTerm) || 
           session.prolificId.includes(searchTerm) ||
           session.status.includes(searchTerm);
  }).sort((a, b) => (a.order || 0) - (b.order || 0)) : sessions;

  // Handle search with debounce
  const handleSearch = (value: string) => {
    setSearchTerm(value);
    if (!value) {
      // If search is cleared, reset to first page
      setPagination(prev => ({...prev, currentPage: 1}));
      fetchSessions(1);
    }
  };

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

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
      .then(() => {
        // Could show a toast notification here
        console.log('Copied to clipboard');
      })
      .catch(err => {
        console.error('Failed to copy: ', err);
      });
  };

  // Drag and drop handlers
  const handleDragStart = (session: Session) => {
    setDraggingSession(session);
  };

  const handleDragOver = (e: React.DragEvent, session: Session) => {
    e.preventDefault();
    if (draggingSession?.id !== session.id) {
      setDragOverSession(session);
    }
  };

  const handleDrop = async (e: React.DragEvent, targetSession: Session) => {
    e.preventDefault();
    if (!draggingSession || draggingSession.id === targetSession.id) return;

    // Update the order in UI immediately
    const updatedSessions = [...sessions];
    const sourceIndex = updatedSessions.findIndex(s => s.id === draggingSession.id);
    const targetIndex = updatedSessions.findIndex(s => s.id === targetSession.id);
    
    if (sourceIndex !== -1 && targetIndex !== -1) {
      // Remove the source session
      const [movedSession] = updatedSessions.splice(sourceIndex, 1);
      // Insert it at the target position
      updatedSessions.splice(targetIndex, 0, movedSession);
      
      // Update order values
      const reorderedSessions = updatedSessions.map((session, index) => ({
        ...session,
        order: index
      }));
      
      setSessions(reorderedSessions);
      
      // Persist the order change via API
      try {
        const response = await fetch('/api/admin/sessions/reorder', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ sessions: reorderedSessions }),
        });
        
        if (!response.ok) {
          throw new Error('Failed to persist session order');
        }
      } catch (err) {
        console.error('Failed to save session order:', err);
        // Could add error state or toast notification here
      }
    }
    
    setDraggingSession(null);
    setDragOverSession(null);
  };

  const handleDragEnd = () => {
    setDraggingSession(null);
    setDragOverSession(null);
  };

  // Export all sessions QA data as JSON file
  const exportSessionsAsJson = async () => {
    if (filteredSessions.length === 0) return;
    
    setLoading(true);
    
    try {
      // Get complete data for each session (including QA pairs)
      const sessionsData = await Promise.all(
        filteredSessions.map(async (session) => {
          try {
            const response = await fetch(`/api/admin/sessions/${session.id}`);
            if (!response.ok) throw new Error(`Failed to fetch session ${session.id}`);
            const data = await response.json();
            return data.session;
          } catch (error) {
            console.error(`Error fetching session ${session.id}:`, error);
            // Return original session data instead of complete data
            return session;
          }
        })
      );
      
      // Create and download JSON file
      const jsonContent = JSON.stringify(sessionsData, null, 2);
      const blob = new Blob([jsonContent], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      
      link.setAttribute('href', url);
      link.setAttribute('download', `all-sessions-qa-data-${timestamp}.json`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error('Failed to export sessions:', error);
      setError('Failed to export sessions data');
    } finally {
      setLoading(false);
    }
  };

  // Export all causal graphs data as JSON file
  const exportAllCausalGraphs = async () => {
    if (filteredSessions.length === 0) return;
    
    setLoading(true);
    
    try {
      // Get causal graphs for each session
      const graphsData = await Promise.all(
        filteredSessions.map(async (session) => {
          try {
            const response = await fetch(`/api/causal-graphs?sessionId=${session.id}`);
            if (!response.ok) throw new Error(`Failed to fetch graphs for session ${session.id}`);
            const data = await response.json();
            
            return {
              sessionId: session.id,
              prolificId: session.prolificId,
              status: session.status,
              graphs: data.causalGraphs || []
            };
          } catch (error) {
            console.error(`Error fetching graphs for session ${session.id}:`, error);
            return {
              sessionId: session.id,
              prolificId: session.prolificId,
              status: session.status,
              graphs: [],
              error: 'Failed to fetch graphs'
            };
          }
        })
      );
      
      // Create and download JSON file
      const jsonContent = JSON.stringify(graphsData, null, 2);
      const blob = new Blob([jsonContent], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      
      link.setAttribute('href', url);
      link.setAttribute('download', `all-causal-graphs-${timestamp}.json`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error('Failed to export causal graphs:', error);
      setError('Failed to export causal graphs data');
    } finally {
      setLoading(false);
    }
  };

  // Render pagination controls
  const renderPagination = () => {
    return (
      <div className="flex items-center justify-center mt-6 space-x-2">
        <Button 
          variant="outline" 
          size="sm" 
          disabled={pagination.currentPage <= 1}
          onClick={() => goToPage(pagination.currentPage - 1)}
        >
          <ChevronLeft className="h-4 w-4 mr-1" /> Previous
        </Button>
        
        <div className="flex items-center space-x-1">
          {[...Array(pagination.totalPages)].map((_, index) => {
            const pageNumber = index + 1;
            
            // Show only a window of pages around current page
            if (
              pageNumber === 1 || 
              pageNumber === pagination.totalPages ||
              (pageNumber >= pagination.currentPage - 2 && 
               pageNumber <= pagination.currentPage + 2)
            ) {
              return (
                <Button
                  key={pageNumber}
                  variant={pagination.currentPage === pageNumber ? "default" : "outline"}
                  size="sm"
                  className={pagination.currentPage === pageNumber ? "bg-[#333333]" : ""}
                  onClick={() => goToPage(pageNumber)}
                >
                  {pageNumber}
                </Button>
              );
            } else if (
              (pageNumber === pagination.currentPage - 3 && pagination.currentPage > 3) ||
              (pageNumber === pagination.currentPage + 3 && pagination.currentPage < pagination.totalPages - 2)
            ) {
              // Show ellipsis for gaps
              return <span key={pageNumber}>...</span>;
            }
            return null;
          })}
        </div>
        
        <Button 
          variant="outline" 
          size="sm" 
          disabled={pagination.currentPage >= pagination.totalPages}
          onClick={() => goToPage(pagination.currentPage + 1)}
        >
          Next <ChevronRight className="h-4 w-4 ml-1" />
        </Button>
        
        <span className="text-sm text-gray-500 ml-2">
          Page {pagination.currentPage} of {pagination.totalPages} 
          ({pagination.totalItems} total sessions)
        </span>
      </div>
    );
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center">
          <h2 className="text-2xl font-semibold">Session Management</h2>
          <Button 
            variant="ghost" 
            size="icon" 
            onClick={() => fetchSessions(pagination.currentPage)} 
            className="ml-2" 
            title="Refresh"
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowOrderControls(!showOrderControls)}
            className="ml-4"
          >
            <MoveHorizontal className="h-4 w-4 mr-2" />
            {showOrderControls ? 'Hide Order Controls' : 'Show Order Controls'}
          </Button>
          <div className="ml-4 flex space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={exportSessionsAsJson}
              disabled={filteredSessions.length === 0 || loading}
              title="Export all sessions Q&A data as JSON"
            >
              <FileJson className="h-4 w-4 mr-2" />
              Export All QAs
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={exportAllCausalGraphs}
              disabled={filteredSessions.length === 0 || loading}
              title="Export all causal graphs data as JSON"
            >
              <Network className="h-4 w-4 mr-2" />
              Export All Graphs
            </Button>
          </div>
        </div>
        <div className="relative">
          <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="Search sessions..."
            value={searchTerm}
            onChange={(e) => handleSearch(e.target.value)}
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

      {showOrderControls && (
        <div className="bg-blue-50 p-4 mb-4 rounded-md">
          <p className="text-blue-800 text-sm">
            <strong>Drag and Drop Mode Enabled:</strong> You can now drag sessions to reorder them. Drag a row and drop it in the desired position.
          </p>
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
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                {showOrderControls && <TableHead className="w-10">#</TableHead>}
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
              {filteredSessions.map((session, index) => (
                <TableRow 
                  key={session.id}
                  draggable={showOrderControls}
                  onDragStart={() => showOrderControls && handleDragStart(session)}
                  onDragOver={(e) => showOrderControls && handleDragOver(e, session)}
                  onDrop={(e) => showOrderControls && handleDrop(e, session)}
                  onDragEnd={handleDragEnd}
                  className={`
                    ${draggingSession?.id === session.id ? 'opacity-50 bg-gray-100' : ''}
                    ${dragOverSession?.id === session.id ? 'border-t-2 border-blue-500' : ''}
                    ${showOrderControls ? 'cursor-move' : ''}
                  `}
                >
                  {showOrderControls && <TableCell>{index + 1}</TableCell>}
                  <TableCell>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <div className="flex items-center">
                            <span className="font-mono">
                              {session.id.length > 15 
                                ? `${session.id.substring(0, 7)}...${session.id.substring(session.id.length - 7)}`
                                : session.id}
                            </span>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-6 w-6 ml-1"
                              onClick={() => copyToClipboard(session.id)}
                            >
                              <Copy className="h-3 w-3" />
                            </Button>
                          </div>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="font-mono">{session.id}</p>
                          <p className="text-xs mt-1">Click to copy full ID</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </TableCell>
                  <TableCell>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <div className="flex items-center">
                            <span>
                              {session.prolificId.length > 10 
                                ? `${session.prolificId.substring(0, 4)}...${session.prolificId.substring(session.prolificId.length - 4)}`
                                : session.prolificId}
                            </span>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-6 w-6 ml-1"
                              onClick={() => copyToClipboard(session.prolificId)}
                            >
                              <Copy className="h-3 w-3" />
                            </Button>
                          </div>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>{session.prolificId}</p>
                          <p className="text-xs mt-1">Click to copy full Prolific ID</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </TableCell>
                  <TableCell>{getStatusBadge(session.status)}</TableCell>
                  <TableCell>
                    {session.progress.current + 1} / {session.progress.total}
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
          
          {/* Render pagination controls */}
          {pagination.totalPages > 1 && renderPagination()}
        </div>
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
              <div className="flex items-center">
                <p><strong>Session ID:</strong></p>
                <p className="font-mono ml-2">{confirmSession.id}</p>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 ml-1"
                  onClick={() => copyToClipboard(confirmSession.id)}
                >
                  <Copy className="h-3 w-3" />
                </Button>
              </div>
              <div className="flex items-center">
                <p><strong>Prolific ID:</strong></p>
                <p className="ml-2">{confirmSession.prolificId}</p>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 ml-1"
                  onClick={() => copyToClipboard(confirmSession.prolificId)}
                >
                  <Copy className="h-3 w-3" />
                </Button>
              </div>
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