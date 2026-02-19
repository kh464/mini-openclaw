"use client";

import { useState, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import { useStore } from "@/lib/store";
import * as api from "@/lib/api";

// Dynamically import Monaco to avoid SSR issues
const MonacoEditor = dynamic(() => import("@monaco-editor/react"), { ssr: false });

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8002";

// File tree structure
const FILE_TREE = [
  {
    label: "workspace",
    children: [
      { path: "workspace/SOUL.md", label: "SOUL.md" },
      { path: "workspace/IDENTITY.md", label: "IDENTITY.md" },
      { path: "workspace/USER.md", label: "USER.md" },
      { path: "workspace/AGENTS.md", label: "AGENTS.md" },
    ],
  },
  {
    label: "memory",
    children: [
      { path: "memory/MEMORY.md", label: "MEMORY.md" },
    ],
  },
  {
    label: "skills",
    children: [
      { path: "skills/get_weather/SKILL.md", label: "get_weather/SKILL.md" },
    ],
  },
  {
    label: "root",
    children: [
      { path: "SKILLS_SNAPSHOT.md", label: "SKILLS_SNAPSHOT.md" },
    ],
  },
];

interface TokenStats {
  system_prompt_tokens: number;
  history_tokens: number;
  total_tokens: number;
  message_count: number;
}

export default function InspectorPanel() {
  const { state } = useStore();
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState("");
  const [modified, setModified] = useState(false);
  const [saving, setSaving] = useState(false);
  const [tokens, setTokens] = useState<TokenStats | null>(null);
  const [compressing, setCompressing] = useState(false);
  const [expandedDirs, setExpandedDirs] = useState<Set<string>>(new Set(["workspace", "memory"]));

  // Load file content
  const loadFile = useCallback(async (path: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/files?path=${encodeURIComponent(path)}`);
      if (res.ok) {
        const data = await res.json();
        setFileContent(data.content);
        setSelectedFile(path);
        setModified(false);
      }
    } catch (err) {
      console.error("Failed to load file:", err);
    }
  }, []);

  // Save file
  const saveFile = async () => {
    if (!selectedFile) return;
    setSaving(true);
    try {
      await fetch(`${API_BASE}/api/files`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: selectedFile, content: fileContent }),
      });
      setModified(false);
    } catch (err) {
      console.error("Failed to save file:", err);
    } finally {
      setSaving(false);
    }
  };

  // Load token stats
  useEffect(() => {
    if (!state.activeSessionId) return;
    api.getSessionTokens(state.activeSessionId).then(setTokens).catch(console.error);
  }, [state.activeSessionId, state.messages.length]);

  // Compress
  const handleCompress = async () => {
    if (!state.activeSessionId) return;
    setCompressing(true);
    try {
      await fetch(`${API_BASE}/api/sessions/${state.activeSessionId}/compress`, {
        method: "POST",
      });
      // Reload tokens
      const t = await api.getSessionTokens(state.activeSessionId);
      setTokens(t);
    } catch (err) {
      console.error("Compress failed:", err);
    } finally {
      setCompressing(false);
    }
  };

  const toggleDir = (dir: string) => {
    setExpandedDirs((prev) => {
      const next = new Set(prev);
      if (next.has(dir)) next.delete(dir);
      else next.add(dir);
      return next;
    });
  };

  return (
    <div className="flex flex-col h-full">
      {/* File Tree */}
      <div className="border-b border-gray-200/30 p-2 max-h-48 overflow-y-auto">
        <h3 className="text-xs font-semibold text-gray-500 uppercase mb-1.5">Files</h3>
        {FILE_TREE.map((group) => (
          <div key={group.label} className="mb-1">
            <button
              onClick={() => toggleDir(group.label)}
              className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 w-full text-left"
            >
              <span className={`transition-transform ${expandedDirs.has(group.label) ? "rotate-90" : ""}`}>
                &#9654;
              </span>
              <span className="font-medium">{group.label}/</span>
            </button>
            {expandedDirs.has(group.label) && (
              <div className="ml-3 space-y-0.5">
                {group.children.map((file) => (
                  <button
                    key={file.path}
                    onClick={() => loadFile(file.path)}
                    className={`block text-xs px-1.5 py-0.5 rounded w-full text-left truncate ${
                      selectedFile === file.path
                        ? "bg-blue-50 text-blue-700 font-medium"
                        : "text-gray-500 hover:bg-gray-100"
                    }`}
                  >
                    {file.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Monaco Editor */}
      <div className="flex-1 min-h-0">
        {selectedFile ? (
          <div className="h-full flex flex-col">
            <div className="flex items-center justify-between px-2 py-1 border-b border-gray-200/30 bg-gray-50/50">
              <span className="text-xs text-gray-500 truncate">{selectedFile}</span>
              <button
                onClick={saveFile}
                disabled={!modified || saving}
                className={`text-xs px-2 py-0.5 rounded transition-colors ${
                  modified
                    ? "bg-blue-500 text-white hover:bg-blue-600"
                    : "bg-gray-200 text-gray-400"
                }`}
              >
                {saving ? "Saving..." : "Save"}
              </button>
            </div>
            <div className="flex-1">
              <MonacoEditor
                height="100%"
                language={selectedFile.endsWith(".md") ? "markdown" : "plaintext"}
                value={fileContent}
                onChange={(val) => {
                  setFileContent(val || "");
                  setModified(true);
                }}
                theme="vs"
                options={{
                  minimap: { enabled: false },
                  fontSize: 12,
                  lineNumbers: "on",
                  wordWrap: "on",
                  scrollBeyondLastLine: false,
                  padding: { top: 8 },
                }}
              />
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-xs text-gray-400">
            Select a file to edit
          </div>
        )}
      </div>

      {/* Token Stats */}
      <div className="border-t border-gray-200/30 p-2 space-y-1.5">
        <h3 className="text-xs font-semibold text-gray-500 uppercase">Token Stats</h3>
        {tokens ? (
          <>
            <div className="grid grid-cols-2 gap-1 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-400">System:</span>
                <span className="font-mono">{tokens.system_prompt_tokens.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">History:</span>
                <span className="font-mono">{tokens.history_tokens.toLocaleString()}</span>
              </div>
              <div className="col-span-2 flex justify-between">
                <span className="text-gray-400">Total:</span>
                <span className="font-mono font-semibold">{tokens.total_tokens.toLocaleString()}</span>
              </div>
            </div>
            <div className="flex items-center justify-between mt-1">
              <span className="text-xs text-gray-400">{tokens.message_count} messages</span>
              <button
                onClick={handleCompress}
                disabled={compressing || tokens.message_count < 4}
                className="text-xs px-2 py-0.5 rounded bg-orange-100 text-orange-600 hover:bg-orange-200 disabled:opacity-40 transition-colors"
              >
                {compressing ? "Compressing..." : "Compress"}
              </button>
            </div>
          </>
        ) : (
          <p className="text-xs text-gray-400">
            {state.activeSessionId ? "Loading..." : "Select a session"}
          </p>
        )}
      </div>
    </div>
  );
}
