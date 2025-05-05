"use client"

/**
 * Mock WebSocket connection for streaming text responses
 */
export function mockWebSocketConnection(fullText: string, onChunk: (chunk: string) => void, onComplete: () => void) {
  let currentIndex = 0
  const chunkSize = 3 // Characters per chunk
  const delay = 50 // Milliseconds between chunks

  const sendNextChunk = () => {
    if (currentIndex < fullText.length) {
      const endIndex = Math.min(currentIndex + chunkSize, fullText.length)
      const chunk = fullText.substring(currentIndex, endIndex)
      onChunk(chunk)
      currentIndex = endIndex
      setTimeout(sendNextChunk, delay)
    } else {
      onComplete()
    }
  }

  // Start sending chunks
  setTimeout(sendNextChunk, delay)

  // Return a mock close function
  return {
    close: () => {
      // This would close the connection in a real implementation
      console.log("Mock WebSocket connection closed")
    },
  }
}
