"use client";

import { useState, useRef, useEffect, KeyboardEvent } from "react";
import { useStore } from "@/lib/store";

export default function ChatInput() {
  const [input, setInput] = useState("");
  const { sendMessage, state } = useStore();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const text = input.trim();
    if (!text || state.isStreaming) return;
    setInput("");
    sendMessage(text);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [input]);

  return (
    <div className="glass border-t border-gray-200/50 p-3">
      <div className="flex items-end gap-2 max-w-3xl mx-auto">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={state.activeSessionId ? "Type a message... (Shift+Enter for new line)" : "Create a session first"}
          disabled={!state.activeSessionId || state.isStreaming}
          rows={1}
          className="flex-1 resize-none rounded-xl border border-gray-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300 disabled:opacity-50 bg-white"
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || state.isStreaming || !state.activeSessionId}
          className="rounded-xl px-4 py-2.5 text-sm font-medium text-white transition-colors disabled:opacity-40"
          style={{ background: "var(--accent)" }}
        >
          {state.isStreaming ? "..." : "Send"}
        </button>
      </div>
    </div>
  );
}
