'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertCircle } from 'lucide-react';

export default function AdminLoginPage() {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const response = await fetch('/api/admin/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ password }),
      });

      if (response.ok) {
        router.push('/admin');
        router.refresh();
      } else {
        const data = await response.json();
        setError(data.error || 'Login failed, please try again');
      }
    } catch (err) {
      setError('An error occurred, please try again');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#f5f2eb]">
      <Card className="w-[350px] border border-[#e0ddd5] shadow-subtle">
        <CardHeader>
          <CardTitle className="text-2xl font-light">Admin Login</CardTitle>
          <CardDescription>
            Please enter the admin password to continue
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent>
            <div className="grid w-full items-center gap-4">
              <Input
                id="password"
                type="password"
                placeholder="Enter password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="bg-[#f5f2eb] border-[#e0ddd5] focus:ring-blue-400"
              />
              {error && (
                <div className="flex items-center gap-2 text-red-500 text-sm mt-1">
                  <AlertCircle className="h-4 w-4" />
                  <span>{error}</span>
                </div>
              )}
            </div>
          </CardContent>
          <CardFooter className="flex justify-end">
            <Button 
              type="submit" 
              disabled={isLoading}
              className="bg-[#333333] hover:bg-[#222222] text-white transition-colors"
            >
              {isLoading ? 'Logging in...' : 'Login'}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
} 