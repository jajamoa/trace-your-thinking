'use client';
import { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle, Save } from "lucide-react";

export default function AdminSettings() {
  const [defaultTopic, setDefaultTopic] = useState('policy');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Fetch current settings
  useEffect(() => {
    async function fetchSettings() {
      try {
        setLoading(true);
        const response = await fetch('/api/admin/settings');
        
        if (!response.ok) {
          throw new Error('Failed to fetch settings');
        }
        
        const data = await response.json();
        
        if (data.settings && data.settings.defaultTopic) {
          setDefaultTopic(data.settings.defaultTopic);
        }
      } catch (err: any) {
        setError('Failed to load settings: ' + (err.message || 'Unknown error'));
      } finally {
        setLoading(false);
      }
    }
    
    fetchSettings();
  }, []);

  // Save settings
  const handleSaveSettings = async () => {
    try {
      setSaving(true);
      setError('');
      setSuccess('');
      
      const response = await fetch('/api/admin/settings', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ defaultTopic }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to update settings');
      }
      
      setSuccess('Settings updated successfully!');
      
      // Hide success message after 3 seconds
      setTimeout(() => {
        setSuccess('');
      }, 3000);
    } catch (err: any) {
      setError('Failed to save settings: ' + (err.message || 'Unknown error'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <h2 className="text-2xl font-semibold mb-6">Interview Settings</h2>
      
      {error && (
        <div className="bg-red-100 text-red-800 p-4 mb-4 rounded-md flex items-center">
          <AlertCircle className="mr-2 h-5 w-5" />
          {error}
        </div>
      )}
      
      {success && (
        <div className="bg-green-100 text-green-800 p-4 mb-4 rounded-md">
          {success}
        </div>
      )}
      
      <Card>
        <CardHeader>
          <CardTitle>Global Interview Settings</CardTitle>
          <CardDescription>
            These settings apply to all new interviews. Changes will not affect existing interviews.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="defaultTopic">Default Interview Topic</Label>
              <Input
                id="defaultTopic"
                value={defaultTopic}
                onChange={(e) => setDefaultTopic(e.target.value)}
                placeholder="e.g., policy, open science, climate change"
                className="bg-[#f5f2eb] border-[#e0ddd5] focus:ring-blue-400"
                disabled={loading || saving}
              />
              <p className="text-sm text-gray-500">
                This topic will be used for all new interviews. It appears in the stance node labeled "Support for [topic]".
              </p>
            </div>
          </div>
        </CardContent>
        <CardFooter>
          <Button 
            onClick={handleSaveSettings} 
            disabled={loading || saving}
            className="bg-[#333333] hover:bg-[#222222]"
          >
            {saving ? (
              <>
                <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"></div>
                Saving...
              </>
            ) : (
              <>
                <Save className="mr-2 h-4 w-4" />
                Save Settings
              </>
            )}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
} 