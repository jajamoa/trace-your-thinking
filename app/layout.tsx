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

export const metadata: Metadata = {
  title: "Trace Your Thinking",
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
    title: 'Trace Your Thinking',
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
    title: 'Trace Your Thinking',
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
      <body className={`${inter.variable} font-sans antialiased bg-[#f5f2eb] text-[#333333] min-h-screen`}>
        <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
          {/* Global session state checker */}
          <SessionCheck />
          {children}
        </ThemeProvider>
      </body>
    </html>
  )
}
