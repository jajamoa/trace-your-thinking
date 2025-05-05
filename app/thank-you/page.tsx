"use client"

import { useEffect } from "react"
import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"
import { ExternalLink, Info } from "lucide-react"
import Confetti from "@/components/Confetti"
import { useStore } from "@/lib/store"
import { useRouter } from "next/navigation"
import Link from "next/link"
import Footer from "@/components/Footer"

export default function ThankYouPage() {
  const { resetStore, prolificId } = useStore()
  const router = useRouter()

  useEffect(() => {
    // Check if user has a Prolific ID
    if (!prolificId) {
      router.push("/")
      return
    }

    // Reset the store when leaving the app
    return () => {
      resetStore()
    }
  }, [resetStore, prolificId, router])

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

          <div className="flex flex-col sm:flex-row justify-center gap-4 mb-6">
            <motion.div whileTap={{ scale: 0.96 }}>
              <Button
                onClick={() => window.close()}
                size="lg"
                className="bg-[#333333] hover:bg-[#222222] text-white px-8 rounded-full shadow-subtle"
              >
                Close Window
                <ExternalLink className="ml-2 h-5 w-5" />
              </Button>
            </motion.div>

            <motion.div whileTap={{ scale: 0.96 }}>
              <Link href="/about">
                <Button
                  variant="outline"
                  size="lg"
                  className="border-[#e0ddd5] hover:bg-[#f5f2eb] px-8 rounded-full shadow-subtle"
                >
                  About This Study
                  <Info className="ml-2 h-5 w-5" />
                </Button>
              </Link>
            </motion.div>
          </div>
        </motion.div>
      </motion.div>

      <Footer />
    </div>
  )
}
