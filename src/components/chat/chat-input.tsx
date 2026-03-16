"use client";

import type { FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { SendHorizonal } from "lucide-react";

interface ChatInputProps {
  input: string;
  isLoading: boolean;
  onInputChange: (value: string) => void;
  onSubmit: (e: FormEvent<HTMLFormElement>) => void;
}

export function ChatInput({
  input,
  isLoading,
  onInputChange,
  onSubmit,
}: ChatInputProps) {
  return (
    <form
      onSubmit={onSubmit}
      className="border-t border-[var(--border)] px-6 py-4"
    >
      <div className="mx-auto flex max-w-3xl items-end gap-2">
        <textarea
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          placeholder="Ask about your budget..."
          rows={1}
          className="flex-1 resize-none rounded-xl border border-[var(--input)] bg-transparent px-4 py-3 text-sm placeholder:text-[var(--muted-foreground)] focus:outline-none focus:ring-1 focus:ring-[var(--ring)]"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              const form = e.currentTarget.form;
              if (form) form.requestSubmit();
            }
          }}
        />
        <Button
          type="submit"
          size="icon"
          disabled={isLoading || !input.trim()}
          className="shrink-0"
        >
          <SendHorizonal className="h-4 w-4" />
        </Button>
      </div>
    </form>
  );
}
