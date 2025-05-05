import { NextResponse } from "next/server"

export async function POST() {
  // Simulate a successful submission
  return NextResponse.json({ ok: true })
}
