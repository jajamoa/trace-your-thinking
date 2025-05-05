"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { Textarea } from "@/components/ui/textarea"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { useStore } from "@/lib/store"
import { toast } from "@/components/ui/use-toast"
import { AlertCircle } from "lucide-react"

interface TranscriptEditorProps {
  highlightEmptyAnswers?: string[]
}

export default function TranscriptEditor({ highlightEmptyAnswers = [] }: TranscriptEditorProps) {
  const { qaPairs, updateQAPair } = useStore()
  const [expandedItems, setExpandedItems] = useState<string[]>([])
  const [isSaving, setIsSaving] = useState(false)
  const [lastSavedTime, setLastSavedTime] = useState<string | null>(null)

  // Initialize all items as expanded
  useEffect(() => {
    if (qaPairs.length > 0) {
      setExpandedItems(qaPairs.map((pair) => pair.id))
    }
  }, [qaPairs])

  // Auto-expand empty answers that need attention
  useEffect(() => {
    if (highlightEmptyAnswers.length > 0) {
      setExpandedItems((prev) => {
        const newExpanded = [...prev]
        highlightEmptyAnswers.forEach((id) => {
          if (!newExpanded.includes(id)) {
            newExpanded.push(id)
          }
        })
        return newExpanded
      })
    }
  }, [highlightEmptyAnswers])

  // Auto-save when answers change
  useEffect(() => {
    const saveTimeout = setTimeout(() => {
      if (qaPairs.length > 0) {
        setIsSaving(true)

        // Mock API call to save responses
        mockSaveResponses(qaPairs)
          .then(() => {
            setIsSaving(false)
            setLastSavedTime(new Date().toLocaleTimeString())
          })
          .catch(() => {
            setIsSaving(false)
            toast({
              title: "Error saving",
              description: "There was an error saving your responses. Please try again.",
              variant: "destructive",
            })
          })
      }
    }, 1000)

    return () => clearTimeout(saveTimeout)
  }, [qaPairs])

  // Mock function to simulate API call
  const mockSaveResponses = async (responses: typeof qaPairs) => {
    return new Promise<void>((resolve, reject) => {
      setTimeout(() => {
        // 95% chance of success
        if (Math.random() > 0.05) {
          resolve()
        } else {
          reject(new Error("Mock API error"))
        }
      }, 800)
    })
  }

  const handleAccordionChange = (value: string) => {
    setExpandedItems((prev) => {
      if (prev.includes(value)) {
        return prev.filter((item) => item !== value)
      } else {
        return [...prev, value]
      }
    })
  }

  const handleAnswerChange = (id: string, newAnswer: string) => {
    updateQAPair(id, { answer: newAnswer })
  }

  if (qaPairs.length === 0) {
    return (
      <div className="bg-white backdrop-blur-md rounded-3xl p-8 shadow-subtle border border-[#e0ddd5] text-center">
        <p className="text-gray-500 font-light">No interview data available.</p>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
      className="bg-white backdrop-blur-md rounded-3xl p-8 shadow-subtle border border-[#e0ddd5]"
    >
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-light tracking-wide">Edit Responses</h2>
        <div className="text-xs text-gray-500">
          {isSaving ? (
            <span className="italic">Saving changes...</span>
          ) : lastSavedTime ? (
            <span>Last saved at {lastSavedTime}</span>
          ) : null}
        </div>
      </div>

      <Accordion type="multiple" value={expandedItems} onValueChange={setExpandedItems} className="space-y-4">
        {qaPairs.map((pair, index) => {
          const isEmpty = !pair.answer.trim()
          const isHighlighted = highlightEmptyAnswers.includes(pair.id)

          return (
            <AccordionItem
              key={pair.id}
              value={pair.id}
              className={`border rounded-xl overflow-hidden ${
                isHighlighted ? "border-amber-300 bg-amber-50" : "border-[#e0ddd5]"
              }`}
              id={`answer-${pair.id}`}
            >
              <AccordionTrigger
                onClick={() => handleAccordionChange(pair.id)}
                className={`px-5 py-4 hover:bg-[#f5f2eb] text-left ${
                  isHighlighted ? "bg-amber-50 hover:bg-amber-100" : ""
                }`}
              >
                <div className="flex items-start gap-3 w-full">
                  <div
                    className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium mt-0.5 ${
                      isHighlighted ? "bg-amber-300 text-amber-800" : "bg-[#e0ddd5] text-gray-700"
                    }`}
                  >
                    {index + 1}
                  </div>
                  <div className="flex flex-col gap-1 flex-grow pr-6">
                    <div className="font-light">{pair.question}</div>
                    {isEmpty && (
                      <div className="text-amber-500 flex items-center gap-1 text-xs font-medium">
                        <AlertCircle className="h-3.5 w-3.5" />
                        <span>Required</span>
                      </div>
                    )}
                  </div>
                </div>
              </AccordionTrigger>
              <AccordionContent
                className={`px-5 py-4 border-t ${isHighlighted ? "border-amber-300" : "border-[#e0ddd5]"}`}
              >
                <div className="pl-9">
                  <div className="text-sm text-gray-500 mb-2">Response:</div>
                  <Textarea
                    value={pair.answer}
                    onChange={(e) => handleAnswerChange(pair.id, e.target.value)}
                    className={`min-h-[100px] resize-none font-light ${
                      isHighlighted
                        ? "bg-amber-50 border-amber-300 focus:ring-amber-400"
                        : "bg-[#f5f2eb] border-[#e0ddd5] focus:ring-blue-400"
                    }`}
                    placeholder={isEmpty ? "This question requires an answer" : "Enter your answer..."}
                    aria-label={`Answer to question ${index + 1}`}
                  />
                </div>
              </AccordionContent>
            </AccordionItem>
          )
        })}
      </Accordion>
    </motion.div>
  )
}
