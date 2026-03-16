import { convertToModelMessages, streamText, UIMessage } from "ai";
import { getMcpTools } from "@/lib/mcp/tools";
import { SYSTEM_PROMPT } from "@/lib/ai/system-prompt";

export async function POST(req: Request) {
  try {
    const { messages }: { messages: UIMessage[] } = await req.json();

    const tools = await getMcpTools();

    const result = streamText({
      model: "anthropic/claude-sonnet-4-6",
      system: SYSTEM_PROMPT,
      messages: await convertToModelMessages(messages),
      tools,
      maxSteps: 10,
    });

    return result.toUIMessageStreamResponse();
  } catch (error) {
    console.error("[chat/route]", error);
    return new Response(JSON.stringify({ error: String(error) }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
}
