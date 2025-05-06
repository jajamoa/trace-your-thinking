'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ChevronLeft, AlertCircle, Save, FileEdit } from 'lucide-react';
import { Textarea } from '@/components/ui/textarea';

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

export default function SessionDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const sessionId = params.id;
  
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [editMode, setEditMode] = useState(false);
  const [editedQAPairs, setEditedQAPairs] = useState<QAPair[]>([]);

  const fetchSession = async () => {
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
    fetchSession();
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
                  <p><strong>Progress:</strong> {session.progress.current} / {session.progress.total}</p>
                  <p><strong>Created At:</strong> {formatDate(session.createdAt)}</p>
                  <p><strong>Completed At:</strong> {formatDate(session.completedAt)}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Q&A Content */}
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-semibold">Q&A Content</h2>
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
          </Tabs>
        </>
      )}
    </div>
  );
} 