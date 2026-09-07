import pytest

from app.web import ROOT
from app.webui.state import ChatTurnLifecycle


def test_structured_turn_reveals_only_after_approval() -> None:
    turn = ChatTurnLifecycle()

    assert turn.phase == "checking"
    assert turn.reveal_approved("Approved answer [source]") == "Approved answer [source]"
    assert turn.finish(turn.visible_text) == "Approved answer [source]"
    assert turn.phase == "complete"


def test_native_stream_only_appends_and_rejects_late_fallback() -> None:
    turn = ChatTurnLifecycle()
    turn.append_stream("Partial answer")

    with pytest.raises(RuntimeError, match="changed streamed answer"):
        turn.finish("Contradictory fallback")
    assert turn.visible_text == "Partial answer"
    assert turn.phase == "streaming"


def test_interruption_preserves_partial_text_and_is_terminal() -> None:
    turn = ChatTurnLifecycle()
    turn.append_stream("Partial provider response")

    assert turn.fail("provider interruption") == "Partial provider response"
    assert turn.phase == "error"
    assert turn.error_reason == "provider interruption"
    with pytest.raises(RuntimeError, match="cannot fail"):
        turn.fail("second interruption")


def test_double_completion_and_post_completion_append_are_rejected() -> None:
    turn = ChatTurnLifecycle()
    turn.finish("One approved answer")

    with pytest.raises(RuntimeError, match="cannot finish"):
        turn.finish("A second answer")
    with pytest.raises(RuntimeError, match="cannot append"):
        turn.append_stream("late text")


def test_chat_submit_has_single_busy_gate_for_rapid_requests() -> None:
    source = (ROOT / "app" / "web.py").read_text(encoding="utf-8")
    assert "if busy:\n            return" in source
    assert "busy = True" in source
    assert "new_chat.disable()" in source
