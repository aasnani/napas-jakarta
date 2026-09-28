"use client";

import type {
  EveAuthorizationPart,
  EveDynamicToolPart,
  EveMessage,
  EveMessageInputRequest,
  EveMessagePart,
} from "eve/react";
import { useCallback, useEffect, useRef, useState, type ComponentProps } from "react";
import {
  ArrowRightIcon,
  CheckCircleIcon,
  CheckIcon,
  ExternalLinkIcon,
  FileIcon,
  ImageIcon,
  KeyRoundIcon,
  ThumbsDownIcon,
  ThumbsUpIcon,
  XCircleIcon,
} from "lucide-react";
import { Message, MessageContent, MessageResponse } from "@/components/ai-elements/message";
import {
  Question,
  QuestionInput,
  QuestionOption,
  QuestionOptions,
  QuestionPrompt,
  type QuestionResponse,
  QuestionSubmit,
  type QuestionValue,
} from "@/components/ai-elements/question";
import { Reasoning, ReasoningContent, ReasoningTrigger } from "@/components/ai-elements/reasoning";
import { Button } from "@/components/ui/button";
import { getUiCopy, type Language } from "@/lib/i18n";
import { normalizeAssistantMarkdown } from "@/lib/assistant-markdown";
import { revealPacedText } from "@/lib/paced-text";
import { extractSourceCitations, type SourceCitation } from "@/lib/source-citations";
import { recordFeedback } from "@/lib/telemetry";
import { trackNapasEvent } from "@/lib/analytics";
import { cn } from "@/lib/utils";

export type AgentInputResponse = {
  readonly optionId?: string;
  readonly requestId: string;
  readonly text?: string;
};

type EveFilePart = Extract<EveMessagePart, { type: "file" }>;

export function AgentMessage({
  canRespond,
  isStreaming,
  isLatest,
  language,
  message,
  onInputResponses,
  sessionId,
}: {
  readonly canRespond: boolean;
  readonly isLatest: boolean;
  readonly isStreaming: boolean;
  readonly language: Language;
  readonly message: EveMessage;
  readonly onInputResponses: (responses: readonly AgentInputResponse[]) => void | Promise<void>;
  readonly sessionId: string;
}) {
  const lastTextIndex = message.parts.reduce(
    (last, part, index) => (part.type === "text" ? index : last),
    -1,
  );
  const hasAssistantText =
    message.role === "assistant" &&
    message.parts.some((part) => part.type === "text" && part.text.length > 0);
  const pacedTurnRef = useRef(isStreaming && message.role === "assistant");
  if (isStreaming && message.role === "assistant") {
    pacedTurnRef.current = true;
  }
  const shouldPaceText = isLatest && message.role === "assistant" && pacedTurnRef.current;
  const [isPacingText, setIsPacingText] = useState(() => shouldPaceText && hasAssistantText);
  const sourceCitations = Array.from(
    new Map(
      message.parts
        .filter((part): part is Extract<EveMessagePart, { type: "dynamic-tool" }> => part.type === "dynamic-tool")
        .flatMap((part) => extractSourceCitations(part.output))
        .map((source) => [source.url, source] as const),
    ).values(),
  );

  useEffect(() => {
    if (!shouldPaceText) {
      setIsPacingText(false);
    }
  }, [shouldPaceText]);

  return (
    <Message
      className={cn("napas-agent-message", isStreaming && "napas-agent-message-streaming")}
      data-optimistic={message.metadata?.optimistic ? "true" : undefined}
      from={message.role}
    >
      <MessageContent>
        {message.parts.map((part, index) =>
          hasAssistantText && part.type === "reasoning" ? null : (
            <AgentMessagePart
              canRespond={canRespond}
              key={partKey(part, index)}
              onInputResponses={onInputResponses}
              onPacingChange={setIsPacingText}
              part={part}
              paceText={shouldPaceText && index === lastTextIndex}
              sourceCitations={sourceCitations}
              language={language}
            />
          ),
        )}
        <SourceCitationList language={language} sources={sourceCitations} />
        {hasAssistantText && isLatest && canRespond && !isStreaming && !isPacingText ? (
          <FeedbackActions interactionId={message.id} language={language} sessionId={sessionId} />
        ) : null}
      </MessageContent>
    </Message>
  );
}

function FeedbackActions({ interactionId, language, sessionId }: { readonly interactionId: string; readonly language: Language; readonly sessionId: string }) {
  const copy = getUiCopy(language);
  const [feedback, setFeedback] = useState<"down" | "up">();
  const [isFading, setIsFading] = useState(false);
  const [showThanks, setShowThanks] = useState(false);

  useEffect(() => {
    if (!feedback) return;

    const fadeTimer = window.setTimeout(() => setIsFading(true), 420);
    const thanksTimer = window.setTimeout(() => setShowThanks(true), 700);
    return () => {
      window.clearTimeout(fadeTimer);
      window.clearTimeout(thanksTimer);
    };
  }, [feedback]);

  const submitFeedback = (value: "down" | "up") => {
    if (feedback) return;
    setFeedback(value);
    trackNapasEvent("assistant_feedback_submitted", {
      rating: value === "up" ? "positive" : "negative",
    });
    recordFeedback({
      feedback: value === "up" ? "positive" : "negative",
      interaction_id: interactionId,
      session_id: sessionId,
    });
  };

  if (showThanks) {
    return (
      <div aria-label={copy.message.feedbackConfirmation} className="napas-feedback napas-feedback-thanks-message" role="status">
        {copy.message.thankYou}
      </div>
    );
  }

  return (
    <div
      aria-label={copy.message.answerFeedback}
      className={cn("napas-feedback", feedback && "has-feedback", isFading && "is-fading")}
      role="group"
    >
      <span>{copy.message.helpful}</span>
      <button
        aria-label={copy.message.helpfulLabel}
        aria-pressed={feedback === "up"}
        disabled={feedback !== undefined}
        className={cn(feedback === "up" && "is-selected")}
        onClick={() => submitFeedback("up")}
        type="button"
      >
        {feedback === "up" ? <CheckIcon /> : <ThumbsUpIcon />}
      </button>
      <button
        aria-label={copy.message.notHelpfulLabel}
        aria-pressed={feedback === "down"}
        disabled={feedback !== undefined}
        className={cn(feedback === "down" && "is-selected")}
        onClick={() => submitFeedback("down")}
        type="button"
      >
        {feedback === "down" ? <CheckIcon /> : <ThumbsDownIcon />}
      </button>
    </div>
  );
}

function AgentMessagePart({
  canRespond,
  language,
  onInputResponses,
  onPacingChange,
  part,
  paceText,
  sourceCitations,
}: {
  readonly canRespond: boolean;
  readonly language: Language;
  readonly onInputResponses: (responses: readonly AgentInputResponse[]) => void | Promise<void>;
  readonly onPacingChange: (isPacing: boolean) => void;
  readonly part: EveMessagePart;
  readonly paceText: boolean;
  readonly sourceCitations: readonly SourceCitation[];
}) {
  switch (part.type) {
    case "step-start":
      return null;
    case "text":
      return (
        <PacedAssistantText
          onPacingChange={onPacingChange}
          shouldPace={paceText}
          sourceCitations={sourceCitations}
          text={part.text}
        />
      );
    case "reasoning":
      return (
        <Reasoning defaultOpen isStreaming={part.state === "streaming"}>
          <ReasoningTrigger
            getThinkingMessage={(isStreaming, duration) => {
              const copy = getUiCopy(language);
              if (isStreaming || duration === 0) {
                return <span>{copy.chat.thinking}</span>;
              }
              if (duration === undefined) {
                return <span>{copy.message.thoughtForFew}</span>;
              }
              return <span>{copy.message.thoughtFor} {duration} {copy.message.seconds}</span>;
            }}
          />
          <ReasoningContent>{part.text}</ReasoningContent>
        </Reasoning>
      );
    case "file":
      return <AttachmentPart language={language} part={part} />;
    case "authorization":
      return <AuthorizationPrompt language={language} part={part} />;
    case "dynamic-tool": {
      const inputRequest = part.toolMetadata?.eve?.inputRequest;
      if (inputRequest?.kind === "question") {
        return (
          <QuestionRequest
            canRespond={canRespond}
            inputRequest={inputRequest}
            inputResponse={part.toolMetadata?.eve?.inputResponse}
            language={language}
            onInputResponses={onInputResponses}
          />
        );
      }

      return (
        <InputRequestActions
          canRespond={canRespond}
          language={language}
          part={part}
          onInputResponses={onInputResponses}
        />
      );
    }
  }
}

function SourceCitationList({ language, sources }: { readonly language: Language; readonly sources: readonly SourceCitation[] }) {
  if (sources.length === 0) return null;

  const copy = getUiCopy(language);

  return (
    <details className="napas-source-citations">
      <summary
        aria-label={sources.length === 1 ? copy.message.showSource : copy.message.showSources}
        onClick={(event) => {
          // Keep keyboard focus visible, but do not leave a mouse-click focus ring
          // sitting on the disclosure after the user opens the source list.
          if (event.detail > 0) {
            event.currentTarget.blur();
          }
        }}
      >
        <span>{copy.message.sources}</span>
        <span>{sources.length === 1 ? `1 ${copy.message.source}` : `${sources.length} ${copy.message.sourcesPlural}`}</span>
      </summary>
      <div className="napas-source-citations-list">
        {sources.map((source) => (
          <a
            className="napas-source-citation"
            href={source.url}
            key={`${source.id}:${source.url}`}
            rel="noreferrer noopener"
            target="_blank"
          >
            <span className="napas-source-citation-copy">
              <strong>{source.title}</strong>
              <span>{source.role ?? source.author ?? source.url}</span>
            </span>
            <ExternalLinkIcon aria-hidden="true" />
          </a>
        ))}
      </div>
    </details>
  );
}

function PacedAssistantText({
  onPacingChange,
  shouldPace,
  sourceCitations,
  text,
}: {
  readonly onPacingChange: (isPacing: boolean) => void;
  readonly shouldPace: boolean;
  readonly sourceCitations: readonly SourceCitation[];
  readonly text: string;
}) {
  const pacedText = usePacedText(normalizeAssistantMarkdown(text), shouldPace);
  const components = sourceCitations.length > 0
    ? {
        inlineCode: ({ children, node: _node, ...props }: ComponentProps<"code"> & { node?: unknown }) => {
          const label = typeof children === "string" ? children.trim() : "";
          const normalizedLabel = label.replace(/^www\./i, "").toLowerCase();
          const source = sourceCitations.find((candidate) => {
            try {
              return new URL(candidate.url).hostname.replace(/^www\./i, "").toLowerCase() === normalizedLabel;
            } catch {
              return false;
            }
          });

          if (!source) {
            return <code {...props}>{children}</code>;
          }

          return (
            <a
              className="wrap-anywhere font-medium text-primary underline"
              href={source.url}
              rel="noreferrer noopener"
              target="_blank"
            >
              {children}
            </a>
          );
        },
      }
    : undefined;

  useEffect(() => {
    onPacingChange(pacedText.isPacing);
  }, [onPacingChange, pacedText.isPacing]);

  return (
    <MessageResponse
      caret="block"
      components={components}
      isAnimating={pacedText.isPacing}
    >
      {pacedText.text}
    </MessageResponse>
  );
}

function usePacedText(targetText: string, shouldPace: boolean): {
  readonly isPacing: boolean;
  readonly text: string;
} {
  const [reducedMotion, setReducedMotion] = useState(false);
  const pacePresentation = shouldPace && !reducedMotion;
  const [visibleText, setVisibleText] = useState(() =>
    pacePresentation ? targetText.slice(0, Math.min(targetText.length, 12)) : targetText,
  );
  const targetRef = useRef(targetText);
  const visibleRef = useRef(visibleText);
  const characterBudgetRef = useRef(0);
  const intervalRef = useRef<number | null>(null);
  const lastTickTimeRef = useRef<number | null>(null);

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return;
    }

    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const updatePreference = () => setReducedMotion(mediaQuery.matches);
    updatePreference();
    mediaQuery.addEventListener?.("change", updatePreference);

    return () => mediaQuery.removeEventListener?.("change", updatePreference);
  }, []);

  const stopPacing = useCallback(() => {
    if (typeof window !== "undefined" && intervalRef.current !== null) {
      window.clearInterval(intervalRef.current);
    }
    intervalRef.current = null;
    lastTickTimeRef.current = null;
    characterBudgetRef.current = 0;
  }, []);

  const startPacing = useCallback(() => {
    if (typeof window === "undefined" || intervalRef.current !== null) {
      return;
    }

    lastTickTimeRef.current = Date.now();
    intervalRef.current = window.setInterval(() => {
      const now = Date.now();
      const previousTickTime = lastTickTimeRef.current ?? now;
      const step = revealPacedText({
        characterBudget: characterBudgetRef.current,
        elapsedMs: now - previousTickTime,
        targetText: targetRef.current,
        visibleText: visibleRef.current,
      });
      lastTickTimeRef.current = now;
      characterBudgetRef.current = step.characterBudget;

      if (step.text !== visibleRef.current) {
        visibleRef.current = step.text;
        setVisibleText(step.text);
      }

      if (step.text === targetRef.current) {
        stopPacing();
      }
    }, 16);
  }, [stopPacing]);

  useEffect(() => {
    targetRef.current = targetText;

    if (!pacePresentation && visibleRef.current !== targetText) {
      visibleRef.current = targetText;
      setVisibleText(targetText);
      stopPacing();
      return;
    }

    if (!targetText.startsWith(visibleRef.current)) {
      const nextText = pacePresentation ? "" : targetText;
      visibleRef.current = nextText;
      characterBudgetRef.current = 0;
      setVisibleText(nextText);
    }

    if (visibleRef.current !== targetText) {
      startPacing();
    }
  }, [pacePresentation, startPacing, stopPacing, targetText]);

  useEffect(
    () => stopPacing,
    [stopPacing],
  );

  return {
    isPacing: visibleText !== targetText,
    text: visibleText,
  };
}

function QuestionRequest({
  canRespond,
  inputRequest,
  inputResponse,
  language,
  onInputResponses,
}: {
  readonly canRespond: boolean;
  readonly inputRequest: EveMessageInputRequest;
  readonly inputResponse?: AgentInputResponse;
  readonly language: Language;
  readonly onInputResponses: (responses: readonly AgentInputResponse[]) => void | Promise<void>;
}) {
  const copy = getUiCopy(language);
  const hasOptions = (inputRequest.options?.length ?? 0) > 0;
  const acceptsFreeform = inputRequest.allowFreeform === true || !hasOptions;
  const [questionValue, setQuestionValue] = useState<QuestionValue>({
    selectedValues: inputResponse?.optionId ? [inputResponse.optionId] : [],
    text: inputResponse?.text ?? "",
  });

  const submitOption = (optionId: string) => {
    setQuestionValue((value) => ({ ...value, selectedValues: [optionId] }));
    return onInputResponses([
      {
        optionId,
        requestId: inputRequest.requestId,
      },
    ]);
  };

  const submitResponse = ({ selectedValues, text }: QuestionResponse) =>
    onInputResponses([
      {
        optionId: selectedValues[0],
        requestId: inputRequest.requestId,
        text,
      },
    ]);

  return (
    <Question
      disabled={!canRespond || inputResponse !== undefined}
      onSubmit={submitResponse}
      onValueChange={setQuestionValue}
      value={questionValue}
    >
      <QuestionPrompt>{inputRequest.prompt}</QuestionPrompt>
      {hasOptions ? (
        <QuestionOptions className="flex-col items-stretch" aria-label={inputRequest.prompt}>
          {inputRequest.options?.map((option, index) => (
            <QuestionOption
              className="justify-start px-3 py-2 text-left"
              key={option.id}
              onClick={() => void submitOption(option.id)}
              value={option.id}
            >
              <span className="min-w-0 flex-1">
                <span className="block text-foreground text-sm leading-tight">{option.label}</span>
                {option.description ? (
                  <span className="block text-sm text-muted-foreground leading-tight">
                    {option.description}
                  </span>
                ) : null}
              </span>
              {inputResponse === undefined ? (
                <span aria-hidden="true" className="relative size-6 shrink-0">
                  <span className="absolute inset-0 flex items-center justify-center rounded-full bg-foreground/8 text-xs text-muted-foreground transition-opacity group-hover/option:opacity-0 group-focus-visible/option:opacity-0">
                    {index + 1}
                  </span>
                  <ArrowRightIcon className="absolute top-1/2 left-1/2 size-4 -translate-x-1/2 -translate-y-1/2 text-muted-foreground opacity-0 transition-[color,opacity] group-hover/option:text-foreground group-hover/option:opacity-100 group-focus-visible/option:opacity-100" />
                </span>
              ) : (
                <CheckIcon className="size-4 shrink-0 opacity-0 transition-opacity group-data-[state=checked]/option:opacity-100" />
              )}
            </QuestionOption>
          ))}
        </QuestionOptions>
      ) : null}
      {acceptsFreeform ? (
        <div className="relative">
          <QuestionInput
            aria-label={copy.message.answer}
            className={inputResponse === undefined ? "pr-12 pb-12" : undefined}
            placeholder={copy.message.typeAnswer}
          />
          {inputResponse === undefined && questionValue.text.trim().length > 0 ? (
            <QuestionSubmit
                aria-label={copy.message.answer}
              className="absolute right-2 bottom-2"
              size="icon-sm"
            >
              <ArrowRightIcon />
            </QuestionSubmit>
          ) : null}
        </div>
      ) : null}
    </Question>
  );
}

function AttachmentPart({ language, part }: { readonly language: Language; readonly part: EveFilePart }) {
  const label = part.filename ?? getUiCopy(language).message.attachment;
  const detail = [part.mediaType, formatBytes(part.size)].filter(Boolean).join(" - ");
  const isImage = part.mediaType.startsWith("image/") && part.url !== undefined;
  const Icon = isImage ? ImageIcon : FileIcon;
  const body = (
    <span className="flex max-w-sm items-center gap-3 rounded-md border bg-background/60 p-2 text-sm">
      {isImage ? (
        <img alt={label} className="size-12 shrink-0 rounded-sm object-cover" src={part.url} />
      ) : (
        <span className="flex size-10 shrink-0 items-center justify-center rounded-sm bg-muted text-muted-foreground">
          <Icon className="size-4" />
        </span>
      )}
      <span className="min-w-0 flex-1">
        <span className="block truncate font-medium">{label}</span>
        {detail ? <span className="block truncate text-muted-foreground">{detail}</span> : null}
      </span>
      {part.url ? <ExternalLinkIcon className="size-4 shrink-0 text-muted-foreground" /> : null}
    </span>
  );

  return part.url ? (
    <a href={part.url} rel="noreferrer" target="_blank">
      {body}
    </a>
  ) : (
    body
  );
}

function AuthorizationPrompt({ language, part }: { readonly language: Language; readonly part: EveAuthorizationPart }) {
  const copy = getUiCopy(language);
  const isAuthorized = part.state === "completed" && part.outcome === "authorized";
  const isCompleted = part.state === "completed";
  const Icon = isAuthorized ? CheckCircleIcon : isCompleted ? XCircleIcon : KeyRoundIcon;
  const instructions = part.authorization?.instructions;
  const shouldShowInstructions = instructions !== undefined && instructions !== part.description;

  return (
    <div
      className={cn(
        "space-y-3 rounded-md border p-3",
        isAuthorized
          ? "border-emerald-500/30 bg-emerald-500/5"
          : isCompleted
            ? "border-destructive/30 bg-destructive/5"
            : "border-blue-500/30 bg-blue-500/5",
      )}
    >
      <div className="flex items-start gap-3">
        <span
          className={cn(
            "mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full",
            isAuthorized
              ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
              : isCompleted
                ? "bg-destructive/10 text-destructive"
                : "bg-blue-500/10 text-blue-700 dark:text-blue-300",
          )}
        >
          <Icon className="size-4" />
        </span>
        <div className="min-w-0 flex-1 space-y-2">
          <p className="font-medium text-sm">{authorizationTitle(part, language)}</p>
          <p className="text-muted-foreground text-sm">{authorizationDescription(part, language)}</p>
          {shouldShowInstructions ? (
            <p className="text-muted-foreground text-sm">{instructions}</p>
          ) : null}
          {part.state === "required" && part.authorization?.userCode ? (
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="text-muted-foreground">{copy.message.code}</span>
              <code className="rounded-md bg-background px-2 py-1 font-mono">
                {part.authorization.userCode}
              </code>
            </div>
          ) : null}
          {part.state === "required" && part.authorization?.url ? (
            <Button asChild size="sm">
              <a href={part.authorization.url} rel="noreferrer" target="_blank">
                <ExternalLinkIcon className="size-4" />
                {copy.message.signInWith} {part.displayName}
              </a>
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function authorizationTitle(part: EveAuthorizationPart, language: Language): string {
  if (part.state === "required") {
    return language === "id" ? `Hubungkan ${part.displayName}` : `Connect ${part.displayName}`;
  }
  if (part.outcome === "authorized") {
    return language === "id" ? `${part.displayName} terhubung` : `${part.displayName} connected`;
  }
  return language === "id"
    ? `Otorisasi ${part.displayName} ${formatAuthorizationOutcome(part.outcome, language)}`
    : `${part.displayName} authorization ${formatAuthorizationOutcome(part.outcome, language)}`;
}

function authorizationDescription(part: EveAuthorizationPart, language: Language): string {
  if (part.state === "required") {
    return part.description;
  }
  if (part.outcome === "authorized") {
    return language === "id" ? `${part.displayName} terhubung.` : `${part.displayName} connected.`;
  }
  const tail = part.reason !== undefined ? ` (${part.reason})` : "";
  return language === "id"
    ? `Otorisasi ${part.displayName} ${formatAuthorizationOutcome(part.outcome, language)}${tail}.`
    : `${part.displayName} authorization ${formatAuthorizationOutcome(part.outcome, language)}${tail}.`;
}

function formatAuthorizationOutcome(outcome: NonNullable<EveAuthorizationPart["outcome"]>, language: Language): string {
  switch (outcome) {
    case "authorized":
      return language === "id" ? "berhasil" : "authorized";
    case "declined":
      return language === "id" ? "ditolak" : "declined";
    case "failed":
      return language === "id" ? "gagal" : "failed";
    case "timed-out":
      return language === "id" ? "kedaluwarsa" : "timed out";
  }
}

function formatBytes(size: number | undefined): string | undefined {
  if (size === undefined) {
    return undefined;
  }
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function InputRequestActions({
  canRespond,
  language,
  onInputResponses,
  part,
}: {
  readonly canRespond: boolean;
  readonly language: Language;
  readonly onInputResponses: (responses: readonly AgentInputResponse[]) => void | Promise<void>;
  readonly part: EveDynamicToolPart;
}) {
  const copy = getUiCopy(language);
  const inputRequest = part.toolMetadata?.eve?.inputRequest;
  if (!inputRequest) {
    return null;
  }

  const inputResponse = part.toolMetadata?.eve?.inputResponse;
  const selectedOption = inputRequest.options?.find(
    (option) => option.id === inputResponse?.optionId,
  );

  return (
    <div className="space-y-3 rounded-md border border-yellow-500/30 bg-yellow-500/5 p-3">
      <p className="text-muted-foreground text-sm">{inputRequest.prompt}</p>
      {inputResponse ? (
        <p className="font-medium text-sm">
          {copy.message.responded} {selectedOption?.label ?? inputResponse.text ?? inputResponse.optionId}
        </p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {inputRequest.options?.map((option) => (
            <Button
              disabled={!canRespond}
              key={option.id}
              onClick={() => {
                void onInputResponses([
                  {
                    optionId: option.id,
                    requestId: inputRequest.requestId,
                  },
                ]);
              }}
              size="sm"
              type="button"
              variant={option.style === "danger" ? "destructive" : "default"}
            >
              {option.label}
            </Button>
          ))}
        </div>
      )}
    </div>
  );
}

function partKey(part: EveMessagePart, index: number): string {
  switch (part.type) {
    case "authorization":
      return `authorization:${part.turnId}:${part.stepIndex}:${part.name}`;
    case "dynamic-tool":
      return part.toolCallId;
    default:
      return `${part.type}:${index}`;
  }
}
