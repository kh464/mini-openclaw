"use client";

import React, { createContext, useContext, useReducer, useCallback, useRef, ReactNode } from "react";
import * as api from "./api";

// Types
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  thoughtChain?: ThoughtEvent[];
  retrievalResults?: any[];
}

export interface ThoughtEvent {
  type: "tool_start" | "tool_end" | "retrieval";
  tool?: string;
  input?: any;
  output?: string;
  results?: any[];
}

interface AppState {
  sessions: api.Session[];
  activeSessionId: string | null;
  messages: ChatMessage[];
  isStreaming: boolean;
  sidebarOpen: boolean;
  config: {
    engine: string;
    memoryBackend: string;
    ragMode: boolean;
  };
}

type Action =
  | { type: "SET_SESSIONS"; sessions: api.Session[] }
  | { type: "SET_ACTIVE_SESSION"; sessionId: string | null }
  | { type: "SET_MESSAGES"; messages: ChatMessage[] }
  | { type: "ADD_MESSAGE"; message: ChatMessage }
  | { type: "UPDATE_LAST_MESSAGE"; content: string }
  | { type: "ADD_THOUGHT"; thought: ThoughtEvent }
  | { type: "SET_STREAMING"; isStreaming: boolean }
  | { type: "TOGGLE_SIDEBAR" }
  | { type: "SET_CONFIG"; config: AppState["config"] };

const initialState: AppState = {
  sessions: [],
  activeSessionId: null,
  messages: [],
  isStreaming: false,
  sidebarOpen: true,
  config: {
    engine: "langgraph",
    memoryBackend: "native",
    ragMode: false,
  },
};

function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case "SET_SESSIONS":
      return { ...state, sessions: action.sessions };
    case "SET_ACTIVE_SESSION":
      return { ...state, activeSessionId: action.sessionId };
    case "SET_MESSAGES":
      return { ...state, messages: action.messages };
    case "ADD_MESSAGE":
      return { ...state, messages: [...state.messages, action.message] };
    case "UPDATE_LAST_MESSAGE": {
      const msgs = [...state.messages];
      if (msgs.length > 0 && msgs[msgs.length - 1].role === "assistant") {
        msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], content: action.content };
      }
      return { ...state, messages: msgs };
    }
    case "ADD_THOUGHT": {
      const msgs = [...state.messages];
      if (msgs.length > 0 && msgs[msgs.length - 1].role === "assistant") {
        const last = { ...msgs[msgs.length - 1] };
        last.thoughtChain = [...(last.thoughtChain || []), action.thought];
        msgs[msgs.length - 1] = last;
      }
      return { ...state, messages: msgs };
    }
    case "SET_STREAMING":
      return { ...state, isStreaming: action.isStreaming };
    case "TOGGLE_SIDEBAR":
      return { ...state, sidebarOpen: !state.sidebarOpen };
    case "SET_CONFIG":
      return { ...state, config: action.config };
    default:
      return state;
  }
}

interface StoreContextValue {
  state: AppState;
  dispatch: React.Dispatch<Action>;
  loadSessions: () => Promise<void>;
  selectSession: (id: string) => Promise<void>;
  createNewSession: () => Promise<void>;
  deleteSession: (id: string) => Promise<void>;
  renameSession: (id: string, title: string) => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
  resendMessage: (content: string) => Promise<void>;
  loadConfig: () => Promise<void>;
}

const StoreContext = createContext<StoreContextValue | null>(null);

export function StoreProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  // Track which session the current stream belongs to
  const streamSessionRef = useRef<string | null>(null);

  const loadSessions = useCallback(async () => {
    try {
      const sessions = await api.listSessions();
      dispatch({ type: "SET_SESSIONS", sessions });
    } catch (err) {
      console.error("Failed to load sessions:", err);
    }
  }, []);

  const selectSession = useCallback(async (id: string) => {
    // If streaming to a different session, detach the stream (it continues in background)
    if (streamSessionRef.current && streamSessionRef.current !== id) {
      streamSessionRef.current = null;
      dispatch({ type: "SET_STREAMING", isStreaming: false });
    }

    dispatch({ type: "SET_ACTIVE_SESSION", sessionId: id });
    try {
      const msgs = await api.getMessages(id);
      const chatMsgs: ChatMessage[] = msgs.map((m, i) => ({
        id: `${id}-${i}`,
        role: m.role as "user" | "assistant",
        content: m.content,
        thoughtChain: m.thought_chain?.map((tc: any) => ({
          type: tc.type,
          tool: tc.tool,
          input: tc.input,
          output: tc.output,
          results: tc.results,
        })),
      }));
      dispatch({ type: "SET_MESSAGES", messages: chatMsgs });
    } catch (err) {
      console.error("Failed to load messages:", err);
    }
  }, []);

  const createNewSession = useCallback(async () => {
    try {
      const { id } = await api.createSession();
      await loadSessions();
      dispatch({ type: "SET_ACTIVE_SESSION", sessionId: id });
      dispatch({ type: "SET_MESSAGES", messages: [] });
    } catch (err) {
      console.error("Failed to create session:", err);
    }
  }, [loadSessions]);

  const deleteSession = useCallback(async (id: string) => {
    try {
      await api.deleteSession(id);
      if (state.activeSessionId === id) {
        dispatch({ type: "SET_ACTIVE_SESSION", sessionId: null });
        dispatch({ type: "SET_MESSAGES", messages: [] });
      }
      await loadSessions();
    } catch (err) {
      console.error("Failed to delete session:", err);
    }
  }, [loadSessions, state.activeSessionId]);

  const renameSession = useCallback(async (id: string, title: string) => {
    try {
      await api.renameSession(id, title);
      await loadSessions();
    } catch (err) {
      console.error("Failed to rename session:", err);
    }
  }, [loadSessions]);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!state.activeSessionId || state.isStreaming) return;

      const sessionId = state.activeSessionId;
      streamSessionRef.current = sessionId;

      // Add user message
      const userMsg: ChatMessage = {
        id: `${Date.now()}-user`,
        role: "user",
        content,
      };
      dispatch({ type: "ADD_MESSAGE", message: userMsg });

      // Add empty assistant message
      const assistantMsg: ChatMessage = {
        id: `${Date.now()}-assistant`,
        role: "assistant",
        content: "",
        thoughtChain: [],
      };
      dispatch({ type: "ADD_MESSAGE", message: assistantMsg });
      dispatch({ type: "SET_STREAMING", isStreaming: true });

      try {
        let fullContent = "";
        for await (const event of api.streamChat(content, sessionId)) {
          // If session switched away, stop dispatching to UI
          if (streamSessionRef.current !== sessionId) continue;

          switch (event.type) {
            case "token":
              fullContent += event.content || "";
              dispatch({ type: "UPDATE_LAST_MESSAGE", content: fullContent });
              break;
            case "tool_start":
              dispatch({
                type: "ADD_THOUGHT",
                thought: { type: "tool_start", tool: event.tool, input: event.input },
              });
              break;
            case "tool_end":
              dispatch({
                type: "ADD_THOUGHT",
                thought: { type: "tool_end", tool: event.tool, output: event.output },
              });
              break;
            case "retrieval":
              dispatch({
                type: "ADD_THOUGHT",
                thought: { type: "retrieval", results: event.results },
              });
              break;
            case "new_response":
              break;
            case "title_generated":
              loadSessions();
              break;
            case "done":
              // Unlock input — user-facing content is complete
              dispatch({ type: "SET_STREAMING", isStreaming: false });
              break;
          }
        }
      } catch (err) {
        console.error("Stream error:", err);
        if (streamSessionRef.current === sessionId) {
          dispatch({ type: "UPDATE_LAST_MESSAGE", content: "Error: Failed to get response." });
        }
      } finally {
        if (streamSessionRef.current === sessionId) {
          dispatch({ type: "SET_STREAMING", isStreaming: false });
          streamSessionRef.current = null;
        }
        loadSessions();
      }
    },
    [state.activeSessionId, state.isStreaming, loadSessions]
  );

  const resendMessage = useCallback(
    async (content: string) => {
      if (!state.activeSessionId || state.isStreaming) return;
      await sendMessage(content);
    },
    [state.activeSessionId, state.isStreaming, sendMessage]
  );

  const loadConfig = useCallback(async () => {
    try {
      const config = await api.getConfig();
      dispatch({ type: "SET_CONFIG", config });
    } catch (err) {
      console.error("Failed to load config:", err);
    }
  }, []);

  return (
    <StoreContext.Provider
      value={{ state, dispatch, loadSessions, selectSession, createNewSession, deleteSession, renameSession, sendMessage, resendMessage, loadConfig }}
    >
      {children}
    </StoreContext.Provider>
  );
}

export function useStore() {
  const ctx = useContext(StoreContext);
  if (!ctx) throw new Error("useStore must be used within StoreProvider");
  return ctx;
}
