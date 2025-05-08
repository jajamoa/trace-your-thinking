import type React from "react"
import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { ThemeProvider } from "@/components/theme-provider"
import SessionCheck from "@/components/SessionCheck"

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
})

// Get the research topic from environment variable
const researchTopic = process.env.NEXT_PUBLIC_RESEARCH_TOPIC || "general";

export const metadata: Metadata = {
  title: `Trace Your Thinking${researchTopic !== "general" ? ` - ${researchTopic.charAt(0).toUpperCase() + researchTopic.slice(1)}` : ""}`,
  description: "A sophisticated interview collection and analysis tool for research studies",
  generator: 'Next.js',
  metadataBase: new URL(process.env.NEXT_PUBLIC_BASE_URL || 'https://trace-your-thinking.com'),
  icons: {
    icon: [
      { url: '/favicon.ico' },
      { url: '/icon.png', type: 'image/png' },
    ],
    apple: [
      { url: '/apple-touch-icon.png' },
    ],
  },
  openGraph: {
    title: `Trace Your Thinking${researchTopic !== "general" ? ` - ${researchTopic.charAt(0).toUpperCase() + researchTopic.slice(1)}` : ""}`,
    description: 'A sophisticated interview collection and analysis tool for research studies',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'Trace Your Thinking',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: `Trace Your Thinking${researchTopic !== "general" ? ` - ${researchTopic.charAt(0).toUpperCase() + researchTopic.slice(1)}` : ""}`,
    description: 'A sophisticated interview collection and analysis tool for research studies',
    images: ['/og-image.png'],
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Force visibility script to prevent blank page issues */}
        <script 
          dangerouslySetInnerHTML={{ 
            __html: `
              // Force content visibility after a delay
              setTimeout(function() {
                document.body.style.visibility = 'visible';
                var elements = document.querySelectorAll('div, main, section');
                elements.forEach(function(el) {
                  el.style.opacity = '1';
                  el.style.transform = 'none';
                });
              }, 2000);
            `
          }}
        />
      </head>
      <body className={`${inter.variable} font-sans antialiased bg-[#f5f2eb] text-[#333333] min-h-screen`}>
        <noscript>
          <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            backgroundColor: '#f44336',
            color: 'white',
            textAlign: 'center',
            padding: '1rem',
            zIndex: 9999,
          }}>
            This application requires JavaScript to be enabled. Please enable JavaScript and reload the page.
          </div>
        </noscript>
        
        <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
          {/* Global session state checker */}
          <SessionCheck />
          {children}
        </ThemeProvider>
      </body>
    </html>
  )
}
