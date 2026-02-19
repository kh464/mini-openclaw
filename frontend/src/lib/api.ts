const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8002";

async function apiFetch(url: string, opts?: RequestInit): Promise<Response> {
  const res = await fetch(url, opts);
  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error");
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res;
}

export interface Session {
  id: string;
  title: string;
  created_at: number;
  updated_at: number;
  message_count: number;
}

export interface Message {
  role: "user" | "assistant" | "system";
  content: string;
  tool_calls?: any[];
}

export interface SSEEvent {
  type: string;
  [key: string]: any;
}

// Sessions API
export async function listSessions(): Promise<Session[]> {
  const res = await apiFetch(`${API_BASE}/api/sessions`);
  return res.json();
}

export async function createSession(title = "New Chat"): Promise<{ id: string; title: string }> {
  const res = await apiFetch(`${API_BASE}/api/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  return res.json();
}

export async function getMessages(sessionId: string): Promise<Message[]> {
  const res = await apiFetch(`${API_BASE}/api/sessions/${sessionId}/messages`);
  const data = await res.json();
  return data.messages;
}

export async function deleteSession(sessionId: string): Promise<void> {
  await apiFetch(`${API_BASE}/api/sessions/${sessionId}`, { method: "DELETE" });
}

export async function renameSession(sessionId: string, title: string): Promise<void> {
  await apiFetch(`${API_BASE}/api/sessions/${sessionId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
}

// Chat API with SSE
export async function* streamChat(
  message: string,
  sessionId: string
): AsyncGenerator<SSEEvent> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId, stream: true }),
  });

  if (!res.body) throw new Error("No response body");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    let currentEvent = "";
    for (const line of lines) {
      if (line.startsWith("event: ")) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith("data: ")) {
        try {
          const data = JSON.parse(line.slice(6));
          yield { type: currentEvent || data.type, ...data };
        } catch {
          // skip malformed data
        }
        currentEvent = "";
      }
    }
  }
}

// Config API
export async function getConfig(): Promise<{
  engine: string;
  memoryBackend: string;
  ragMode: boolean;
}> {
  const [engine, memory, rag] = await Promise.all([
    apiFetch(`${API_BASE}/api/config/engine`).then((r) => r.json()),
    apiFetch(`${API_BASE}/api/config/memory-backend`).then((r) => r.json()),
    apiFetch(`${API_BASE}/api/config/rag-mode`).then((r) => r.json()),
  ]);
  return {
    engine: engine.engine,
    memoryBackend: memory.backend,
    ragMode: rag.enabled,
  };
}

export async function setEngine(engine: string): Promise<void> {
  await apiFetch(`${API_BASE}/api/config/engine`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ engine }),
  });
}

export async function setMemoryBackend(backend: string): Promise<void> {
  await apiFetch(`${API_BASE}/api/config/memory-backend`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ backend }),
  });
}

export async function setRagMode(enabled: boolean): Promise<void> {
  await apiFetch(`${API_BASE}/api/config/rag-mode`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
}

// Token API
export async function getSessionTokens(sessionId: string): Promise<{
  system_prompt_tokens: number;
  history_tokens: number;
  total_tokens: number;
  message_count: number;
}> {
  const res = await apiFetch(`${API_BASE}/api/tokens/session/${sessionId}`);
  return res.json();
}
