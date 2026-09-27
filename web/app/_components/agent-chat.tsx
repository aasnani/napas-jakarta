"use client";

import type { UserContent } from "ai";
import type { EveMessage } from "eve/react";
import { useEveAgent } from "eve/react";
import {
  AlertCircleIcon,
  BookOpenIcon,
  BrainIcon,
  ChevronDownIcon,
  MapIcon,
  MapPinIcon,
  SendHorizontalIcon,
  SquareIcon,
  XIcon,
} from "lucide-react";
import { useEffect, useRef, useState, type RefObject } from "react";
import {
  Conversation,
  ConversationContent,
  ConversationScrollAccessibility,
  ConversationScrollButton,
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
import { getUiCopy, localizedCategory, localizedDistrict, replaceCopy, type Language } from "@/lib/i18n";
import { recordChatTurn } from "@/lib/telemetry";
import {
  buildNapasClientContext,
  findTopic,
  getLocalizedTopicCopy,
  getLocalizedTopicGroupCopy,
  getTopicSourceLabels,
  TOPIC_GROUPS,
  type TopicCopy,
  type TopicOption,
} from "@/lib/topics";
import { getSuggestedQuestions } from "@/lib/suggestions";
import { shouldShowPendingThinking, shouldShowSuggestedQuestions } from "@/lib/chat-state";
import type { DemoStation } from "@/lib/napas";
import { AgentMessage } from "./agent-message";

export function AgentChat({
  language,
  isLegendOpen,
  isMapOpen,
  onMapToggle,
  onLegendOpen,
  onStationClear,
  onStationSelect,
  prefillPrompt,
  selectedStation,
  selectedStationId,
  stationOptions,
}: {
  readonly language: Language;
  readonly isLegendOpen: boolean;
  readonly isMapOpen: boolean;
  readonly onMapToggle: () => void;
  readonly onLegendOpen: () => void;
  readonly onStationClear: () => void;
  readonly onStationSelect: (station: DemoStation) => void;
  readonly prefillPrompt?: { readonly id: number; readonly text: string };
  readonly selectedStation?: string;
  readonly selectedStationId?: string;
  readonly stationOptions: readonly DemoStation[];
}) {
  const copy = getUiCopy(language);
  const [cancellationError, setCancellationError] = useState<string>();
  const [hasInputText, setHasInputText] = useState(false);
  const [inputText, setInputText] = useState("");
  const [contextOpen, setContextOpen] = useState(false);
  const [selectedTopicId, setSelectedTopicId] = useState<string>();
  const [stationMenuOpen, setStationMenuOpen] = useState(false);
  const [topicMenuOpen, setTopicMenuOpen] = useState(false);
  const stationPickerRef = useRef<HTMLDivElement>(null);
  const topicPickerRef = useRef<HTMLDivElement>(null);
  const appliedPrefillId = useRef<number | undefined>(undefined);
  const agent = useEveAgent();
  const selectedTopic = findTopic(selectedTopicId);
  const localizedTopic = selectedTopic ? getLocalizedTopicCopy(selectedTopic, language) : undefined;
  const suggestedQuestions = getSuggestedQuestions(localizedTopic, selectedStation, language);

  const isBusy = agent.status === "submitted" || agent.status === "streaming";
  const isResuming = agent.status === "resuming";
  const isEmpty = agent.data.messages.length === 0;
  const lastMessage = agent.data.messages.at(-1);
  const showPendingThinking = shouldShowPendingThinking({ isBusy, isResuming });
  const turnFailure = isBusy || isResuming ? undefined : getLatestTurnFailure(agent.events, language);
  const errorMessage = cancellationError ?? localizeAgentError(agent.error?.message, language) ?? turnFailure;
  const anonymousSessionId = useRef(createAnonymousSessionId());
  const telemetrySessionId = anonymousSessionId.current;
  const recordedTurnIds = useRef(new Set<string>());
  const latestUserMessage = [...agent.data.messages].reverse().find((message) => message.role === "user");
  const latestAssistantMessage = lastMessage?.role === "assistant" ? lastMessage : undefined;
  const latestQuestion = latestUserMessage ? messageText(latestUserMessage) : "";
  const latestAnswer = latestAssistantMessage ? messageText(latestAssistantMessage) : "";
  const showSuggestedQuestions = shouldShowSuggestedQuestions({
    hasAssistantAnswer: latestAnswer.length > 0,
    isBusy,
    isEmpty,
    isResuming,
  });

  useEffect(() => {
    if (!prefillPrompt || appliedPrefillId.current === prefillPrompt.id) return;

    appliedPrefillId.current = prefillPrompt.id;
    setInputText(prefillPrompt.text);
    setHasInputText(true);

    const frame = window.requestAnimationFrame(() => {
      const textarea = document.getElementById("napas-composer-input");
      if (!(textarea instanceof HTMLTextAreaElement)) return;
      textarea.focus();
      textarea.setSelectionRange(textarea.value.length, textarea.value.length);
    });

    return () => window.cancelAnimationFrame(frame);
  }, [prefillPrompt]);

  useEffect(() => {
    if (isBusy || isResuming || latestAssistantMessage === undefined || latestQuestion.length === 0 || latestAnswer.length === 0) {
      return;
    }
    if (recordedTurnIds.current.has(latestAssistantMessage.id)) {
      return;
    }

    recordedTurnIds.current.add(latestAssistantMessage.id);
    recordChatTurn({
      answer: latestAnswer,
      conversation_turn: agent.data.messages.filter((message) => message.role === "user").length,
      history_messages: agent.data.messages.length,
      interaction_id: latestAssistantMessage.id,
      question: latestQuestion,
      session_id: telemetrySessionId,
    });
  }, [
    agent.data.messages,
    isBusy,
    isResuming,
    latestAnswer,
    latestAssistantMessage,
    latestQuestion,
    telemetrySessionId,
  ]);

  useEffect(() => {
    if (!topicMenuOpen && !stationMenuOpen) return;

    const handlePointerDown = (event: PointerEvent) => {
      if (
        event.target instanceof Node &&
        !topicPickerRef.current?.contains(event.target) &&
        !stationPickerRef.current?.contains(event.target)
      ) {
        setTopicMenuOpen(false);
        setStationMenuOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setTopicMenuOpen(false);
        setStationMenuOpen(false);
      }
    };

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [stationMenuOpen, topicMenuOpen]);

  const handleMapToggle = () => {
    setStationMenuOpen(false);
    setTopicMenuOpen(false);
    onMapToggle();
  };

  const handleStationSelect = (station: DemoStation) => {
    setStationMenuOpen(false);
    onStationSelect(station);
  };

  const requestCancellation = () => {
    setCancellationError(undefined);
    void agent.cancel().catch((error: unknown) => {
      setCancellationError(toErrorMessage(error, language));
    });
  };

  const sendText = async (text: string) => {
    const normalizedText = text.trim();
    if (normalizedText.length === 0 || isResuming) return;

    setInputText("");
    setHasInputText(false);
    setCancellationError(undefined);

    try {
      await agent.send(normalizedText, buildSendOptions());
    } catch (error: unknown) {
      setCancellationError(toErrorMessage(error, language));
    }
  };

  const buildSendOptions = () => ({
    ...(isBusy ? { turnPolicy: "steer" as const } : {}),
    clientContext: buildNapasClientContext(selectedTopic, selectedStation, language),
  });

  const handleSubmit = async (message: PromptInputMessage) => {
    const text = message.text.trim();
    if ((text.length === 0 && message.files.length === 0) || isResuming) return;

    const options = buildSendOptions();

    if (message.files.length === 0) {
      await sendText(text);
      return;
    }

    setHasInputText(false);
    setInputText("");
    setCancellationError(undefined);
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
    <PromptInput fileInputLabel={copy.message.attachment} onSubmit={handleSubmit}>
      <PromptInputTextarea
        className="napas-prompt-textarea"
        disabled={isResuming}
        id="napas-composer-input"
        onChange={(event) => {
          setInputText(event.currentTarget.value);
          setHasInputText(event.currentTarget.value.trim().length > 0);
        }}
        placeholder={copy.chat.placeholder}
        value={inputText}
      />
      <ComposerAction
        hasInputText={hasInputText}
        isBusy={isBusy}
        isResuming={isResuming}
        language={language}
        onCancel={requestCancellation}
      />
    </PromptInput>
  );

  return (
    <div
      className="relative flex h-full min-h-0 flex-col overflow-hidden bg-background text-foreground napas-chat-shell"
      data-suggestions-visible={showSuggestedQuestions ? "true" : undefined}
    >
      <header className="chat-head">
        <div className="chat-title-row">
          <span className="chat-brand-mark" aria-hidden="true">
            <img alt="" height={1254} src="/napas-jakarta-air-icon.png" width={1254} />
          </span>
          <div className="chat-title-copy">
            <div className="chat-heading-line">
            <h2 id="chat-heading">{copy.chat.heading}</h2>
            </div>
            <div className="chat-meta-line">
              <p className="connection">
                <span className="connection-dot" aria-hidden="true" />
                <span className="connection-copy">{copy.chat.tagline}</span>
              </p>
            </div>
          </div>
          {isMapOpen ? (
            <button
              aria-controls="mobile-legend-dialog"
              aria-expanded={isLegendOpen}
              aria-label={copy.chat.openLegend}
              className="mobile-legend-toggle"
              onClick={onLegendOpen}
              title={copy.chat.mapLegend}
              type="button"
            >
              <BookOpenIcon aria-hidden="true" />
            </button>
          ) : null}
        </div>
        <div className="assistant-guidance">
          <div className="assistant-guidance-copy">
            <p className="assistant-guidance-title">{copy.chat.guidanceTitle}</p>
            <p className="assistant-guidance-description">{copy.chat.guidanceDescription}</p>
          </div>
          <div aria-label={copy.chat.capabilities} className="assistant-capabilities">
            <span className="assistant-capability">
              <MapPinIcon aria-hidden="true" className="size-3.5" />
              {copy.chat.capabilityStationAware}
            </span>
            <span className="assistant-capability">
              <BookOpenIcon aria-hidden="true" className="size-3.5" />
              {copy.chat.capabilityPlainLanguage}
            </span>
            <span className="assistant-capability">
              <BrainIcon aria-hidden="true" className="size-3.5" />
              {copy.chat.capabilityTopicAware}
            </span>
          </div>
        </div>
        <div className="chat-context-controls">
          <div className="chat-selection-controls">
            <StationPicker
              language={language}
              onClear={() => {
                setStationMenuOpen(false);
                onStationClear();
              }}
              onSelect={handleStationSelect}
              onToggle={() => setStationMenuOpen((open) => !open)}
              open={stationMenuOpen}
              pickerRef={stationPickerRef}
              selectedStation={selectedStation}
              selectedStationId={selectedStationId}
              stations={stationOptions}
            />
            <div className="napas-topic-picker" ref={topicPickerRef}>
              <button
                aria-controls="napas-topic-menu"
                aria-expanded={topicMenuOpen}
                aria-haspopup="dialog"
                className="napas-topic-trigger"
                onClick={() => {
                  setStationMenuOpen(false);
                  setTopicMenuOpen((open) => !open);
                }}
                type="button"
              >
                <BookOpenIcon aria-hidden="true" className="size-3.5" />
                <span>{localizedTopic?.label ?? copy.chat.topics}</span>
                <ChevronDownIcon aria-hidden="true" className="size-3.5" />
              </button>
              {topicMenuOpen ? (
                <TopicMenu
                  language={language}
                  onClear={() => {
                    setSelectedTopicId(undefined);
                    setTopicMenuOpen(false);
                  }}
                  onSelect={(topic) => {
                    setSelectedTopicId(topic.id);
                    setTopicMenuOpen(false);
                  }}
                  selectedTopic={selectedTopic}
                />
              ) : null}
            </div>
          </div>
          <button
            aria-controls="map-panel"
            aria-expanded={isMapOpen}
            aria-label={isMapOpen ? copy.chat.closeMap : copy.chat.openMap}
            className="mobile-map-toggle"
            onClick={handleMapToggle}
            type="button"
          >
            {isMapOpen ? <XIcon aria-hidden="true" /> : <MapIcon aria-hidden="true" />}
            {isMapOpen ? null : <span>{copy.chat.map}</span>}
          </button>
        </div>
      </header>

      <Conversation aria-label={copy.chat.conversation} className="min-h-0 flex-1 napas-chat-scroll" resize="smooth" tabIndex={0}>
        <ConversationContent className="mx-auto w-full gap-6 px-4 sm:px-6 napas-chat-content max-w-none pt-4 pb-5">
          {isEmpty ? <EmptyChatState language={language} /> : null}
          {agent.data.messages.map((message, index) =>
            showPendingThinking &&
            message.role === "assistant" &&
            message.id === lastMessage?.id ? null : (
              <AgentMessage
                canRespond={!isBusy && !isResuming}
                isLatest={index === agent.data.messages.length - 1}
                isStreaming={
                  agent.status === "streaming" && index === agent.data.messages.length - 1
                }
                key={message.id}
                message={message}
                language={language}
                sessionId={telemetrySessionId}
                onInputResponses={(inputResponses) => {
                  setCancellationError(undefined);
                  return agent.respond(inputResponses);
                }}
              />
            ),
          )}
          {showPendingThinking ? <PendingThinking language={language} /> : null}
          {errorMessage ? <ErrorMessage language={language} message={errorMessage} /> : null}
        </ConversationContent>
        <ConversationScrollAccessibility label={copy.chat.conversation} />
        <ConversationScrollButton aria-label={copy.chat.scrollToBottom} />
      </Conversation>

      <div className="mx-auto w-full px-4 sm:px-6 napas-chat-dock">
        <ChatUtilityRow
          contextOpen={contextOpen}
          isBusy={isBusy || isResuming}
          onStationClear={() => {
            setContextOpen(false);
            onStationClear();
          }}
          onTopicClear={() => setSelectedTopicId(undefined)}
          onTopicOpen={() => setTopicMenuOpen(true)}
          onContextToggle={() => setContextOpen((open) => !open)}
          onPrompt={(prompt) => void sendText(prompt)}
          language={language}
          selectedTopic={localizedTopic}
          selectedStation={selectedStation}
          suggestions={suggestedQuestions}
          showSuggestions={showSuggestedQuestions}
        />
        <div className="w-full napas-composer-wrap">{composer}</div>
      </div>
    </div>
  );
}

function EmptyChatState({ language }: { readonly language: Language }) {
  const copy = getUiCopy(language);

  return (
    <div className="napas-empty-state" aria-label={copy.chat.emptyTitle}>
      <div className="napas-empty-mark"><img alt="" src="/napas-jakarta-air-icon.png" /></div>
      <p>{copy.chat.emptyTitle}</p>
      <span>{copy.chat.emptyDescription}</span>
    </div>
  );
}

function ChatUtilityRow({
  contextOpen,
  isBusy,
  language,
  onContextToggle,
  onPrompt,
  onStationClear,
  onTopicClear,
  onTopicOpen,
  selectedTopic,
  selectedStation,
  suggestions,
  showSuggestions,
}: {
  readonly contextOpen: boolean;
  readonly isBusy: boolean;
  readonly language: Language;
  readonly onContextToggle: () => void;
  readonly onPrompt: (prompt: string) => void;
  readonly onStationClear: () => void;
  readonly onTopicClear: () => void;
  readonly onTopicOpen: () => void;
  readonly selectedTopic?: TopicCopy;
  readonly selectedStation?: string;
  readonly suggestions: readonly string[];
  readonly showSuggestions: boolean;
}) {
  const copy = getUiCopy(language);

  return (
    <div className="napas-chat-utility-row">
      {showSuggestions ? (
        <div aria-label={copy.chat.suggestedQuestions} className="napas-suggestions-overlay">
          {suggestions.map((prompt) => (
            <button
              className="prompt-chip"
              disabled={isBusy}
              key={prompt}
              onClick={() => onPrompt(prompt)}
              type="button"
            >
              {prompt}
            </button>
          ))}
        </div>
      ) : null}
      <div className="napas-context-stack">
        {selectedTopic ? (
          <div className="napas-selected-context napas-selected-topic" role="group">
            <button
              aria-label={`${copy.chat.selectedTopic}${selectedTopic.label}`}
              className="napas-context-main"
              onClick={onTopicOpen}
              type="button"
              title={selectedTopic.label}
            >
              <BookOpenIcon aria-hidden="true" className="size-3.5" />
              <span>{selectedTopic.label}</span>
              <small>{copy.chat.topic}</small>
            </button>
            <button
              aria-label={copy.chat.clearSelectedTopic}
              className="napas-context-clear"
              onClick={onTopicClear}
              type="button"
            >
              <XIcon aria-hidden="true" className="size-3" />
            </button>
          </div>
        ) : null}
        <div className="napas-context-wrap">
          {selectedStation ? (
            <div className="napas-selected-context napas-selected-location" role="group">
              <button
                aria-expanded={contextOpen}
                aria-label={copy.chat.selectedLocation}
                className="napas-context-main"
                onClick={onContextToggle}
                type="button"
              >
                <MapPinIcon aria-hidden="true" className="size-3.5" />
                <span>{selectedStation}</span>
                <small>{copy.chat.selected}</small>
              </button>
              <button
                aria-label={copy.chat.clearSelectedLocation}
                className="napas-context-clear"
                onClick={onStationClear}
                type="button"
              >
                <XIcon aria-hidden="true" className="size-3" />
              </button>
            </div>
          ) : null}
          {contextOpen && selectedStation ? (
            <div className="napas-context-menu" role="dialog" aria-label={copy.chat.messageContext}>
              <strong>{copy.chat.messageContext}</strong>
              <span><MapPinIcon aria-hidden="true" className="size-3" />{replaceCopy(copy.chat.includeLocation, { station: selectedStation })}</span>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function StationPicker({
  language,
  onClear,
  onSelect,
  onToggle,
  open,
  pickerRef,
  selectedStation,
  selectedStationId,
  stations,
}: {
  readonly language: Language;
  readonly onClear: () => void;
  readonly onSelect: (station: DemoStation) => void;
  readonly onToggle: () => void;
  readonly open: boolean;
  readonly pickerRef: RefObject<HTMLDivElement | null>;
  readonly selectedStation?: string;
  readonly selectedStationId?: string;
  readonly stations: readonly DemoStation[];
}) {
  const selected = stations.find((station) => station.id === selectedStationId);
  const copy = getUiCopy(language);

  return (
    <div className="napas-station-picker" ref={pickerRef}>
      <button
        aria-controls="napas-station-menu"
        aria-expanded={open}
        aria-haspopup="dialog"
        className="napas-station-trigger"
        onClick={onToggle}
        type="button"
      >
        <MapPinIcon aria-hidden="true" className="size-3.5" />
        <span>{selected?.name ?? selectedStation ?? copy.chat.station}</span>
        <ChevronDownIcon aria-hidden="true" className="size-3.5" />
      </button>
      {open ? (
        <StationMenu
          language={language}
          onClear={onClear}
          onSelect={onSelect}
          selectedStationId={selectedStationId}
          stations={stations}
        />
      ) : null}
    </div>
  );
}

function StationMenu({
  language,
  onClear,
  onSelect,
  selectedStationId,
  stations,
}: {
  readonly language: Language;
  readonly onClear: () => void;
  readonly onSelect: (station: DemoStation) => void;
  readonly selectedStationId?: string;
  readonly stations: readonly DemoStation[];
}) {
  const copy = getUiCopy(language);

  return (
    <div aria-label={copy.chat.chooseStation} className="napas-station-menu" id="napas-station-menu" role="dialog">
      <div className="napas-station-menu-head">
        <div>
          <strong>{copy.chat.chooseStation}</strong>
          <span>{copy.chat.stationMenuDescription}</span>
        </div>
        {selectedStationId ? (
          <button className="napas-station-clear" onClick={onClear} type="button">
            <XIcon aria-hidden="true" className="size-3" />
            {copy.chat.clear}
          </button>
        ) : null}
      </div>
      <div className="napas-station-list">
        {stations.length > 0 ? stations.map((station) => {
          const isSelected = station.id === selectedStationId;
          return (
            <button
              aria-pressed={isSelected}
              className={`napas-station-option${isSelected ? " is-selected" : ""}`}
              key={station.id}
              onClick={() => onSelect(station)}
              type="button"
            >
              <span className="napas-station-option-topline">
                <strong>{station.name}</strong>
                {isSelected ? <small>{copy.chat.selectedOption}</small> : null}
              </span>
              <span>{localizedDistrict(station.district, language)} · {localizedCategory(station.category, language)}</span>
            </button>
          );
        }) : (
          <p className="napas-station-empty">{copy.chat.stationLocationsLoading}</p>
        )}
      </div>
    </div>
  );
}

function TopicMenu({
  language,
  onClear,
  onSelect,
  selectedTopic,
}: {
  readonly language: Language;
  readonly onClear: () => void;
  readonly onSelect: (topic: TopicOption) => void;
  readonly selectedTopic?: TopicOption;
}) {
  const copy = getUiCopy(language);

  return (
    <div aria-label={copy.chat.chooseTopic} className="napas-topic-menu" id="napas-topic-menu" role="dialog">
      <div className="napas-topic-menu-head">
        <div>
          <strong>{copy.chat.chooseTopic}</strong>
          <span>{copy.chat.topicMenuDescription}</span>
        </div>
        {selectedTopic ? (
          <button className="napas-topic-clear" onClick={onClear} type="button">
            <XIcon aria-hidden="true" className="size-3" />
            {copy.chat.clear}
          </button>
        ) : null}
      </div>
      <p className="napas-topic-menu-note">{copy.chat.topicMenuNote}</p>
      <div className="napas-topic-list">
        {TOPIC_GROUPS.map((group) => {
          const localizedGroup = getLocalizedTopicGroupCopy(group, language);

          return (
          <section aria-labelledby={`topic-group-${group.id}`} className="napas-topic-group" key={group.id}>
            <div className="napas-topic-group-head">
              <h2 id={`topic-group-${group.id}`}>{localizedGroup.label}</h2>
              <p>{localizedGroup.description}</p>
            </div>
            <div className="napas-topic-options">
              {group.topics.map((topic) => {
                const localizedTopic = getLocalizedTopicCopy(topic, language);
                const sourceLabels = getTopicSourceLabels(topic, language);
                const sourceSummary = sourceLabels.length > 2
                  ? `${sourceLabels.slice(0, 2).join(" · ")} +${sourceLabels.length - 2} ${copy.chat.more}`
                  : sourceLabels.join(" · ");
                return (
                  <button
                    aria-pressed={selectedTopic?.id === topic.id}
                    className={`napas-topic-option${selectedTopic?.id === topic.id ? " is-selected" : ""}`}
                    key={topic.id}
                    onClick={() => onSelect(topic)}
                    type="button"
                  >
                    <span className="napas-topic-option-topline">
                      <strong>{localizedTopic.label}</strong>
                      {selectedTopic?.id === topic.id ? <span className="napas-topic-selected-label">{copy.chat.selectedOption}</span> : null}
                    </span>
                    <span className="napas-topic-option-description">{localizedTopic.description}</span>
                    <span className="napas-topic-option-question"><em>{copy.chat.ask}</em> {localizedTopic.suggestedQuestion}</span>
                    <span className="napas-topic-option-source"><BookOpenIcon aria-hidden="true" className="size-3" />{sourceSummary}</span>
                    {topic.reviewStatus === "clinical-review-required" ? (
                      <span className="napas-topic-review-note">{copy.chat.clinicalReview}</span>
                    ) : null}
                  </button>
                );
              })}
            </div>
          </section>
          );
        })}
      </div>
    </div>
  );
}

function ComposerAction({
  hasInputText,
  isBusy,
  isResuming,
  language,
  onCancel,
}: {
  readonly hasInputText: boolean;
  readonly isBusy: boolean;
  readonly isResuming: boolean;
  readonly language: Language;
  readonly onCancel: () => void;
}) {
  const copy = getUiCopy(language);
  const attachments = usePromptInputAttachments();
  const canSubmit = hasInputText || attachments.files.length > 0;

  if (!isBusy || canSubmit) {
    return (
      <PromptInputSubmit
        aria-label={copy.chat.sendMessage}
        className="napas-send-action absolute right-2.5 top-1/2"
        disabled={isResuming}
      >
        <SendHorizontalIcon aria-hidden="true" className="size-4" />
        <span className="napas-send-label">{copy.chat.send}</span>
      </PromptInputSubmit>
    );
  }

  return (
    <PromptInputButton
      aria-label={copy.chat.stop}
      className="napas-send-action napas-stop-action absolute right-2.5 top-1/2"
      onClick={onCancel}
      variant="outline"
    >
      <SquareIcon className="size-3 fill-current" />
    </PromptInputButton>
  );
}

function ErrorMessage({ language, message }: { readonly language: Language; readonly message: string }) {
  const copy = getUiCopy(language);

  return (
    <Message className="max-w-full" from="assistant">
      <MessageContent>
        <div
          className="flex w-full items-start gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2.5 text-sm"
          role="alert"
        >
          <AlertCircleIcon className="mt-0.5 size-4 shrink-0 text-destructive" />
          <div>
            <p className="font-medium">{copy.chat.requestFailed}</p>
            <p className="mt-0.5 text-muted-foreground">{message}</p>
          </div>
        </div>
      </MessageContent>
    </Message>
  );
}

function PendingThinking({ language }: { readonly language: Language }) {
  const copy = getUiCopy(language);

  return (
    <Message aria-live="polite" className="napas-thinking-message" from="assistant">
      <MessageContent>
        <div className="mb-4 flex w-full items-center gap-2 text-muted-foreground text-sm">
          <BrainIcon className="size-4" />
          <Shimmer duration={1}>{copy.chat.thinking}</Shimmer>
        </div>
      </MessageContent>
    </Message>
  );
}

function toErrorMessage(error: unknown, language: Language): string {
  return localizeAgentError(error instanceof Error ? error.message : undefined, language) ?? getUiCopy(language).chat.unableToCancel;
}

function localizeAgentError(message: string | undefined, language: Language): string | undefined {
  if (!message) return undefined;
  if (language === "en") return message;
  if (/cancel|abort/i.test(message)) return getUiCopy(language).chat.unableToCancel;
  if (/model|gemini|network|fetch|timeout|request/i.test(message)) return getUiCopy(language).chat.modelUnavailable;
  return getUiCopy(language).chat.requestFailedDetail;
}

function getLatestTurnFailure(
  events: ReturnType<typeof useEveAgent>["events"],
  language: Language,
): string | undefined {
  for (let index = events.length - 1; index >= 0; index -= 1) {
    const event = events[index];

    if (event.type === "turn.failed") {
      return event.data.code === "MODEL_CALL_FAILED"
        ? getUiCopy(language).chat.modelUnavailable
        : language === "id" ? getUiCopy(language).chat.requestFailedDetail : event.data.message;
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

function messageText(message: EveMessage): string {
  return message.parts
    .filter((part): part is Extract<EveMessage["parts"][number], { type: "text" }> => part.type === "text")
    .map((part) => part.text)
    .join("\n\n")
    .trim();
}

function createAnonymousSessionId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `anonymous-${crypto.randomUUID()}`;
  }
  return `anonymous-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}
