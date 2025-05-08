"use client"

import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"
import { ArrowLeft, Info, ExternalLink } from "lucide-react"
import Confetti from "@/components/Confetti"
import { useStore } from "@/lib/store"
import { useRouter } from "next/navigation"
import Link from "next/link"
import Footer from "@/components/Footer"

export default function ThankYouPage() {
  const { resetStore, prolificId } = useStore()
  const router = useRouter()
  const [prolificCompletionUrl, setProlificCompletionUrl] = useState<string | null>(null)

  useEffect(() => {
    // Check if user has a Prolific ID
    if (!prolificId) {
      router.push("/")
      return
    }

    // Try to get Prolific completion URL from environment variable
    // Using fetch to get environment variables from the server side
    fetch('/api/get-env')
      .then(response => response.json())
      .then(data => {
        if (data.PROLIFIC_COMPLETION_URL) {
          // Ensure we have a complete URL with protocol
          let completionUrl = data.PROLIFIC_COMPLETION_URL;
          
          // If URL doesn't start with http:// or https://, add https://
          if (!/^https?:\/\//i.test(completionUrl)) {
            completionUrl = 'https://' + completionUrl;
          }
          
          setProlificCompletionUrl(completionUrl);
          console.log("Setting Prolific completion URL:", completionUrl);
        }
      })
      .catch(error => {
        console.error("Failed to fetch environment variables:", error);
      });
    
    // No need to reset the store when loading this page
    // Let the user explicitly choose to return to home to start fresh

  }, [prolificId, router])

  // Handler for returning to home and starting fresh
  const handleReturnHome = () => {
    // Clear ALL data including prolificId before redirecting
    resetStore();
    
    // Force page reload to ensure all React state is reset 
    // and we start completely fresh
    window.location.href = "/";
  }

  return (
    <div className="min-h-screen relative bg-[#f5f2eb]">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.12, ease: [0.4, 0, 0.2, 1] }}
        className="container mx-auto px-4 py-24 flex flex-col items-center justify-center min-h-screen text-center"
      >
        <Confetti />

        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.3, duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
          className="bg-white backdrop-blur-md rounded-3xl p-12 shadow-subtle max-w-2xl mx-auto border border-[#e0ddd5]"
        >
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.5 }}
            className="mb-8"
          >
            <svg
              width="48"
              height="48"
              viewBox="0 0 48 48"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              className="mx-auto"
            >
              <circle cx="24" cy="24" r="24" fill="#2563EB" fillOpacity="0.1" />
              <path
                d="M32 18L22 28L16 22"
                stroke="#333333"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </motion.div>

          <h1 className="text-4xl font-light mb-6 tracking-tight text-[#333333]">Thank You</h1>

          <div className="text-lg text-gray-600 mb-8 leading-relaxed font-light">
            <p className="mb-4">
              Your responses have been successfully submitted. Thank you for contributing to our map of public reasoning.
            </p>
            <div className="inline-block bg-[#f5f2eb] px-4 py-2 rounded-lg">
              <span className="font-medium">Prolific ID:</span> <span className="font-mono">{prolificId}</span>
            </div>
          </div>

          <div className="flex flex-col gap-6 mb-6 w-full max-w-md mx-auto">
            {/* Prolific completion button - prominent */}
            {prolificCompletionUrl && (
              <a 
                href={prolificCompletionUrl} 
                target="_blank" 
                rel="noopener noreferrer" 
                className="w-full"
                onClick={(e) => {
                  // For debugging - log the actual URL being used
                  console.log("Opening Prolific URL:", prolificCompletionUrl);
                  
                  // Handle click directly to ensure it opens as absolute URL
                  if (prolificCompletionUrl) {
                    window.open(prolificCompletionUrl, '_blank', 'noopener,noreferrer');
                    e.preventDefault(); // Prevent default to ensure our handling works
                  }
                }}
              >
                <motion.div 
                  whileHover={{ scale: 1.03 }} 
                  whileTap={{ scale: 0.97 }}
                  className="w-full"
                >
                  <Button
                    size="lg"
                    className="bg-[#1E40AF] hover:bg-[#1E3A8A] text-white px-8 py-6 rounded-xl shadow-md w-full font-medium text-lg flex items-center justify-center gap-2"
                  >
                    Complete on Prolific
                    <ExternalLink className="h-5 w-5" />
                  </Button>
                </motion.div>
              </a>
            )}

            {/* Secondary buttons container */}
            <div className="flex flex-col sm:flex-row justify-center gap-4 w-full">
              <motion.div 
                whileHover={{ scale: 1.02 }} 
                whileTap={{ scale: 0.97 }}
                className="w-full sm:w-1/2"
              >
                <Button
                  onClick={handleReturnHome}
                  size="lg"
                  className="bg-[#333333] hover:bg-[#222222] text-white px-8 py-5 rounded-lg shadow-sm w-full"
                >
                  Return to Home
                  <ArrowLeft className="ml-2 h-5 w-5" />
                </Button>
              </motion.div>

              <motion.div 
                whileHover={{ scale: 1.02 }} 
                whileTap={{ scale: 0.97 }}
                className="w-full sm:w-1/2"
              >
                <Link href="/about" className="w-full">
                  <Button
                    variant="outline"
                    size="lg"
                    className="border-[#e0ddd5] hover:bg-[#f5f2eb] px-8 py-5 rounded-lg shadow-sm w-full"
                  >
                    About This Study
                    <Info className="ml-2 h-5 w-5" />
                  </Button>
                </Link>
              </motion.div>
            </div>
          </div>
        </motion.div>
      </motion.div>

      <Footer />
    </div>
  )
}
