// NOTE: Before using this file, you need to install the following dependencies:
// npm install mongodb mongoose
// npm install --save-dev @types/mongoose

import mongoose from 'mongoose';

const { MONGODB_URI } = process.env;

if (!MONGODB_URI) {
  throw new Error('Please set the MONGODB_URI environment variable');
}

let cachedConnection: typeof mongoose | null = null;

/**
 * Connect to MongoDB database
 * @returns Mongoose connection
 */
async function connectToDatabase() {
  if (cachedConnection) {
    return cachedConnection;
  }

  try {
    const connection = await mongoose.connect(MONGODB_URI as string);
    cachedConnection = connection;
    return connection;
  } catch (error) {
    console.error('MongoDB connection error:', error);
    throw error;
  }
}

export default connectToDatabase; 