"use client";

import { useState, useCallback } from "react";
import Sidebar from "@/components/layout/Sidebar";
import ChatPanel from "@/components/chat/ChatPanel";
import ResizeHandle from "@/components/layout/ResizeHandle";
import InspectorPanel from "@/components/editor/InspectorPanel";
import { useStore } from "@/lib/store";

export default function Home() {
  const { state } = useStore();
  const [sidebarWidth, setSidebarWidth] = useState(280);
  const [inspectorWidth, setInspectorWidth] = useState(320);

  const handleSidebarResize = useCallback((delta: number) => {
    setSidebarWidth((w) => Math.max(200, Math.min(400, w + delta)));
  }, []);

  const handleInspectorResize = useCallback((delta: number) => {
    setInspectorWidth((w) => Math.max(200, Math.min(500, w - delta)));
  }, []);

  return (
    <div className="flex h-full">
      {/* Left: Sidebar */}
      {state.sidebarOpen && (
        <>
          <div style={{ width: sidebarWidth, flexShrink: 0 }}>
            <Sidebar />
          </div>
          <ResizeHandle onResize={handleSidebarResize} />
        </>
      )}

      {/* Center: Chat */}
      <div className="flex-1 min-w-0">
        <ChatPanel />
      </div>

      {/* Right: Inspector */}
      <ResizeHandle onResize={handleInspectorResize} />
      <div
        style={{ width: inspectorWidth, flexShrink: 0 }}
        className="border-l border-gray-200/50"
      >
        <InspectorPanel />
      </div>
    </div>
  );
}
