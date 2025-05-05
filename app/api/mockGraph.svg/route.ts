import { NextResponse } from "next/server"

export async function GET() {
  // Create a more elegant SVG graph
  const svg = `
    <svg width="200" height="100" viewBox="0 0 200 100" xmlns="http://www.w3.org/2000/svg">
      <rect width="200" height="100" fill="#000000" />
      <path d="M0,50 Q50,20 100,50 T200,50" stroke="#ffffff" stroke-width="0.5" fill="none" />
      <path d="M0,70 Q50,40 100,70 T200,70" stroke="#2563EB" stroke-width="0.5" fill="none" />
      <circle cx="50" cy="30" r="2" fill="#ffffff" />
      <circle cx="100" cy="50" r="2" fill="#ffffff" />
      <circle cx="150" cy="30" r="2" fill="#ffffff" />
      <circle cx="50" cy="70" r="2" fill="#2563EB" />
      <circle cx="100" cy="70" r="2" fill="#2563EB" />
      <circle cx="150" cy="70" r="2" fill="#2563EB" />
    </svg>
  `

  return new NextResponse(svg, {
    headers: {
      "Content-Type": "image/svg+xml",
    },
  })
}
