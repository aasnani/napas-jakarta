"""Small, browser-client-owned state helpers."""

from dataclasses import dataclass

from nicegui import app

CHAT_STORAGE_KEY = "napas-jakarta-chat-v1"


@dataclass
class ChatTurnLifecycle:
    """Guard the one-visible-answer contract for a chat turn."""

    phase: str = "checking"
    visible_text: str = ""
    error_reason: str | None = None

    def append_stream(self, text: str) -> str:
        """Append native provider text; never replace an earlier chunk."""
        if self.phase == "checking":
            self.phase = "streaming"
        if self.phase != "streaming":
            raise RuntimeError(f"cannot append while turn is {self.phase}")
        self.visible_text += text
        return self.visible_text

    def reveal_approved(self, text: str) -> str:
        """Reveal validated structured text through the same answer component."""
        if self.phase not in {"checking", "revealing"}:
            raise RuntimeError(f"cannot reveal while turn is {self.phase}")
        self.phase = "revealing"
        self.visible_text += text
        return self.visible_text

    def finish(self, final_text: str) -> str:
        """Complete without changing already-visible semantics.

        A native stream may receive a final suffix that was queued just after
        the last UI tick.  It may append that suffix, but a different prefix
        is rejected so a fallback can never swap an answer already on screen.
        """
        if self.phase == "checking":
            self.reveal_approved(final_text)
        elif self.phase == "revealing":
            if final_text != self.visible_text:
                raise RuntimeError("approved answer changed during reveal")
        elif self.phase == "streaming":
            if final_text == self.visible_text:
                pass
            elif final_text.startswith(self.visible_text):
                self.visible_text += final_text[len(self.visible_text) :]
            else:
                raise RuntimeError("provider completion changed streamed answer")
        else:
            raise RuntimeError(f"cannot finish while turn is {self.phase}")
        self.phase = "complete"
        return self.visible_text

    def fail(self, reason: str) -> str:
        """Enter a terminal error state without replacing visible content."""
        if self.phase in {"complete", "error"}:
            raise RuntimeError(f"cannot fail while turn is {self.phase}")
        self.phase = "error"
        self.error_reason = reason
        return self.visible_text


def client_state() -> dict:
    state = app.storage.client.setdefault("napas", {})
    state.setdefault("messages", [])
    state.setdefault("language", "English")
    state.setdefault("pending_question", None)
    state.setdefault("conversation", {})
    return state


def clear_conversation(state: dict | None = None) -> dict:
    """Clear only the current client/tab conversation and its metadata."""
    if state is None:
        state = client_state()
    state["messages"] = []
    state["pending_question"] = None
    state["conversation"] = {}
    return state


def valid_chat_messages(value: object) -> list[dict]:
    """Validate browser-hydrated messages without accepting arbitrary objects."""
    if not isinstance(value, list):
        return []
    messages = []
    for item in value:
        if not isinstance(item, dict) or item.get("role") not in {"user", "assistant"}:
            continue
        content = item.get("content")
        if not isinstance(content, str):
            continue
        message = {"role": item["role"], "content": content}
        if item["role"] == "assistant":
            sources = item.get("sources", [])
            message["sources"] = sources if isinstance(sources, list) else []
            if isinstance(item.get("meta"), dict):
                message["meta"] = item["meta"]
        messages.append(message)
    return messages


def chat_payload(state: dict) -> dict:
    """Return the JSON-safe tab handoff payload for route navigation."""
    return {
        "messages": list(state.get("messages", [])),
        "conversation": state.get("conversation", {}),
    }


def restore_chat_payload(state: dict, payload: object) -> dict:
    """Restore only validated conversation data received from this tab."""
    if not isinstance(payload, dict):
        return state
    state["messages"] = valid_chat_messages(payload.get("messages"))
    conversation = payload.get("conversation")
    state["conversation"] = conversation if isinstance(conversation, dict) else {}
    state["pending_question"] = None
    return state
