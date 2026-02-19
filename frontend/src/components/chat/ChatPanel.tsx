"use client";

import { useRef, useEffect } from "react";
import { useStore } from "@/lib/store";
import ChatMessage from "./ChatMessage";
import ChatInput from "./ChatInput";

export default function ChatPanel() {
  const { state } = useStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages are added
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [state.messages.length]);

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {state.messages.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <div className="text-center">
              <h2 className="text-xl font-semibold mb-2" style={{ color: "var(--accent)" }}>
                mini OpenClaw
              </h2>
              <p className="text-sm text-gray-400">
                {state.activeSessionId
                  ? "Send a message to start chatting"
                  : "Create or select a session to begin"}
              </p>
            </div>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto">
            {state.messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input area */}
      <ChatInput />
    </div>
  );
}
