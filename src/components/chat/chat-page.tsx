"use client";

import { useState } from "react";
import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { MessageList } from "./message-list";
import { ChatInput } from "./chat-input";

const transport = new DefaultChatTransport({
  api: "/api/chat",
});

export function ChatPage() {
  const [input, setInput] = useState("");
  const { messages, sendMessage, status, error } = useChat({ transport });

  const isLoading = status === "streaming" || status === "submitted";

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    sendMessage({ text: input });
    setInput("");
  }

  return (
    <div className="flex h-dvh flex-col">
      <header className="flex items-center justify-between border-b border-[var(--border)] px-6 py-3">
        <h1 className="text-lg font-semibold">BudgetLens</h1>
      </header>
      <MessageList messages={messages} isLoading={isLoading} />
      {error && (
        <div className="px-6 py-2 text-sm text-[var(--destructive)]">
          Error: {error.message}
        </div>
      )}
      <ChatInput
        input={input}
        isLoading={isLoading}
        onInputChange={setInput}
        onSubmit={handleSubmit}
      />
    </div>
  );
}
