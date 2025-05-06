'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function LogoutPage() {
  const router = useRouter();

  useEffect(() => {
    // Call the logout API endpoint
    fetch('/api/admin/logout')
      .then(() => {
        // Redirect to login page after successful logout
        router.push('/admin/login');
      })
      .catch((error) => {
        console.error('Logout error:', error);
        // Redirect to login page even if there's an error
        router.push('/admin/login');
      });
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#f5f2eb]">
      <div className="text-center">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-800 mb-4"></div>
        <p>Logging out...</p>
      </div>
    </div>
  );
} 