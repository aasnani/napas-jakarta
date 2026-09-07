import sys
import types

from app.provider import (
    PROMPTS,
    SYSTEM_PROMPT,
    generate_answer,
    generation_usage,
    selected_prompt_variant,
    selected_prompt_version,
)


def test_openai_compatible_provider_contract(monkeypatch):
    calls = {}

    class FakeCompletions:
        def create(self, **kwargs):
            calls["request"] = kwargs
            return types.SimpleNamespace(
                choices=[
                    types.SimpleNamespace(message=types.SimpleNamespace(content="grounded [ispu]"))
                ]
            )

    class FakeClient:
        def __init__(self, **kwargs):
            calls["client"] = kwargs
            self.chat = types.SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeClient))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://provider.example/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    assert (
        generate_answer("What is ISPU?", "[ispu] evidence", "Bahasa Indonesia") == "grounded [ispu]"
    )
    assert calls["client"] == {
        "api_key": "test-key",
        "base_url": "https://provider.example/v1",
        "timeout": 30.0,
        "max_retries": 2,
    }
    assert calls["request"]["model"] == "test-model"
    assert calls["request"]["messages"][0]["content"] == SYSTEM_PROMPT
    assert "Bahasa Indonesia" in calls["request"]["messages"][1]["content"]


def test_prompt_variant_is_shared_by_runtime_and_evaluator_contract(monkeypatch):
    calls = {}

    class FakeCompletions:
        def create(self, **kwargs):
            calls["request"] = kwargs
            return types.SimpleNamespace(
                choices=[
                    types.SimpleNamespace(message=types.SimpleNamespace(content="grounded [ispu]"))
                ]
            )

    class FakeClient:
        def __init__(self, **kwargs):
            self.chat = types.SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeClient))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("PROMPT_VARIANT", "helpful")
    assert selected_prompt_variant() == "helpful"
    assert selected_prompt_version() == "helpful-v1"
    assert generate_answer("What is ISPU?", "[ispu] evidence") == "grounded [ispu]"
    assert calls["request"]["messages"][0]["content"] == PROMPTS["helpful"]


def test_provider_failure_returns_fallback_signal(monkeypatch):
    class FailingClient:
        def __init__(self, **kwargs):
            raise RuntimeError("provider unavailable")

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FailingClient))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    assert generate_answer("question", "context") is None


def test_anthropic_native_messages_contract(monkeypatch):
    calls = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "content": [{"type": "text", "text": "jawaban [ispu]"}],
                "usage": {"input_tokens": 100, "output_tokens": 20},
            }

    def fake_post(url, **kwargs):
        calls["url"] = url
        calls.update(kwargs)
        return FakeResponse()

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(post=fake_post))
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "claude-haiku-4-5-20251001")
    assert (
        generate_answer("What is ISPU?", "[ispu] evidence", "Bahasa Indonesia") == "jawaban [ispu]"
    )
    assert calls["url"] == "https://api.anthropic.com/v1/messages"
    assert calls["headers"]["x-api-key"] == "test-key"
    assert calls["json"]["model"] == "claude-haiku-4-5-20251001"
    assert "Bahasa Indonesia" in calls["json"]["messages"][0]["content"]
    assert generation_usage()["total_tokens"] == 120
    assert generation_usage()["estimated_cost_usd"] == 0.0002


def test_anthropic_receives_bounded_prior_turns(monkeypatch):
    calls = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"content": [{"type": "text", "text": "follow-up"}]}

    def fake_post(url, **kwargs):
        calls["json"] = kwargs["json"]
        return Response()

    monkeypatch.setattr("requests.post", fake_post)
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    assert (
        generate_answer(
            "Would running there be sensible?",
            "[current] evidence",
            history=[
                {"role": "user", "content": "What is Jakarta Pusat like?"},
                {"role": "assistant", "content": "It is moderate [current]."},
                {"role": "user", "content": "Would running there be sensible?"},
            ],
        )
        == "follow-up"
    )
    messages = calls["json"]["messages"]
    assert [item["role"] for item in messages] == ["user", "assistant", "user"]
    assert "Jakarta Pusat" in messages[0]["content"]
    assert "[current] evidence" in messages[-1]["content"]


def test_anthropic_adds_summary_for_older_turns(monkeypatch):
    calls = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"content": [{"type": "text", "text": "ok"}]}

    def fake_post(url, **kwargs):
        calls["json"] = kwargs["json"]
        return Response()

    monkeypatch.setattr("requests.post", fake_post)
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    history = []
    for index in range(6):
        history.extend(
            [
                {"role": "user", "content": f"Earlier question {index}"},
                {"role": "assistant", "content": "Earlier answer"},
            ]
        )
    assert generate_answer("New question", "[source]", history=history) == "ok"
    current = calls["json"]["messages"][-1]["content"]
    assert "Conversation summary for continuity only" in current
    assert "Earlier question 0" in current


def test_anthropic_native_sse_stream_delivers_ordered_deltas_and_usage(monkeypatch):
    calls = {}

    class Response:
        def raise_for_status(self):
            return None

        def iter_lines(self, decode_unicode=True):
            assert decode_unicode is True
            yield "event: message_start"
            yield 'data: {"type":"message_start","message":{"usage":{"input_tokens":17}}}'
            yield ""
            yield "event: content_block_delta"
            yield 'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"first "}}'
            yield ""
            yield "event: content_block_delta"
            yield 'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"second [ispu]"}}'
            yield ""
            yield "event: message_delta"
            yield 'data: {"type":"message_delta","usage":{"output_tokens":9}}'
            yield ""

    def fake_post(url, **kwargs):
        calls.update(kwargs)
        return Response()

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(post=fake_post))
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "claude-haiku-4-5-20251001")
    received = []
    result = generate_answer("Question", "[ispu] evidence", on_delta=received.append)
    assert result == "first second [ispu]"
    assert received == ["first ", "second [ispu]"]
    assert calls["json"]["stream"] is True
    assert calls["stream"] is True
    assert generation_usage()["input_tokens"] == 17
    assert generation_usage()["output_tokens"] == 9


def test_anthropic_partial_stream_is_retained_without_fallback(monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def iter_lines(self, decode_unicode=True):
            yield "event: content_block_delta"
            yield 'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"partial"}}'
            yield ""
            raise RuntimeError("connection closed")

    monkeypatch.setitem(
        sys.modules, "requests", types.SimpleNamespace(post=lambda *args, **kwargs: Response())
    )
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    received = []
    result = generate_answer("Question", "context", on_delta=received.append)
    assert received == ["partial"]
    assert result == "partial\n\n_(Response interrupted before completion.)_"


def test_generation_prompt_contract_uses_shared_variants(monkeypatch):
    from evaluation import eval_generation

    monkeypatch.setenv("PROMPT_VARIANT", "strict")
    result = eval_generation.evaluate_prompt_contract()
    assert result["selected_prompt_variant"] == "strict"
    assert result["selected_prompt_version"] == "strict-v1"
    assert {item["prompt"] for item in result["variants"]} == set(PROMPTS)
    assert all(item["required_fragments_present"] for item in result["variants"])
