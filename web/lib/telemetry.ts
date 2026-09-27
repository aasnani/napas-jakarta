type ChatTurnTelemetry = {
  readonly answer: string;
  readonly conversation_turn: number;
  readonly history_messages: number;
  readonly interaction_id: string;
  readonly question: string;
  readonly session_id: string;
};

type FeedbackTelemetry = {
  readonly feedback: "negative" | "positive";
  readonly interaction_id: string;
  readonly session_id: string;
};

export function recordChatTurn(payload: ChatTurnTelemetry): void {
  void sendTelemetry({ payload, type: "turn" });
}

export function recordFeedback(payload: FeedbackTelemetry): void {
  void sendTelemetry({ payload, type: "feedback" });
}

async function sendTelemetry(payload: Record<string, unknown>): Promise<void> {
  try {
    await fetch("/api/telemetry", {
      body: JSON.stringify(payload),
      headers: { "content-type": "application/json" },
      keepalive: true,
      method: "POST",
    });
  } catch {
    // Telemetry must never interrupt or visibly fail the chat experience.
  }
}
