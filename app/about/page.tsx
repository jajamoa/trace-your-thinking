"use client"

import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"
import { ArrowLeft, ExternalLink } from "lucide-react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import Footer from "@/components/Footer"
import useDeviceDetect from "@/hooks/useDeviceDetect"

export default function AboutPage() {
  const router = useRouter()
  const { isMobile } = useDeviceDetect()

  return (
    <div className="min-h-screen relative bg-[#f5f2eb] px-2 sm:px-4 py-8 sm:py-16">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
        className="container mx-auto max-w-3xl"
      >
        <Button
          variant="ghost"
          onClick={() => router.back()}
          className="mb-4 sm:mb-8 text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>

        <div className={`bg-white rounded-2xl sm:rounded-3xl p-5 sm:p-8 md:p-12 shadow-subtle border border-[#e0ddd5] ${isMobile ? 'mx-0' : ''}`}>
          <h1 className="text-2xl sm:text-3xl font-light mb-6 sm:mb-8 text-[#333333]">About This Study</h1>

          <div className="space-y-4 sm:space-y-6 text-gray-700 leading-relaxed text-sm sm:text-base">
            <p>
              We are a research team from{" "}
              <Link href="https://www.media.mit.edu/" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline inline-flex items-center">
                MIT Media Lab
                <ExternalLink className="h-3 w-3 ml-0.5" />
              </Link>,{" "}
              <Link href="https://www.eecs.mit.edu/" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline inline-flex items-center">
                EECS
                <ExternalLink className="h-3 w-3 ml-0.5" />
              </Link>,{" "}
              <Link href="https://bcs.mit.edu/" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline inline-flex items-center">
                BCS
                <ExternalLink className="h-3 w-3 ml-0.5" />
              </Link>,{" "}
              <Link href="https://dusp.mit.edu/" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline inline-flex items-center">
                DUSP
                <ExternalLink className="h-3 w-3 ml-0.5" />
              </Link>, and{" "}
              <Link href="https://idss.mit.edu/" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline inline-flex items-center">
                IDSS
                <ExternalLink className="h-3 w-3 ml-0.5" />
              </Link>{" "}
              conducting a study to understand how people reason about policy and development.
            </p>

            <div className="py-3 sm:py-4 px-4 sm:px-6 bg-[#f5f2eb] rounded-lg border border-[#e0ddd5]">
              <p className="text-xs sm:text-sm">
                This study (COUHES Protocol E-6512) is approved by MIT's ethics board (COUHES) as exempt
                research under U.S. federal guidelines.
              </p>
            </div>

            <p>
              We do not collect personal identifiers, and your responses will remain confidential
              and used for academic research only.
            </p>

            <div className="pt-4 sm:pt-6 border-t border-[#e0ddd5]">
              <h2 className="text-lg sm:text-xl font-light mb-2 sm:mb-4 text-[#333333]">Contact Information</h2>
              <p>
                For questions about this study, please contact: <a href="mailto:cli@mit.edu" className="text-blue-600 hover:underline">cli@mit.edu</a>
              </p>
            </div>
          </div>
        </div>
      </motion.div>
      
      <Footer />
    </div>
  )
} 