"use client";

import { useEffect, useRef } from "react";
import type { UIMessage } from "ai";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageBubble } from "./message-bubble";
import { ToolInvocation } from "./tool-invocation";
import { Loader2 } from "lucide-react";

interface MessageListProps {
  messages: UIMessage[];
  isLoading: boolean;
}

export function MessageList({ messages, isLoading }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <ScrollArea className="flex-1">
      <div className="mx-auto max-w-3xl space-y-4 p-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 text-center text-[var(--muted-foreground)]">
            <p className="text-lg font-medium">
              Ask me about your budget
            </p>
            <p className="mt-1 text-sm">
              Try &quot;What budgets do I have?&quot; or &quot;Show me where my
              money is going&quot;
            </p>
          </div>
        )}
        {messages.map((message) => (
          <div key={message.id}>
            {message.parts.map((part, i) => {
              if (part.type === "text" && part.text.trim()) {
                return (
                  <MessageBubble
                    key={i}
                    role={message.role}
                    content={part.text}
                  />
                );
              }
              if (part.type.startsWith("tool-")) {
                const toolPart = part as {
                  type: string;
                  toolCallId: string;
                  state: string;
                  input?: Record<string, unknown>;
                  output?: unknown;
                };
                return (
                  <ToolInvocation
                    key={i}
                    toolName={part.type.replace(/^tool-/, "")}
                    toolCallId={toolPart.toolCallId}
                    state={toolPart.state}
                    input={toolPart.input}
                    output={toolPart.output}
                  />
                );
              }
              return null;
            })}
          </div>
        ))}
        {isLoading &&
          messages.length > 0 &&
          messages[messages.length - 1].role === "user" && (
            <div className="flex items-center gap-2 text-sm text-[var(--muted-foreground)]">
              <Loader2 className="h-4 w-4 animate-spin" />
              Thinking...
            </div>
          )}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
