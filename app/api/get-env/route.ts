import { NextResponse } from 'next/server';

/**
 * GET handler for /api/get-env endpoint
 * Returns selected environment variables that are safe to expose to the client
 * Only returns variables that are explicitly allowed in this function
 */
export async function GET() {
  // Only expose specific environment variables that are safe for the client
  const safeEnvVars = {
    // Prolific completion URL for redirecting users back to Prolific
    PROLIFIC_COMPLETION_URL: process.env.PROLIFIC_COMPLETION_URL || null,
  };

  return NextResponse.json(safeEnvVars, { status: 200 });
} 