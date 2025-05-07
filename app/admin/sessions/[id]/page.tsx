'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ChevronLeft, AlertCircle, Save, FileEdit, Download, Network, FileJson } from 'lucide-react';
import { Textarea } from '@/components/ui/textarea';
import CausalGraphViewer from '@/components/admin/CausalGraphViewer';

interface QAPair {
  id: string;
  question: string;
  answer: string;
}

interface Session {
  id: string;
  prolificId: string;
  status: string;
  qaPairs: QAPair[];
  progress: {
    current: number;
    total: number;
  };
  createdAt: string;
  updatedAt: string;
  completedAt?: string;
}

// Add interface for CausalGraph
interface CausalGraph {
  _id: string;
  sessionId: string;
  prolificId: string;
  qaPairId: string;
  graphData: any;
  timestamp: string;
}

// Use search params instead of directly accessing params.id
export default function SessionDetailPage() {
  const router = useRouter();
  const [sessionId, setSessionId] = useState<string>('');
  
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [editMode, setEditMode] = useState(false);
  const [editedQAPairs, setEditedQAPairs] = useState<QAPair[]>([]);

  // Get session ID from URL
  useEffect(() => {
    // Extract session ID from URL path
    const pathSegments = window.location.pathname.split('/');
    const id = pathSegments[pathSegments.length - 1];
    if (id) {
      setSessionId(id);
    }
  }, []);

  const fetchSession = async () => {
    if (!sessionId) return;
    
    setLoading(true);
    try {
      const response = await fetch(`/api/admin/sessions/${sessionId}`);
      if (!response.ok) throw new Error('Failed to fetch session data');
      const data = await response.json();
      setSession(data.session);
      setEditedQAPairs(data.session.qaPairs);
    } catch (err: any) {
      setError(err.message || 'Unable to load session data');
      console.error('Session fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (sessionId) {
      fetchSession();
    }
  }, [sessionId]);

  const handleSaveChanges = async () => {
    try {
      const response = await fetch(`/api/admin/sessions/${sessionId}/update`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ qaPairs: editedQAPairs }),
      });

      if (!response.ok) throw new Error('Failed to update session');
      
      setEditMode(false);
      await fetchSession(); // Refetch latest data
    } catch (err: any) {
      setError(err.message || 'Update failed');
      console.error('Session update error:', err);
    }
  };

  const handleAnswerChange = (pairId: string, newAnswer: string) => {
    setEditedQAPairs(prev => 
      prev.map(pair => 
        pair.id === pairId ? { ...pair, answer: newAnswer } : pair
      )
    );
  };

  // Format date
  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Not completed';
    return new Date(dateString).toLocaleString('en-US');
  };

  // Export session details as CSV
  const exportSessionDetails = () => {
    if (!session) return;

    // Session basic information
    const sessionInfo = [
      ['Session ID', session.id],
      ['Prolific ID', session.prolificId],
      ['Status', session.status],
      ['Progress', `${session.progress.current + 1}/${session.progress.total}`],
      ['Created At', formatDate(session.createdAt)],
      ['Updated At', formatDate(session.updatedAt)],
      ['Completed At', session.completedAt ? formatDate(session.completedAt) : 'Not completed'],
      [''] // Empty line separator
    ];

    // Q&A content
    const qaHeaders = ['Question Number', 'Question', 'Answer'];
    const qaRows = session.qaPairs.map((pair, index) => [
      `${index + 1}`,
      pair.question,
      pair.answer || 'No answer'
    ]);

    // Combine all rows into CSV format
    const allRows = [
      ...sessionInfo,
      qaHeaders,
      ...qaRows
    ];

    const csvContent = allRows.map(row => 
      row.map(cell => 
        // Handle cells with special characters like commas and quotes
        typeof cell === 'string' && (cell.includes(',') || cell.includes('"') || cell.includes('\n')) 
          ? `"${cell.replace(/"/g, '""')}"` 
          : cell
      ).join(',')
    ).join('\n');

    // Create Blob and download
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    
    link.setAttribute('href', url);
    link.setAttribute('download', `session-${session.id}-qa-data.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Export causal graphs as JSON
  const exportCausalGraphs = async () => {
    if (!session) return;
    
    setLoading(true);
    try {
      // Fetch causal graphs for this session
      const response = await fetch(`/api/causal-graphs?sessionId=${sessionId}`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch graphs: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Unknown error fetching graphs');
      }
      
      // If no graphs found
      if (!data.causalGraphs || data.causalGraphs.length === 0) {
        setError('No causal graphs found for this session');
        return;
      }
      
      // Create formatted JSON with session info and graphs
      const exportData = {
        sessionInfo: {
          id: session.id,
          prolificId: session.prolificId,
          status: session.status,
          createdAt: session.createdAt,
          completedAt: session.completedAt,
          updatedAt: session.updatedAt,
        },
        graphs: data.causalGraphs.map((graph: CausalGraph) => ({
          qaPairId: graph.qaPairId,
          graphData: graph.graphData,
          timestamp: graph.timestamp
        }))
      };
      
      // Create and download the JSON file
      const jsonContent = JSON.stringify(exportData, null, 2);
      const blob = new Blob([jsonContent], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      
      link.setAttribute('href', url);
      link.setAttribute('download', `session-${session.id}-causal-graphs.json`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
    } catch (err: any) {
      setError(err.message || 'Failed to export causal graphs');
      console.error('Error exporting causal graphs:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading && !session) {
    return (
      <div className="container mx-auto p-6 max-w-7xl">
        <div className="text-center py-10">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-800"></div>
          <p className="mt-2">Loading session data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 max-w-7xl">
      <div className="flex items-center mb-6">
        <Button 
          variant="ghost" 
          onClick={() => router.push('/admin')} 
          className="mr-4"
        >
          <ChevronLeft className="h-4 w-4 mr-1" />
          Back
        </Button>
        <h1 className="text-3xl font-bold">Session Details</h1>
      </div>
      
      {error && (
        <div className="bg-red-100 text-red-800 p-4 mb-4 rounded-md flex items-center">
          <AlertCircle className="mr-2 h-5 w-5" />
          {error}
        </div>
      )}

      {session && (
        <>
          {/* Session Information Card */}
          <Card className="mb-6 border border-[#e0ddd5]">
            <CardHeader>
              <CardTitle>Session Information</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p><strong>Session ID:</strong> {session.id}</p>
                  <p><strong>Prolific ID:</strong> {session.prolificId}</p>
                  <p><strong>Status:</strong> {session.status}</p>
                </div>
                <div>
                  <p><strong>Progress:</strong> {session.progress.current + 1} / {session.progress.total}</p>
                  <p><strong>Created At:</strong> {formatDate(session.createdAt)}</p>
                  <p><strong>Completed At:</strong> {formatDate(session.completedAt)}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Q&A Content */}
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-semibold">Q&A Content</h2>
            <div className="flex space-x-2">
              <Button 
                variant="outline" 
                onClick={exportSessionDetails}
                disabled={loading}
              >
                <Download className="h-4 w-4 mr-2" />
                Export QA Data
              </Button>
              <Button 
                variant="outline" 
                onClick={exportCausalGraphs}
                disabled={loading}
              >
                <FileJson className="h-4 w-4 mr-2" />
                Export All Graphs
              </Button>
              <Button 
                variant={editMode ? "default" : "outline"} 
                onClick={() => setEditMode(!editMode)}
                className={editMode ? "bg-[#333333] hover:bg-[#222222]" : ""}
              >
                {editMode ? (
                  <>
                    <Save className="h-4 w-4 mr-2" />
                    Finish Editing
                  </>
                ) : (
                  <>
                    <FileEdit className="h-4 w-4 mr-2" />
                    Edit Answers
                  </>
                )}
              </Button>
            </div>
          </div>

          {editMode && (
            <div className="bg-yellow-50 border border-yellow-200 p-4 mb-4 rounded-md">
              <p className="text-sm text-yellow-800">
                You are now in edit mode. After modifying any answers, click the "Save Changes" button to save your edits.
              </p>
            </div>
          )}

          <Tabs defaultValue="qa" className="w-full">
            <TabsList className="mb-4 bg-[#f5f2eb]">
              <TabsTrigger 
                value="qa"
                className="data-[state=active]:bg-[#333333] data-[state=active]:text-white"
              >
                Q&A List
              </TabsTrigger>
              <TabsTrigger 
                value="graphs"
                className="data-[state=active]:bg-[#333333] data-[state=active]:text-white"
              >
                <Network className="h-4 w-4 mr-2" />
                Causal Graphs
              </TabsTrigger>
            </TabsList>
            
            <TabsContent value="qa">
              {session.qaPairs.length === 0 ? (
                <div className="text-center py-10 text-gray-500">
                  This session has no Q&A data
                </div>
              ) : (
                <div className="space-y-6">
                  {(editMode ? editedQAPairs : session.qaPairs).map((pair, index) => (
                    <Card key={pair.id} className="overflow-hidden border border-[#e0ddd5]">
                      <CardHeader className="bg-blue-50 py-3">
                        <CardTitle className="text-lg flex items-center">
                          <span className="bg-blue-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm mr-2">
                            Q
                          </span>
                          Question {index + 1}
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="pt-4">
                        <p className="mb-4">{pair.question}</p>
                        <div className="mt-4">
                          <div className="flex items-center mb-2">
                            <span className="bg-green-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm mr-2">
                              A
                            </span>
                            <h4 className="font-medium">Answer:</h4>
                          </div>
                          {editMode ? (
                            <Textarea
                              value={pair.answer}
                              onChange={(e) => handleAnswerChange(pair.id, e.target.value)}
                              rows={6}
                              className="w-full bg-[#f5f2eb] border-[#e0ddd5] focus:ring-blue-400"
                            />
                          ) : (
                            <div className="bg-gray-50 p-4 rounded-md">
                              {pair.answer || <span className="text-gray-400">(No answer)</span>}
                            </div>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  ))}

                  {editMode && (
                    <div className="flex justify-end mt-4">
                      <Button 
                        variant="outline" 
                        onClick={() => setEditMode(false)} 
                        className="mr-2"
                      >
                        Cancel
                      </Button>
                      <Button 
                        onClick={handleSaveChanges}
                        className="bg-[#333333] hover:bg-[#222222]"
                      >
                        Save Changes
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </TabsContent>
            
            <TabsContent value="graphs">
              <div className="mb-4">
                <h3 className="text-lg font-semibold mb-1">Causal Graph Visualization</h3>
                <p className="text-sm text-gray-500">
                  This visualization shows the causal graphs generated from user responses. 
                  Navigate between graphs to see how the model evolves with each question.
                </p>
              </div>
              
              <CausalGraphViewer sessionId={sessionId} className="mt-6 bg-white p-4 rounded-md border border-[#e0ddd5]" />
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  );
} 