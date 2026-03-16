"use client";

import { Loader2, Wrench, CheckCircle2 } from "lucide-react";
import { ToolResultRenderer } from "@/components/viz/tool-result-renderer";

interface ToolInvocationProps {
  toolName: string;
  toolCallId: string;
  state: string;
  input?: Record<string, unknown>;
  output?: unknown;
}

function formatToolName(name: string): string {
  return name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function ToolInvocation({ toolName, toolCallId, state, input, output }: ToolInvocationProps) {
  const isComplete = state === "output-available";
  const args = input ?? {};

  return (
    <div className="my-2 rounded-lg border border-[var(--border)] bg-[var(--card)] text-sm">
      <div className="flex items-center gap-2 px-3 py-2 text-[var(--muted-foreground)]">
        {isComplete ? (
          <CheckCircle2 className="h-4 w-4 text-green-500" />
        ) : (
          <Loader2 className="h-4 w-4 animate-spin" />
        )}
        <Wrench className="h-3.5 w-3.5" />
        <span className="font-medium">{formatToolName(toolName)}</span>
        {Object.keys(args).length > 0 && (
          <span className="text-xs opacity-60">
            ({Object.entries(args)
              .filter(([, v]) => v !== undefined)
              .map(([k, v]) => `${k}: ${v}`)
              .join(", ")})
          </span>
        )}
      </div>
      {isComplete && output != null && (
        <div className="border-t border-[var(--border)] p-3">
          <ToolResultRenderer toolName={toolName} result={output as string} />
        </div>
      )}
    </div>
  );
}
