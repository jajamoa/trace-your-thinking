// 运行此脚本来初始化引导问题数据库
// node scripts/seed-guiding-questions.js

const { MongoClient } = require('mongodb');
require('dotenv').config({ path: '.env.local' });

// 默认的引导问题
const initialGuidingQuestions = [
  {
    id: "gq1",
    text: "Could you describe your current research focus and how it relates to the broader field?",
    shortText: "Research focus",
    category: "research",
    isActive: true,
    order: 0
  },
  {
    id: "gq2",
    text: "Could you elaborate on the methodologies you're using in your current project?",
    shortText: "Methodologies",
    category: "research",
    isActive: true,
    order: 1
  },
  {
    id: "gq3",
    text: "What challenges have you encountered in your research, and how have you addressed them?",
    shortText: "Challenges",
    category: "research",
    isActive: true,
    order: 2
  },
  {
    id: "gq4",
    text: "How do you situate your work within existing literature in your field?",
    shortText: "Literature context",
    category: "research",
    isActive: true,
    order: 3
  },
  {
    id: "gq5",
    text: "What implications might your findings have for theory or practice in your domain?",
    shortText: "Implications",
    category: "research",
    isActive: true,
    order: 4
  }
];

async function seedGuidingQuestions() {
  // 检查环境变量
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

    // 检查集合是否为空
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

    // 插入新的引导问题
    const result = await collection.insertMany(initialGuidingQuestions);
    console.log(`${result.insertedCount} guiding questions have been added to the database.`);

    // 添加时间戳
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

// 执行脚本
seedGuidingQuestions(); 