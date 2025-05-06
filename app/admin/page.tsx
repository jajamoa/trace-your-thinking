import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { redirect } from 'next/navigation';
import { cookies } from 'next/headers';
import dynamic from 'next/dynamic';

// Dynamically import client components without ssr: false
const AdminSessions = dynamic(() => import('@/components/admin/AdminSessions'));
const AdminQuestions = dynamic(() => import('@/components/admin/AdminQuestions'));
const AdminSystemStatus = dynamic(() => import('@/components/admin/AdminSystemStatus'));

export default async function AdminPage() {
  // Simple cookie check for server rendering
  // This is a simplification but works for admin page protection
  const cookieStore = await cookies();
  const adminCookie = cookieStore.get('admin_authenticated');
  const isAuthenticated = adminCookie?.value === 'true';
  
  // If not authenticated, redirect to login page
  if (!isAuthenticated) {
    redirect('/admin/login');
  }

  return (
    <div className="container mx-auto p-6 max-w-7xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">Admin Control Panel</h1>
        <a 
          href="/admin/logout" 
          className="bg-[#333333] hover:bg-[#222222] text-white px-4 py-2 rounded-md transition-colors"
        >
          Logout
        </a>
      </div>
      
      <Tabs defaultValue="sessions" className="w-full">
        <TabsList className="grid w-full grid-cols-3 mb-8 bg-[#f5f2eb] rounded-md">
          <TabsTrigger 
            value="sessions"
            className="data-[state=active]:bg-[#333333] data-[state=active]:text-white"
          >
            Session Management
          </TabsTrigger>
          <TabsTrigger 
            value="questions"
            className="data-[state=active]:bg-[#333333] data-[state=active]:text-white"
          >
            Guiding Questions
          </TabsTrigger>
          <TabsTrigger 
            value="system"
            className="data-[state=active]:bg-[#333333] data-[state=active]:text-white"
          >
            System Status
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="sessions" className="bg-white rounded-lg p-6 shadow-sm">
          <AdminSessions />
        </TabsContent>
        
        <TabsContent value="questions" className="bg-white rounded-lg p-6 shadow-sm">
          <AdminQuestions />
        </TabsContent>
        
        <TabsContent value="system" className="bg-white rounded-lg p-6 shadow-sm">
          <AdminSystemStatus />
        </TabsContent>
      </Tabs>
    </div>
  );
} 