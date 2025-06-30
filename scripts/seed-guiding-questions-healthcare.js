// Run this script to initialize the guiding questions database for universal healthcare research
// node scripts/seed-guiding-questions-healthcare.js

const { MongoClient } = require("mongodb");
require("dotenv").config({ path: ".env.local" });

// Default guiding questions for universal healthcare study
const initialGuidingQuestions = [
  {
    id: "gq0a",
    text: "Welcome to the Trace Your Thinking interview system. This platform is designed to capture your thoughts about universal healthcare policies. Would you like me to guide you through using this system?",
    shortText: "Welcome",
    category: "tutorial",
    isActive: true,
    order: 0,
  },
  {
    id: "gq0b",
    text: "You have two options for answering questions: voice recording or typing. For voice recording, press the microphone button (🎤) or the Space key to start recording. When finished, press the microphone button or Space key again to stop. You can also press ESC to cancel. The system will automatically transcribe and submit your response after recording. Would you like to try voice recording now?",
    shortText: "Voice recording guide",
    category: "tutorial",
    isActive: true,
    order: 1,
  },
  {
    id: "gq0c",
    text: "For text input, click the message icon (💬) to switch modes. Type your response in the text box. Press Ctrl+Enter or click the send button (➤) to submit. You can press ESC to clear your text. Would you like to try text input now?",
    shortText: "Text input guide",
    category: "tutorial",
    isActive: true,
    order: 2,
  },
  {
    id: "gq0d",
    text: "You can switch between voice and text modes at any time. In voice mode, the microphone button will show as red when recording is active. During transcription, you'll see 'Transcribing your speech...' and your answer will be automatically submitted once ready. Feel comfortable with the system now?",
    shortText: "Mode switching guide",
    category: "tutorial",
    isActive: true,
    order: 3,
  },
  {
    id: "gq0e",
    text: "As the interview progresses, you'll notice the progress bar at the top of the screen showing your current position. Based on your responses, the system may generate follow-up questions to dive deeper into specific topics. These new questions will be added to your interview flow automatically. This helps us capture your thinking process more thoroughly.",
    shortText: "Progress tracking",
    category: "tutorial",
    isActive: true,
    order: 4,
  },
  {
    id: "gq0f",
    text: "Excellent! We're now ready to begin the interview about universal healthcare policies. Take your time with each response and provide as much detail as you'd like. Let's start with our first question.",
    shortText: "Start interview",
    category: "tutorial",
    isActive: true,
    order: 5,
  },
  // Phase 1: Node Discovery Questions - Primary stance exploration
  {
    id: "gq1",
    text: "To what extent do you support or oppose universal healthcare policies that provide government-funded healthcare coverage for all citizens? Please explain your reasoning.",
    shortText: "Stance on universal healthcare",
    category: "research",
    isActive: true,
    order: 6,
  },
  // Phase 1: Node Discovery Questions - Discovering key concepts/nodes
  {
    id: "gq2",
    text: "What do you think are the most significant impacts, positive or negative, of implementing a universal healthcare system?",
    shortText: "Healthcare system impacts",
    category: "research",
    isActive: true,
    order: 7,
  },
  {
    id: "gq3",
    text: "How do you think universal healthcare policies might affect healthcare quality and accessibility?",
    shortText: "Quality and accessibility",
    category: "research",
    isActive: true,
    order: 8,
  },
  {
    id: "gq4",
    text: "What impact do you believe a universal healthcare system might have on medical innovation and research?",
    shortText: "Medical innovation",
    category: "research",
    isActive: true,
    order: 9,
  },
  {
    id: "gq5",
    text: "How do you think universal healthcare might affect the economic burden on individuals and families?",
    shortText: "Economic burden",
    category: "research",
    isActive: true,
    order: 10,
  },
  {
    id: "gq6",
    text: "What role do you believe government should play in healthcare delivery and financing?",
    shortText: "Government role",
    category: "research",
    isActive: true,
    order: 11,
  },
  {
    id: "gq7",
    text: "How might healthcare provider concerns factor into decisions about universal healthcare implementation?",
    shortText: "Provider concerns",
    category: "research",
    isActive: true,
    order: 12,
  },
  {
    id: "gq8",
    text: "What economic effects, both positive and negative, might result from transitioning to a universal healthcare system?",
    shortText: "Economic effects",
    category: "research",
    isActive: true,
    order: 13,
  },
  {
    id: "gq9",
    text: "How do you think the interests of taxpayers versus healthcare consumers should be balanced when making healthcare policy?",
    shortText: "Taxpayers vs consumers",
    category: "research",
    isActive: true,
    order: 14,
  },
  {
    id: "gq10",
    text: "What role do you think social equity and access to care play in discussions about healthcare policy?",
    shortText: "Social equity",
    category: "research",
    isActive: true,
    order: 15,
  },
  // Phase 2 questions will be generated dynamically based on the nodes discovered
  {
    id: "gq11",
    text: "Thank you for sharing your perspectives. As we conclude, is there anything else about universal healthcare policies that you'd like to add?",
    shortText: "Final thoughts",
    category: "conclusion",
    isActive: true,
    order: 16,
  },
];

async function seedGuidingQuestions() {
  // Check environment variables
  if (!process.env.MONGODB_URI) {
    console.error("MONGODB_URI environment variable is not defined in .env.healthcare.local");
    process.exit(1);
  }

  const client = new MongoClient(process.env.MONGODB_URI);

  try {
    await client.connect();
    console.log("Connected to MongoDB");

    const db = client.db();
    const collection = db.collection("guidingquestions");

    // Check if collection is empty
    const count = await collection.countDocuments();

    if (count > 0) {
      console.log(`Found ${count} existing guiding questions.`);
      const deletePrompt = process.argv.includes("--force")
        ? "y"
        : await promptUser(
            "Do you want to delete existing guiding questions? (y/n): "
          );

      if (deletePrompt.toLowerCase() === "y") {
        await collection.deleteMany({});
        console.log("Deleted existing guiding questions.");
      } else {
        console.log("Operation cancelled. No changes made.");
        return;
      }
    }

    // Insert new guiding questions
    const result = await collection.insertMany(initialGuidingQuestions);
    console.log(
      `${result.insertedCount} healthcare guiding questions have been added to the database.`
    );

    // Add timestamps
    const timestamp = new Date();
    for (const id of Object.values(result.insertedIds)) {
      await collection.updateOne(
        { _id: id },
        { $set: { createdAt: timestamp, updatedAt: timestamp } }
      );
    }

    console.log("Added timestamps to all guiding questions.");
    console.log("Database seeding for healthcare study completed successfully!");
  } catch (error) {
    console.error("An error occurred while seeding the database:", error);
  } finally {
    await client.close();
    console.log("MongoDB connection closed.");
  }
}

async function promptUser(question) {
  const readline = require("readline").createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  return new Promise((resolve) => {
    readline.question(question, (answer) => {
      readline.close();
      resolve(answer);
    });
  });
}

// Execute script
seedGuidingQuestions();