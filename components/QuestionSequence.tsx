"use client"

import { motion } from "framer-motion"
import { useStore } from "@/lib/store"

export default function QuestionSequence() {
  const { questions, currentQuestionIndex } = useStore()

  return (
    <div className="w-full mb-6">
      <h3 className="text-sm font-medium text-gray-500 mb-3">Question Sequence</h3>
      <div className="flex flex-col gap-2">
        {questions.map((question, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1, duration: 0.3 }}
            className={`p-3 rounded-lg border ${
              index === currentQuestionIndex
                ? "bg-[#333333] text-white border-[#222222]"
                : index < currentQuestionIndex
                  ? "bg-[#f5f2eb] text-gray-500 border-[#e0ddd5]"
                  : "bg-white text-gray-400 border-[#e0ddd5]"
            }`}
          >
            <div className="flex items-center gap-3">
              <div
                className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                  index === currentQuestionIndex
                    ? "bg-white text-[#333333]"
                    : index < currentQuestionIndex
                      ? "bg-[#333333] text-white"
                      : "bg-[#e0ddd5] text-gray-500"
                }`}
              >
                {index + 1}
              </div>
              <div className={`font-light text-sm ${index > currentQuestionIndex ? "opacity-50" : ""}`}>
                {question.shortText}
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
