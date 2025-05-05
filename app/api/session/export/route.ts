import { NextResponse } from "next/server"

export async function GET() {
  // Mock data for the export
  const mockData = {
    sessionId: "mock-session-123",
    timestamp: new Date().toISOString(),
    qaPairs: [
      {
        id: "q1",
        question: "Could you describe your current research focus and how it relates to the broader field?",
        answer:
          "My research focuses on human-computer interaction with a specific emphasis on accessibility. I'm developing new interfaces that can adapt to users with different abilities, which connects to the broader field of inclusive design.",
      },
      {
        id: "q2",
        question: "Could you elaborate on the methodologies you're using in your current project?",
        answer:
          "I'm using a mixed-methods approach that combines quantitative user testing with qualitative interviews. This allows me to gather both performance metrics and rich contextual information about the user experience.",
      },
      {
        id: "q3",
        question: "What challenges have you encountered in your research, and how have you addressed them?",
        answer:
          "The biggest challenge has been recruiting diverse participants. I've addressed this by partnering with community organizations and using more inclusive recruitment language in our materials.",
      },
    ],
    metadata: {
      duration: "15m 42s",
      nodeCount: 24,
      motifCount: 3,
    },
  }

  return NextResponse.json(mockData)
}
