import { NextResponse } from "next/server"
import { openai, WhisperSegment } from "@/lib/openai-client"
import fs from 'fs';
import path from 'path';
import os from 'os';

export async function POST(request: Request) {
  let tempFilePath: string | null = null;
  
  try {
    // Get the form data from the request
    const formData = await request.formData()
    const audioFile = formData.get("file") as File
    
    if (!audioFile) {
      return NextResponse.json({ error: "No audio file provided" }, { status: 400 })
    }
    
    // Extract language and optional parameters
    const language = formData.get("language") as string || "en"
    const model = formData.get("model") as string || "whisper-1"
    
    console.log(`Processing audio file (${audioFile.size} bytes) with Whisper API`)
    
    // Create a temporary file
    const tempDir = os.tmpdir();
    tempFilePath = path.join(tempDir, `audio_${Date.now()}.webm`);
    
    // Convert File to Buffer and write to temporary file
    const arrayBuffer = await audioFile.arrayBuffer();
    fs.writeFileSync(tempFilePath, Buffer.from(arrayBuffer));
    
    // Call OpenAI Whisper API with the file path
    const response = await openai.audio.transcriptions.create({
      file: fs.createReadStream(tempFilePath),
      model: model,
      language: language,
      response_format: "verbose_json",
    });
    
    console.log("Whisper API transcription successful");
    
    // Format the response to match our expected format
    const result = {
      text: response.text,
      segments: response.segments ? response.segments.map((segment: any) => ({
        id: segment.id,
        start: segment.start,
        end: segment.end,
        text: segment.text,
        confidence: segment.confidence || 0.9,
      })) : [],
      language: response.language || language,
    }
    
    return NextResponse.json(result)
  } catch (error: any) {
    console.error("Error in Whisper transcription:", error)
    
    // Format error message
    const errorMessage = error.message || "Failed to transcribe audio"
    const status = error.status || 500
    
    return NextResponse.json({ error: errorMessage }, { status })
  } finally {
    // Clean up temporary file
    if (tempFilePath && fs.existsSync(tempFilePath)) {
      try {
        fs.unlinkSync(tempFilePath);
      } catch (e) {
        console.error("Error cleaning up temporary file:", e);
      }
    }
  }
}
