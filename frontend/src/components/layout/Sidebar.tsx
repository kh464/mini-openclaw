"use client";

import { useEffect, useState, useRef } from "react";
import { useStore } from "@/lib/store";
import * as api from "@/lib/api";

export default function Sidebar() {
  const { state, loadSessions, selectSession, createNewSession, loadConfig, deleteSession, renameSession } = useStore();
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const editRef = useRef<HTMLInputElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadSessions();
    loadConfig();
  }, [loadSessions, loadConfig]);

  // Close menu on click outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpenId(null);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Auto-focus rename input
  useEffect(() => {
    if (editingId && editRef.current) editRef.current.focus();
  }, [editingId]);

  const handleRename = async (id: string) => {
    const trimmed = editTitle.trim();
    if (trimmed) {
      await renameSession(id, trimmed);
    }
    setEditingId(null);
  };

  return (
    <aside className="glass flex flex-col h-full w-full border-r border-gray-200/50">
      {/* New Chat Button */}
      <div className="p-3 border-b border-gray-200/30">
        <button
          onClick={createNewSession}
          className="w-full py-2 px-3 rounded-lg text-sm font-medium transition-colors"
          style={{ background: "var(--accent)", color: "white" }}
        >
          + New Chat
        </button>
      </div>

      {/* Session List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {state.sessions.map((session) => (
          <div key={session.id} className="relative group">
            {editingId === session.id ? (
              <input
                ref={editRef}
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                onBlur={() => handleRename(session.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleRename(session.id);
                  if (e.key === "Escape") setEditingId(null);
                }}
                className="w-full px-3 py-2 rounded-lg text-sm border border-blue-300 outline-none"
              />
            ) : (
              <button
                onClick={() => selectSession(session.id)}
                onContextMenu={(e) => {
                  e.preventDefault();
                  setMenuOpenId(menuOpenId === session.id ? null : session.id);
                }}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors truncate flex items-center justify-between ${
                  state.activeSessionId === session.id
                    ? "bg-blue-50 text-blue-700 font-medium"
                    : "text-gray-600 hover:bg-gray-100"
                }`}
              >
                <span className="truncate">
                  {session.title}
                  <span className="text-xs text-gray-400 ml-1">({session.message_count})</span>
                </span>
                {/* Three-dot menu trigger */}
                <span
                  onClick={(e) => {
                    e.stopPropagation();
                    setMenuOpenId(menuOpenId === session.id ? null : session.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 ml-1 px-1 text-gray-400 hover:text-gray-600 flex-shrink-0"
                >
                  &#8943;
                </span>
              </button>
            )}

            {/* Context menu */}
            {menuOpenId === session.id && (
              <div
                ref={menuRef}
                className="absolute right-2 top-8 z-20 bg-white border border-gray-200 rounded-lg shadow-lg py-1 min-w-[120px]"
              >
                <button
                  onClick={() => {
                    setEditTitle(session.title);
                    setEditingId(session.id);
                    setMenuOpenId(null);
                  }}
                  className="w-full text-left px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100"
                >
                  Rename
                </button>
                <button
                  onClick={async () => {
                    setMenuOpenId(null);
                    if (confirm("Delete this session?")) {
                      await deleteSession(session.id);
                    }
                  }}
                  className="w-full text-left px-3 py-1.5 text-sm text-red-600 hover:bg-red-50"
                >
                  Delete
                </button>
              </div>
            )}
          </div>
        ))}
        {state.sessions.length === 0 && (
          <p className="text-sm text-gray-400 text-center py-4">No sessions yet</p>
        )}
      </div>

      {/* Settings Panel */}
      <div className="border-t border-gray-200/30 p-3 space-y-3">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Settings</h3>

        {/* Engine Selector */}
        <div>
          <label className="text-xs text-gray-500">Agent Engine</label>
          <select
            value={state.config.engine}
            onChange={async (e) => {
              await api.setEngine(e.target.value);
              loadConfig();
            }}
            className="w-full mt-1 text-sm rounded-md border border-gray-200 px-2 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-blue-300"
          >
            <option value="langgraph">LangGraph (Teaching)</option>
            <option value="create_agent">create_agent (Production)</option>
            <option value="raw_loop">Raw Loop (Minimal)</option>
          </select>
        </div>

        {/* Memory Backend */}
        <div>
          <label className="text-xs text-gray-500">Memory Backend</label>
          <select
            value={state.config.memoryBackend}
            onChange={async (e) => {
              await api.setMemoryBackend(e.target.value);
              loadConfig();
            }}
            className="w-full mt-1 text-sm rounded-md border border-gray-200 px-2 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-blue-300"
          >
            <option value="native">Native (File-based)</option>
            <option value="mem0">Mem0 (MaaS)</option>
          </select>
        </div>

        {/* RAG Toggle */}
        <div className="flex items-center justify-between">
          <label className="text-xs text-gray-500">RAG Mode</label>
          <button
            onClick={async () => {
              await api.setRagMode(!state.config.ragMode);
              loadConfig();
            }}
            className={`relative w-10 h-5 rounded-full transition-colors ${
              state.config.ragMode ? "bg-blue-500" : "bg-gray-300"
            }`}
          >
            <span
              className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${
                state.config.ragMode ? "translate-x-5" : ""
              }`}
            />
          </button>
        </div>
      </div>
    </aside>
  );
}
