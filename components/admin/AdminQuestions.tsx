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
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { 
  AlertCircle, 
  Plus, 
  Trash, 
  Edit, 
  ChevronUp, 
  ChevronDown, 
  Save
} from "lucide-react";

interface GuidingQuestion {
  id: string;
  text: string;
  shortText: string;
  category?: string;
  isActive: boolean;
  order: number;
  createdAt: string;
  updatedAt: string;
}

export default function AdminQuestions() {
  const [questions, setQuestions] = useState<GuidingQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [selectedQuestion, setSelectedQuestion] = useState<GuidingQuestion | null>(null);
  
  const [formData, setFormData] = useState({
    text: '',
    shortText: '',
    category: '',
    isActive: true
  });

  const fetchQuestions = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/admin/questions');
      if (!response.ok) throw new Error('Failed to fetch question data');
      const data = await response.json();
      // Sort by order
      const sortedQuestions = data.questions.sort((a: GuidingQuestion, b: GuidingQuestion) => a.order - b.order);
      setQuestions(sortedQuestions);
    } catch (err: any) {
      setError(err.message || 'Unable to load question data');
      console.error('Question fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQuestions();
  }, []);

  const handleCreateQuestion = async () => {
    try {
      const response = await fetch('/api/admin/questions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) throw new Error('Failed to create question');
      
      setIsCreateDialogOpen(false);
      resetForm();
      fetchQuestions();
    } catch (err: any) {
      setError(err.message || 'Creation failed');
      console.error('Question creation error:', err);
    }
  };

  const handleUpdateQuestion = async () => {
    if (!selectedQuestion) return;
    
    try {
      const response = await fetch(`/api/admin/questions/${selectedQuestion.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) throw new Error('Failed to update question');
      
      setIsEditDialogOpen(false);
      setSelectedQuestion(null);
      resetForm();
      fetchQuestions();
    } catch (err: any) {
      setError(err.message || 'Update failed');
      console.error('Question update error:', err);
    }
  };

  const handleDeleteQuestion = async () => {
    if (!selectedQuestion) return;
    
    try {
      const response = await fetch(`/api/admin/questions/${selectedQuestion.id}`, {
        method: 'DELETE',
      });

      if (!response.ok) throw new Error('Failed to delete question');
      
      setIsDeleteDialogOpen(false);
      setSelectedQuestion(null);
      fetchQuestions();
    } catch (err: any) {
      setError(err.message || 'Deletion failed');
      console.error('Question deletion error:', err);
    }
  };

  const handleMoveQuestion = async (id: string, direction: 'up' | 'down') => {
    const currentIndex = questions.findIndex(q => q.id === id);
    if (
      (direction === 'up' && currentIndex === 0) || 
      (direction === 'down' && currentIndex === questions.length - 1)
    ) return;

    const newIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1;
    
    try {
      const response = await fetch(`/api/admin/questions/${id}/reorder`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ newOrder: questions[newIndex].order }),
      });

      if (!response.ok) throw new Error('Failed to reorder question');
      
      fetchQuestions();
    } catch (err: any) {
      setError(err.message || 'Operation failed');
      console.error('Reorder error:', err);
    }
  };

  const resetForm = () => {
    setFormData({
      text: '',
      shortText: '',
      category: '',
      isActive: true
    });
  };

  const openEditDialog = (question: GuidingQuestion) => {
    setSelectedQuestion(question);
    setFormData({
      text: question.text,
      shortText: question.shortText,
      category: question.category || '',
      isActive: question.isActive
    });
    setIsEditDialogOpen(true);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-semibold">Guiding Questions</h2>
        <Button onClick={() => setIsCreateDialogOpen(true)} className="bg-[#333333] hover:bg-[#222222]">
          <Plus className="h-4 w-4 mr-2" />
          Add Question
        </Button>
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
      ) : questions.length === 0 ? (
        <div className="text-center py-10 text-gray-500">
          No guiding questions found
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12">Order</TableHead>
              <TableHead className="w-64">Short Text</TableHead>
              <TableHead>Full Question</TableHead>
              <TableHead>Category</TableHead>
              <TableHead className="w-20">Status</TableHead>
              <TableHead className="w-32">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {questions.map((question) => (
              <TableRow key={question.id}>
                <TableCell>
                  <div className="flex flex-col items-center">
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      className="h-6 w-6" 
                      onClick={() => handleMoveQuestion(question.id, 'up')}
                      disabled={questions.indexOf(question) === 0}
                    >
                      <ChevronUp className="h-4 w-4" />
                    </Button>
                    <span className="mx-2">{question.order + 1}</span>
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      className="h-6 w-6" 
                      onClick={() => handleMoveQuestion(question.id, 'down')}
                      disabled={questions.indexOf(question) === questions.length - 1}
                    >
                      <ChevronDown className="h-4 w-4" />
                    </Button>
                  </div>
                </TableCell>
                <TableCell>{question.shortText}</TableCell>
                <TableCell className="max-w-md truncate">{question.text}</TableCell>
                <TableCell>{question.category || '-'}</TableCell>
                <TableCell>
                  <Switch 
                    checked={question.isActive} 
                    onCheckedChange={async (checked) => {
                      setSelectedQuestion(question);
                      setFormData({
                        ...formData,
                        text: question.text,
                        shortText: question.shortText,
                        category: question.category || '',
                        isActive: checked
                      });
                      await handleUpdateQuestion();
                    }}
                  />
                </TableCell>
                <TableCell>
                  <div className="flex space-x-1">
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      onClick={() => openEditDialog(question)}
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      onClick={() => {
                        setSelectedQuestion(question);
                        setIsDeleteDialogOpen(true);
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

      {/* Create Question Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>Add New Question</DialogTitle>
            <DialogDescription>
              Add a new guiding question for respondents to answer.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="shortText">Short Question Description</Label>
              <Input
                id="shortText"
                value={formData.shortText}
                onChange={(e) => setFormData({ ...formData, shortText: e.target.value })}
                placeholder="Short description (for tabs, etc.)"
                className="bg-[#f5f2eb] border-[#e0ddd5] focus:ring-blue-400"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="text">Full Question Text</Label>
              <Textarea
                id="text"
                value={formData.text}
                onChange={(e) => setFormData({ ...formData, text: e.target.value })}
                placeholder="Detailed question content"
                rows={4}
                className="bg-[#f5f2eb] border-[#e0ddd5] focus:ring-blue-400"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="category">Category (Optional)</Label>
              <Input
                id="category"
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                placeholder="Question category"
                className="bg-[#f5f2eb] border-[#e0ddd5] focus:ring-blue-400"
              />
            </div>
            <div className="flex items-center space-x-2">
              <Switch
                id="isActive"
                checked={formData.isActive}
                onCheckedChange={(checked) => setFormData({ ...formData, isActive: checked })}
              />
              <Label htmlFor="isActive">Enable this question</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateQuestion} className="bg-[#333333] hover:bg-[#222222]">
              <Save className="h-4 w-4 mr-2" />
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Question Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>Edit Question</DialogTitle>
            <DialogDescription>
              Modify the existing guiding question.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="shortText">Short Question Description</Label>
              <Input
                id="shortText"
                value={formData.shortText}
                onChange={(e) => setFormData({ ...formData, shortText: e.target.value })}
                className="bg-[#f5f2eb] border-[#e0ddd5] focus:ring-blue-400"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="text">Full Question Text</Label>
              <Textarea
                id="text"
                value={formData.text}
                onChange={(e) => setFormData({ ...formData, text: e.target.value })}
                rows={4}
                className="bg-[#f5f2eb] border-[#e0ddd5] focus:ring-blue-400"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="category">Category (Optional)</Label>
              <Input
                id="category"
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                className="bg-[#f5f2eb] border-[#e0ddd5] focus:ring-blue-400"
              />
            </div>
            <div className="flex items-center space-x-2">
              <Switch
                id="isActive"
                checked={formData.isActive}
                onCheckedChange={(checked) => setFormData({ ...formData, isActive: checked })}
              />
              <Label htmlFor="isActive">Enable this question</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleUpdateQuestion} className="bg-[#333333] hover:bg-[#222222]">
              <Save className="h-4 w-4 mr-2" />
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Question</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this question? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          
          {selectedQuestion && (
            <div className="py-4">
              <p><strong>Question:</strong> {selectedQuestion.shortText}</p>
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDeleteQuestion}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
} 