// Run this script to initialize the guiding questions database
// node scripts/seed-guiding-questions.js

const { MongoClient } = require('mongodb');
require('dotenv').config({ path: '.env.local' });

// Default guiding questions
const initialGuidingQuestions = [
  {
    id: "gq0a",
    text: "Welcome to the Trace Your Thinking interview system. This platform is designed to capture your research insights in a comfortable and intuitive way. Would you like me to guide you through using this system?",
    shortText: "Welcome",
    category: "tutorial",
    isActive: true,
    order: 0
  },
  {
    id: "gq0b",
    text: "You have two options for answering questions: voice recording or typing. For voice recording, press the microphone button (🎤) or the Space key to start recording. When finished, press the microphone button or Space key again to stop. You can also press ESC to cancel. The system will automatically transcribe and submit your response after recording. Would you like to try voice recording now?",
    shortText: "Voice recording guide",
    category: "tutorial",
    isActive: true,
    order: 1
  },
  {
    id: "gq0c",
    text: "For text input, click the message icon (💬) to switch modes. Type your response in the text box. Press Ctrl+Enter or click the send button (➤) to submit. You can press ESC to clear your text. Would you like to try text input now?",
    shortText: "Text input guide",
    category: "tutorial",
    isActive: true,
    order: 2
  },
  {
    id: "gq0d",
    text: "You can switch between voice and text modes at any time. In voice mode, the microphone button will show as red when recording is active. During transcription, you'll see 'Transcribing your speech...' and your answer will be automatically submitted once ready. Remember, in voice mode, always press the microphone button or Space key to begin and end your recording. Feel comfortable with the system now?",
    shortText: "Mode switching guide",
    category: "tutorial",
    isActive: true,
    order: 3
  },
  {
    id: "gq0e",
    text: "As the interview progresses, you'll notice the progress bar at the top of the screen showing your current position. Based on your responses, the system may generate follow-up questions to dive deeper into specific topics. These new questions will be added to your interview flow automatically. Don't be surprised if the progress bar adjusts as new questions are added. This helps us capture your thinking process more thoroughly.",
    shortText: "Progress tracking",
    category: "tutorial",
    isActive: true,
    order: 4
  },
  {
    id: "gq0f",
    text: "Excellent! We're now ready to begin the research interview. Remember you can switch input methods anytime. For voice recording, you'll need to explicitly start and stop recording using the microphone button or Space key. Take your time with each response and provide as much detail as you'd like. Let's start with our first research question.",
    shortText: "Start interview",
    category: "tutorial",
    isActive: true,
    order: 5
  },
  {
    id: "gq1",
    text: "Could you describe your current research focus and how it relates to the broader field?",
    shortText: "Research focus",
    category: "research",
    isActive: true,
    order: 6
  },
  {
    id: "gq2",
    text: "Could you elaborate on the methodologies you're using in your current project?",
    shortText: "Methodologies",
    category: "research",
    isActive: true,
    order: 7
  },
  {
    id: "gq3",
    text: "What challenges have you encountered in your research, and how have you addressed them?",
    shortText: "Challenges",
    category: "research",
    isActive: true,
    order: 8
  },
  {
    id: "gq4",
    text: "How do you situate your work within existing literature in your field?",
    shortText: "Literature context",
    category: "research",
    isActive: true,
    order: 9
  },
  {
    id: "gq5",
    text: "What implications might your findings have for theory or practice in your domain?",
    shortText: "Implications",
    category: "research",
    isActive: true,
    order: 10
  }
];

async function seedGuidingQuestions() {
  // Check environment variables
  if (!process.env.MONGODB_URI) {
    console.error('MONGODB_URI environment variable is not defined.');
    process.exit(1);
  }

  const client = new MongoClient(process.env.MONGODB_URI);

  try {
    await client.connect();
    console.log('Connected to MongoDB');

    const db = client.db();
    const collection = db.collection('guidingquestions');

    // Check if collection is empty
    const count = await collection.countDocuments();
    
    if (count > 0) {
      console.log(`Found ${count} existing guiding questions.`);
      const deletePrompt = process.argv.includes('--force') ? 'y' : 
        await promptUser('Do you want to delete existing guiding questions? (y/n): ');
      
      if (deletePrompt.toLowerCase() === 'y') {
        await collection.deleteMany({});
        console.log('Deleted existing guiding questions.');
      } else {
        console.log('Operation cancelled. No changes made.');
        return;
      }
    }

    // Insert new guiding questions
    const result = await collection.insertMany(initialGuidingQuestions);
    console.log(`${result.insertedCount} guiding questions have been added to the database.`);

    // Add timestamps
    const timestamp = new Date();
    for (const id of Object.values(result.insertedIds)) {
      await collection.updateOne(
        { _id: id },
        { $set: { createdAt: timestamp, updatedAt: timestamp } }
      );
    }
    
    console.log('Added timestamps to all guiding questions.');
    console.log('Database seeding completed successfully!');
    
  } catch (error) {
    console.error('An error occurred while seeding the database:', error);
  } finally {
    await client.close();
    console.log('MongoDB connection closed.');
  }
}

async function promptUser(question) {
  const readline = require('readline').createInterface({
    input: process.stdin,
    output: process.stdout
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