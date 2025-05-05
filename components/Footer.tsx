"use client"

import Image from "next/image"
import { useMemo } from "react"

interface FooterProps {
  showLogo?: boolean
}

export default function Footer({ showLogo = true }: FooterProps) {
  // Get current year
  const currentYear = useMemo(() => new Date().getFullYear(), [])
  
  return (
    <footer className="absolute bottom-0 left-0 right-0 p-4 text-xs text-gray-500 flex justify-between items-center">
      <div>© {currentYear} MIT · COUHES Protocol E-6512</div>
      {showLogo && (
        <div className="opacity-70 hover:opacity-100 transition-opacity">
          <Image
            src="/mit-logo.svg"
            alt="MIT Logo"
            width={60}
            height={30}
            className="h-6 w-auto"
          />
        </div>
      )}
    </footer>
  )
} 