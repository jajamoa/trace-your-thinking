"use client"

import Image from "next/image"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Info } from "lucide-react"
import Footer from "./Footer"

export default function MobileRedirect() {
  return (
    <div className="min-h-screen bg-[#f5f2eb] flex flex-col items-center justify-center px-4 py-8 relative">
      <div className="w-full max-w-md mx-auto mb-8 relative">
        <div className="absolute inset-0 bg-gradient-to-b from-[#f5f2eb]/50 to-[#f5f2eb] rounded-2xl z-0 opacity-70"></div>
        <div className="absolute -inset-1 bg-gradient-to-r from-blue-100 to-blue-50 rounded-2xl blur-xl opacity-50 z-0"></div>
        <Image
          src="/og-image.png"
          alt="Trace Your Thinking"
          width={1200}
          height={630}
          className="w-full h-auto rounded-2xl shadow-sm relative z-10 mix-blend-multiply opacity-90"
          priority
          unoptimized={true}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#f5f2eb] to-transparent opacity-30 rounded-2xl z-20 mix-blend-overlay"></div>
      </div>
      
      <div className="bg-white rounded-2xl p-6 shadow-subtle border border-[#e0ddd5] w-full max-w-md mx-auto">
        <h1 className="text-2xl font-light mb-4 text-center">Desktop Experience Required</h1>
        
        <p className="text-gray-600 mb-6 text-center">
          Trace Your Thinking is designed for desktop computers to ensure the best interview experience. 
          Please access this application from a laptop or desktop computer.
        </p>
        
        <Link href="/about" className="block w-full">
          <Button 
            variant="outline" 
            className="w-full border-[#e0ddd5] hover:bg-[#f5f2eb]"
          >
            Learn More About This Study
            <Info className="ml-2 h-4 w-4" />
          </Button>
        </Link>
      </div>
      
      <Footer showAboutLink={false} />
    </div>
  )
} 