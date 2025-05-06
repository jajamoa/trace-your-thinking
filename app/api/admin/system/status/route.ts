import { NextRequest, NextResponse } from 'next/server';
import mongoose from 'mongoose';
import connectToDatabase from '@/lib/mongodb';

// Check MongoDB connection status
async function checkDatabaseStatus() {
  const result = {
    connected: false,
    error: '',
    details: {
      version: '',
      collections: [] as string[],
      connectionString: ''
    }
  };

  try {
    await connectToDatabase();
    
    // Check connection state
    result.connected = mongoose.connection.readyState === 1;
    
    if (result.connected && mongoose.connection.db) {
      try {
        // Get database version and collections
        const admin = mongoose.connection.db.admin();
        const serverStatus = await admin.serverStatus();
        result.details.version = serverStatus.version;
        
        // Get collections list
        const collections = await mongoose.connection.db.listCollections().toArray();
        result.details.collections = collections.map(c => c.name);
        
        // Hide sensitive info in connection string
        const mongooseAny = mongoose as any;
        if (mongooseAny.connection && mongooseAny.connection.client && mongooseAny.connection.client.s) {
          const connStr = mongooseAny.connection.client.s.url;
          result.details.connectionString = connStr.replace(/(mongodb:\/\/[^:]+):([^@]+)@/, '$1:****@');
        }
      } catch (err) {
        console.error('Error fetching database details:', err);
      }
    }
  } catch (error: any) {
    result.error = error.message;
  }

  return result;
}

// Check Python backend API status
async function checkBackendStatus() {
  const result = {
    connected: false,
    error: '',
    details: {
      version: '',
      url: process.env.PYTHON_API_URL || 'http://localhost:5000',
      status: ''
    }
  };

  try {
    const apiUrl = process.env.PYTHON_API_URL || 'http://localhost:5000';
    const response = await fetch(`${apiUrl}/api/status`, { 
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
      cache: 'no-store'
    });
    
    if (response.ok) {
      const data = await response.json();
      result.connected = true;
      result.details.version = data.version || 'Unknown';
      result.details.status = data.status || 'Running';
    } else {
      result.error = `API returned ${response.status}: ${response.statusText}`;
    }
  } catch (error: any) {
    result.error = error.message;
  }

  return result;
}

export async function GET(request: NextRequest) {
  // Use a simpler cookie checking approach
  const cookieStr = request.cookies.toString();
  const isAuthenticated = cookieStr.includes('admin_authenticated=true');
  
  if (!isAuthenticated) {
    return NextResponse.json({ error: 'Unauthorized access' }, { status: 401 });
  }

  // Check all system statuses in parallel
  const [database, backend] = await Promise.all([
    checkDatabaseStatus(),
    checkBackendStatus()
  ]);

  return NextResponse.json({
    database,
    backend,
    timestamp: new Date().toISOString()
  });
} 