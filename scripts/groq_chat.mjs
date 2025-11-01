// Simple Groq chat example using OpenAI-compatible API
// Usage:
//   1) npm i openai
//   2) set GROQ_API_KEY=... (or export on macOS/Linux)
//   3) node scripts/groq_chat.mjs "Your prompt here"

import OpenAI from "openai";

const apiKey = process.env.GROQ_API_KEY;
if (!apiKey) {
  console.error("GROQ_API_KEY is not set in environment.");
  process.exit(1);
}

const client = new OpenAI({
  apiKey,
  baseURL: "https://api.groq.com/openai/v1",
});

const prompt = process.argv.slice(2).join(" ") || "Explain the importance of fast language models.";
const model = process.env.GROQ_MODEL || "llama3-70b-8192"; // e.g., llama3-70b-8192, mixtral-8x7b-32768

try {
  const resp = await client.chat.completions.create({
    model,
    messages: [
      { role: "system", content: "You are a concise AI assistant." },
      { role: "user", content: prompt },
    ],
    temperature: 0.2,
  });

  console.log(resp.choices[0]?.message?.content ?? "<no content>");
} catch (err) {
  console.error("Groq request failed:", err?.response?.data || err?.message || err);
  process.exit(1);
}

