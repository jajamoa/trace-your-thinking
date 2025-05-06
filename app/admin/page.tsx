import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { redirect } from 'next/navigation';
import { cookies } from 'next/headers';

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
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-800"></div>
            <p className="mt-2">Loading session data...</p>
          </div>
        </TabsContent>
        
        <TabsContent value="questions" className="bg-white rounded-lg p-6 shadow-sm">
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-800"></div>
            <p className="mt-2">Loading question data...</p>
          </div>
        </TabsContent>
        
        <TabsContent value="system" className="bg-white rounded-lg p-6 shadow-sm">
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-800"></div>
            <p className="mt-2">Loading system status...</p>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
} 