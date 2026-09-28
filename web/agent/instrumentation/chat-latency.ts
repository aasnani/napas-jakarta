import { defineInstrumentation } from "eve/instrumentation";
import { emitServerLog } from "../../lib/server-logger";

function scopeFields(scope: {
  readonly attemptId: string;
  readonly sessionId: string;
  readonly stepIndex: number;
  readonly turnId: string;
}) {
  return {
    attempt_id: scope.attemptId,
    session_id: scope.sessionId,
    step_index: scope.stepIndex,
    turn_id: scope.turnId,
  };
}

function durationFromState(state: unknown): number | undefined {
  if (typeof state !== "object" || state === null || Array.isArray(state)) return undefined;
  const startedAt = (state as { readonly startedAt?: unknown }).startedAt;
  return typeof startedAt === "number" ? Date.now() - startedAt : undefined;
}

export default defineInstrumentation({
  // Latency diagnostics need identities and timings, never prompts, tool
  // arguments, generated text, or tool results.
  tracePolicy: () => ({ emit: true, recordInputs: false, recordOutputs: false }),
  events: {
    "channel.delivery.started": (event) => {
      emitServerLog("info", "chat_request_arrival", {
        channel: event.delivery.channelName,
        request_id: event.delivery.requestId,
        root_session_id: event.rootSessionId,
        session_id: event.sessionId,
        turn_id: event.turnId,
      });
    },
    "model.call.started": (event, ctx) => {
      ctx.state.set({ startedAt: Date.now() });
      emitServerLog("info", "gemini_model_call_started", {
        idempotency_key: event.idempotencyKey,
        model: event.model.modelId,
        provider: event.model.provider,
        ...scopeFields(event.scope),
      });
    },
    "model.call.completed": (event, ctx) => {
      const state = ctx.state.get();
      emitServerLog("info", "gemini_model_call_completed", {
        duration_ms: durationFromState(state),
        finish_reason: event.finishReason,
        idempotency_key: event.idempotencyKey,
        output_tokens: event.usage.outputTokens,
        ...scopeFields(event.scope),
      });
    },
    "model.call.failed": (event, ctx) => {
      const state = ctx.state.get();
      emitServerLog("error", "gemini_model_call_failed", {
        duration_ms: durationFromState(state),
        error_type: event.error instanceof Error ? event.error.name : typeof event.error,
        idempotency_key: event.idempotencyKey,
        ...scopeFields(event.scope),
      });
    },
    "tool.call.started": (event, ctx) => {
      ctx.state.set({ startedAt: Date.now() });
      emitServerLog("info", "gemini_tool_call_started", {
        call_id: event.callId,
        idempotency_key: event.idempotencyKey,
        tool_name: event.toolName,
        ...scopeFields(event.scope),
      });
    },
    "tool.call.completed": (event, ctx) => {
      const state = ctx.state.get();
      emitServerLog("info", "gemini_tool_call_completed", {
        duration_ms: durationFromState(state),
        idempotency_key: event.idempotencyKey,
        outcome: event.output.type,
        ...scopeFields(event.scope),
      });
    },
    "tool.call.failed": (event, ctx) => {
      const state = ctx.state.get();
      emitServerLog("error", "gemini_tool_call_failed", {
        duration_ms: durationFromState(state),
        error_type: event.error instanceof Error ? event.error.name : typeof event.error,
        idempotency_key: event.idempotencyKey,
        ...scopeFields(event.scope),
      });
    },
  },
});
