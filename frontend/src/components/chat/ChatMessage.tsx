"use client";

import { useState } from "react";
import { ChatMessage as ChatMessageType, useStore } from "@/lib/store";
import ThoughtChain from "./ThoughtChain";

interface Props {
  message: ChatMessageType;
}

export default function ChatMessage({ message }: Props) {
  const isUser = message.role === "user";
  const { resendMessage, state } = useStore();
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Fallback for non-HTTPS
      const ta = document.createElement("textarea");
      ta.value = message.content;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  };

  const handleResend = () => {
    if (!state.isStreaming && message.content) {
      resendMessage(message.content);
    }
  };

  return (
    <div className={`group flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className={`relative max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-blue-600 text-white rounded-br-md"
            : "glass rounded-bl-md"
        }`}
      >
        {/* Thought chain for assistant messages — show above content */}
        {!isUser && message.thoughtChain && message.thoughtChain.length > 0 && (
          <div className="mb-2 border-b border-gray-200/30 pb-2">
            <ThoughtChain events={message.thoughtChain} />
          </div>
        )}

        {/* Message content */}
        <div className={`text-sm leading-relaxed whitespace-pre-wrap ${isUser ? "" : "prose prose-sm max-w-none"}`}>
          {message.content || (
            <span className="inline-flex items-center gap-1 text-gray-400">
              <span className="animate-pulse">●</span>
              <span className="animate-pulse" style={{ animationDelay: "0.2s" }}>●</span>
              <span className="animate-pulse" style={{ animationDelay: "0.4s" }}>●</span>
            </span>
          )}
        </div>

        {/* Action buttons — visible on hover */}
        {message.content && (
          <div className={`flex items-center gap-1 mt-1.5 opacity-0 group-hover:opacity-100 transition-opacity ${
            isUser ? "justify-end" : "justify-start"
          }`}>
            <button
              onClick={handleCopy}
              className={`text-xs px-1.5 py-0.5 rounded transition-colors ${
                isUser
                  ? "text-blue-200 hover:text-white hover:bg-blue-500"
                  : "text-gray-400 hover:text-gray-600 hover:bg-gray-100"
              }`}
              title="Copy"
            >
              {copied ? "Copied!" : "Copy"}
            </button>
            {isUser && (
              <button
                onClick={handleResend}
                disabled={state.isStreaming}
                className="text-xs px-1.5 py-0.5 rounded text-blue-200 hover:text-white hover:bg-blue-500 transition-colors disabled:opacity-40"
                title="Resend this message"
              >
                Resend
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
