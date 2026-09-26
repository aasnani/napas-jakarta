"use client";

import type { UserContent } from "ai";
import { useEveAgent } from "eve/react";
import { AlertCircleIcon, BrainIcon, MapPinIcon, PlusIcon, SquareIcon } from "lucide-react";
import { useState } from "react";
import {
  Conversation,
  ConversationContent,
  ConversationScrollButton,
  ConversationTopFade,
} from "@/components/ai-elements/conversation";
import { Message, MessageContent } from "@/components/ai-elements/message";
import {
  PromptInput,
  PromptInputButton,
  type PromptInputMessage,
  PromptInputSubmit,
  PromptInputTextarea,
  usePromptInputAttachments,
} from "@/components/ai-elements/prompt-input";
import { Shimmer } from "@/components/ai-elements/shimmer";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { AgentMessage } from "./agent-message";
import { WEB_CHAT_AGENT } from "@/app/eve-agent";

const DEFAULT_AGENT_NAME = "web";
const AGENT_NAME = WEB_CHAT_AGENT ?? DEFAULT_AGENT_NAME;

export function AgentChat({
  embedded = false,
  selectedStation,
  sessionId,
  sessionless = false,
}: {
  readonly embedded?: boolean;
  readonly selectedStation?: string;
  readonly sessionId?: string;
  readonly sessionless?: boolean;
}) {
  const [cancellationError, setCancellationError] = useState<string>();
  const [hasInputText, setHasInputText] = useState(false);
  const [contextOpen, setContextOpen] = useState(false);
  const agent = useEveAgent({
    agent: WEB_CHAT_AGENT,
    initialSession:
      sessionId === undefined
        ? undefined
        : {
            sessionId,
            streamIndex: 0,
          },
    resume: sessionId !== undefined,
    onSessionChange(session) {
      if (sessionId === undefined && session !== undefined) {
        // Next patches window.history to navigate, which would detach the active stream.
        History.prototype.replaceState.call(
          window.history,
          window.history.state,
          "",
          `/s/${encodeURIComponent(session.sessionId)}`,
        );
      }
    },
  });

  const isBusy = agent.status === "submitted" || agent.status === "streaming";
  const isResuming = agent.status === "resuming";
  const isEmpty = agent.data.messages.length === 0;
  const lastMessage = agent.data.messages.at(-1);
  const isPendingAssistantShell =
    lastMessage?.role === "assistant" &&
    lastMessage.parts.every((part) => part.type === "step-start");
  const showPendingThinking =
    isBusy &&
    (agent.status === "submitted" || lastMessage?.role !== "assistant" || isPendingAssistantShell);
  const turnFailure = isBusy || isResuming ? undefined : getLatestTurnFailure(agent.events);
  const errorMessage = cancellationError ?? agent.error?.message ?? turnFailure;
  const hasConversationContent = sessionless || !isEmpty || errorMessage !== undefined;
  const showConversationLayout = isResuming || hasConversationContent;
  const activeSessionId = sessionId ?? agent.session?.sessionId;

  const requestCancellation = () => {
    setCancellationError(undefined);
    void agent.cancel().catch((error: unknown) => {
      setCancellationError(toErrorMessage(error));
    });
  };

  const handleSubmit = async (message: PromptInputMessage) => {
    const text = message.text.trim();
    if ((text.length === 0 && message.files.length === 0) || isResuming) return;

    setHasInputText(false);
    setCancellationError(undefined);
    const options = isBusy ? { turnPolicy: "steer" as const } : undefined;

    if (message.files.length === 0) {
      await agent.send(text, options);
      return;
    }

    const parts: UserContent = [];
    if (text.length > 0) {
      parts.push({ text, type: "text" });
    }
    for (const file of message.files) {
      parts.push({
        data: file.url,
        filename: file.filename,
        mediaType: file.mediaType,
        type: "file",
      });
    }

    await agent.send(parts, options);
  };

  const composer = (
    <PromptInput onSubmit={handleSubmit}>
      <PromptInputTextarea
        className={embedded ? "napas-prompt-textarea" : undefined}
        disabled={isResuming}
        onChange={(event) => setHasInputText(event.currentTarget.value.trim().length > 0)}
        placeholder={embedded ? "Ask about a station or air quality across Jakarta…" : "Send a message…"}
      />
      {embedded ? (
        <>
          <PromptInputButton
            aria-expanded={contextOpen}
            aria-label="Message context"
            className="napas-context-button"
            onClick={() => setContextOpen((open) => !open)}
          >
            <PlusIcon className="size-4" />
          </PromptInputButton>
          <span className="napas-context-indicator">
            <MapPinIcon className="size-3" />
            {selectedStation ?? "No station selected"} selected
          </span>
          {contextOpen ? (
            <div className="napas-context-menu" role="dialog" aria-label="Message context">
              <strong>Message context</strong>
              <span><MapPinIcon className="size-3" />Include {selectedStation ?? "the selected station"}</span>
            </div>
          ) : null}
        </>
      ) : null}
      <ComposerAction
        hasInputText={hasInputText}
        isBusy={isBusy}
        isResuming={isResuming}
        onCancel={requestCancellation}
      />
    </PromptInput>
  );

  return (
      <main
        className={cn(
          "flex h-full min-h-0 flex-col overflow-hidden bg-background text-foreground",
          !embedded && "h-dvh",
          embedded && "napas-chat-shell",
        )}
      >
      {embedded ? (
        <header className="chat-head">
          <h1 id="chat-heading">Napas assistant</h1>
          <p className="connection"><span className="connection-dot" aria-hidden="true" />Connected to monitoring data <span aria-hidden="true">·</span> Demo snapshot</p>
        </header>
      ) : null}
      {showConversationLayout && !embedded ? (
        <ChatHeader canStartNewChat={activeSessionId !== undefined} />
      ) : null}

      {showConversationLayout || embedded ? (
        <Conversation
          className={cn("min-h-0 flex-1", embedded && "napas-chat-scroll")}
          initial={sessionId === undefined ? undefined : false}
          resize={activeSessionId === undefined ? "smooth" : "instant"}
          scrollRestorationKey={
            isEmpty || activeSessionId === undefined
              ? undefined
              : `eve:web-chat-scroll:${activeSessionId}`
          }
        >
          <ConversationTopFade className="top-14" />
          <ConversationContent
            className={cn(
              "mx-auto w-full gap-6 px-4 sm:px-6",
              embedded ? "napas-chat-content max-w-none pt-4 pb-5" : "max-w-3xl pt-20 pb-36",
            )}
          >
            {embedded && isEmpty ? <DemoConversation onPrompt={(prompt) => void agent.send(prompt)} /> : null}
            {agent.data.messages.map((message, index) =>
              showPendingThinking &&
              isPendingAssistantShell &&
              message.id === lastMessage.id ? null : (
                <AgentMessage
                  canRespond={!isBusy && !isResuming}
                  isStreaming={
                    agent.status === "streaming" && index === agent.data.messages.length - 1
                  }
                  key={message.id}
                  message={message}
                  onInputResponses={(inputResponses) => {
                    setCancellationError(undefined);
                    return agent.respond(inputResponses);
                  }}
                />
              ),
            )}
            {showPendingThinking ? <PendingThinking /> : null}
            {errorMessage ? <ErrorMessage message={errorMessage} /> : null}
          </ConversationContent>
          <ConversationScrollButton />
        </Conversation>
      ) : null}

      <div
        className={cn(
          "mx-auto w-full px-4 sm:px-6",
          embedded
            ? "napas-composer-wrap shrink-0 border-t border-border/70 bg-background px-4 py-4 sm:px-5"
            : showConversationLayout
            ? "fixed bottom-0 left-1/2 z-20 max-w-3xl -translate-x-1/2 bg-gradient-to-t from-background via-background to-transparent pt-4 pb-6"
            : "flex max-w-xl flex-1 flex-col items-center justify-center gap-8 pb-[10vh]",
        )}
      >
        {!showConversationLayout && !embedded ? (
          <div className="flex flex-col items-center gap-3 text-center">
            <div className="flex size-11 items-center justify-center rounded-2xl bg-[#E7F5F2] text-[#086B68]">
              <BrainIcon className="size-5" />
            </div>
            <h2 className="font-semibold text-xl tracking-[-0.03em]">What should we explore?</h2>
            <p className="max-w-[280px] text-sm leading-6 text-muted-foreground">
              Ask about current conditions, a neighborhood, or how Jakarta&apos;s air has changed.
            </p>
            <div className="grid w-full max-w-[320px] gap-2 pt-1">
              {[
                "Which areas are most polluted right now?",
                "How is the air around Central Jakarta?",
                "Show me the latest PM2.5 picture.",
              ].map((prompt) => (
                <button
                  className="rounded-xl border border-border bg-white px-3 py-2.5 text-left text-xs text-foreground transition-colors hover:border-[#086B68] hover:bg-[#E7F5F2]"
                  key={prompt}
                  onClick={() => void agent.send(prompt)}
                  type="button"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : null}
        <div className="w-full">{composer}</div>
      </div>
    </main>
  );
}

function DemoConversation({ onPrompt }: { readonly onPrompt: (prompt: string) => void }) {
  return (
    <>
      <article className="napas-demo-message assistant">
        <div className="assistant-mark"><img src="/napas-jakarta-air-icon.png" alt="Napas Jakarta logo" /></div>
        <div>
          <div className="message-kicker">Napas assistant</div>
          <div className="message-body"><p>Hi, I can help you read Jakarta&apos;s air quality: current station readings, trends at a station, changes across the city, and practical outdoor guidance.</p><p>This screen uses illustrative readings from a demo snapshot, so it is useful for exploring the experience rather than making a live health decision.</p></div>
        </div>
      </article>
      <div className="suggestions" aria-label="Suggested questions">
        <button className="prompt-chip" onClick={() => onPrompt("Where is air quality worst right now?")} type="button">Where is air quality worst right now?</button>
        <button className="prompt-chip" onClick={() => onPrompt("Compare north and south Jakarta")} type="button">Compare north and south Jakarta</button>
        <button className="prompt-chip" onClick={() => onPrompt("Is it safe to exercise outside?")} type="button">Is it safe to exercise outside?</button>
      </div>
      <div className="thread-divider" aria-hidden="true" />
      <article className="napas-demo-message user"><div className="message-kicker">You · example</div><div className="user-bubble">How is the air around Kelapa Gading?</div></article>
      <article className="napas-demo-message assistant">
        <div className="assistant-mark"><img src="/napas-jakarta-air-icon.png" alt="Napas Jakarta logo" /></div>
        <div>
          <div className="message-kicker">Napas assistant</div>
          <div className="message-body"><p>Kelapa Gading is <strong>Moderate</strong> in this demo snapshot: ISPU 82 and PM2.5 30 µg/m³, observed at 09:20 WIB. The map highlights its monitor so you can compare nearby stations.</p>
            <div className="summary-card"><div className="summary-top"><span className="summary-title">Jakarta at a glance</span><span className="demo-label">Demo snapshot</span></div><div className="summary-metrics"><div><strong>14/16</strong><span>reporting</span></div><div><strong>8</strong><span>moderate</span></div><div><strong>4</strong><span>unhealthy</span></div></div><div className="summary-bar" aria-label="Of 14 reporting stations, 2 Good, 8 Moderate, and 4 Unhealthy"><i className="good" /><i className="moderate" /><i className="unhealthy" /></div></div>
          </div>
        </div>
      </article>
    </>
  );
}

function ComposerAction({
  hasInputText,
  isBusy,
  isResuming,
  onCancel,
}: {
  readonly hasInputText: boolean;
  readonly isBusy: boolean;
  readonly isResuming: boolean;
  readonly onCancel: () => void;
}) {
  const attachments = usePromptInputAttachments();
  const canSubmit = hasInputText || attachments.files.length > 0;

  if (!isBusy || canSubmit) {
    return <PromptInputSubmit disabled={isResuming} />;
  }

  return (
    <PromptInputButton
      aria-label="Stop"
      className="absolute right-2.5 bottom-2.5"
      onClick={onCancel}
      variant="outline"
    >
      <SquareIcon className="size-3 fill-current" />
    </PromptInputButton>
  );
}

function ErrorMessage({ message }: { readonly message: string }) {
  return (
    <Message className="max-w-full" from="assistant">
      <MessageContent>
        <div
          className="flex w-full items-start gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2.5 text-sm"
          role="alert"
        >
          <AlertCircleIcon className="mt-0.5 size-4 shrink-0 text-destructive" />
          <div>
            <p className="font-medium">Request failed</p>
            <p className="mt-0.5 text-muted-foreground">{message}</p>
          </div>
        </div>
      </MessageContent>
    </Message>
  );
}

function ChatHeader({ canStartNewChat }: { readonly canStartNewChat: boolean }) {
  return (
    <header className="pointer-events-none fixed top-0 right-0 left-0 z-20 h-14">
      <div className="relative mx-auto flex h-full w-full max-w-3xl items-center justify-center bg-background px-24">
        <span className="truncate text-muted-foreground text-sm">{AGENT_NAME}</span>
        {canStartNewChat ? (
          <Button
            aria-label="Start a new chat"
            className="pointer-events-auto fixed top-3 right-6 pr-4"
            onClick={() => window.location.assign("/s")}
            size="sm"
            type="button"
            variant="ghost"
          >
            <PlusIcon className="size-4" />
            <span className="hidden font-normal text-sm sm:inline">New chat</span>
          </Button>
        ) : null}
      </div>
    </header>
  );
}

function PendingThinking() {
  return (
    <Message aria-live="polite" from="assistant">
      <MessageContent>
        <div className="mb-4 flex w-full items-center gap-2 text-muted-foreground text-sm">
          <BrainIcon className="size-4" />
          <Shimmer duration={1}>Thinking</Shimmer>
        </div>
      </MessageContent>
    </Message>
  );
}

function toErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Unable to cancel the response.";
}

function getLatestTurnFailure(
  events: ReturnType<typeof useEveAgent>["events"],
): string | undefined {
  for (let index = events.length - 1; index >= 0; index -= 1) {
    const event = events[index];

    if (event.type === "turn.failed") {
      return event.data.code === "MODEL_CALL_FAILED"
        ? "The model is temporarily unavailable. Please try again."
        : event.data.message;
    }

    if (event.type === "turn.completed" || event.type === "turn.cancelled") {
      return undefined;
    }

    if (event.type === "message.received") {
      return undefined;
    }
  }

  return undefined;
}
