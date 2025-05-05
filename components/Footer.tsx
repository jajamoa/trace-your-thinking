"use client"

import { useMemo } from "react"
import Link from "next/link"

interface FooterProps {
  showLogo?: boolean
  showAboutLink?: boolean
}

export default function Footer({ showLogo = true, showAboutLink = false }: FooterProps) {
  // Get current year
  const currentYear = useMemo(() => new Date().getFullYear(), [])
  
  return (
    <footer className="absolute bottom-0 left-0 right-0 p-4 text-xs text-gray-500 flex justify-between items-center z-10">
      <div className="flex items-center gap-2">
        <span>© {currentYear} MIT · COUHES Protocol E-6512</span>
        {showAboutLink && (
          <>
            <span className="mx-1">·</span>
            <Link 
              href="/about" 
              className="text-blue-500 hover:text-blue-600 hover:underline transition-colors cursor-pointer" 
              prefetch={true}
            >
              About this study →
            </Link>
          </>
        )}
      </div>
      {showLogo && (
        <div className="opacity-70 hover:opacity-100 transition-opacity">
          <img
            src="/mit-logo.svg"
            alt="MIT Logo"
            className="h-6 w-auto"
          />
        </div>
      )}
    </footer>
  )
} 