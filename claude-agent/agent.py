"""터미널에서 대화하는 Claude 에이전트.

실행:  python agent.py
종료:  exit 또는 quit 입력 (또는 Ctrl+C)

동작 원리:
  1. 사용자의 질문을 Claude에게 보냅니다 (도구 목록도 함께).
  2. Claude가 "이 도구를 이렇게 호출해줘"라고 답하면,
     SDK의 Tool Runner가 해당 파이썬 함수를 실행하고 결과를 다시 Claude에게 보냅니다.
  3. Claude가 더 이상 도구를 부르지 않고 최종 답을 낼 때까지 2번을 반복합니다.
"""

from __future__ import annotations

import sys

import anthropic

from tools import ALL_TOOLS

MODEL = "claude-opus-5-5"

SYSTEM_PROMPT = """당신은 친절한 한국어 도우미 에이전트입니다.
- 정확한 계산이 필요하면 calculate 도구를 사용하세요.
- 날짜나 시간 질문에는 get_current_time 도구를 사용하세요.
- 파일에 대한 질문이면 list_files, read_file 도구로 직접 확인한 뒤 답하세요.
- 도구가 필요 없는 질문에는 바로 답하세요.
답변은 간결하고 이해하기 쉽게 작성하세요."""


def run_turn(
    client: anthropic.Anthropic,
    history: list,
    system: str = SYSTEM_PROMPT,
    tools: list = ALL_TOOLS,
) -> str:
    """대화 기록(history)을 Claude에게 보내고, 도구 사용이 끝날 때까지 실행합니다.

    실행 중 오간 모든 메시지(Claude의 답변, 도구 결과)를 history에 추가하고
    마지막 답변의 텍스트를 반환합니다.
    """
    runner = client.beta.messages.tool_runner(
        model=MODEL,
        max_tokens=16000,
        system=system,
        tools=tools,
        messages=list(history),
        output_config={"effort": "medium"},
        max_iterations=10,  # 도구 호출이 무한히 반복되지 않도록 제한
        # 안전 필터가 요청을 거절하면 서버가 자동으로 다른 모델로 다시 시도합니다.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )

    last_message = None
    for message in runner:  # Claude의 응답이 올 때마다 반복
        last_message = message
        history.append(message.to_param())

        for block in message.content:
            if block.type == "tool_use":
                print(f"  🔧 도구 호출: {block.name}({block.input})")

        # 도구 실행 결과 (Tool Runner가 다음 요청에 쓰는 것과 같은 값, 캐시되어 두 번 실행되지 않음)
        tool_results = runner.generate_tool_call_response()
        if tool_results is not None:
            history.append(tool_results)

    if last_message is None:
        return "(응답이 없습니다)"
    if last_message.stop_reason == "refusal":
        return "(Claude가 이 요청에 답하지 않았습니다. 질문을 바꿔서 다시 시도해 보세요.)"
    if last_message.stop_reason == "max_tokens":
        print("  ⚠️ 답변이 길어서 중간에 잘렸습니다.")

    text = "".join(block.text for block in last_message.content if block.type == "text")
    return text or "(텍스트 답변 없음)"


def chat(
    system: str = SYSTEM_PROMPT,
    tools: list = ALL_TOOLS,
    greeting: str = "🤖 Claude 에이전트입니다. 무엇이든 물어보세요! (종료: exit)",
) -> None:
    """터미널 대화 루프. 다른 에이전트(roadmap_agent.py 등)도 이 함수를 재사용합니다."""
    # API 키는 환경 변수 ANTHROPIC_API_KEY 에서 자동으로 읽습니다.
    client = anthropic.Anthropic()
    history: list = []

    print(greeting + "\n")
    while True:
        try:
            user_input = input("나> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n안녕히 가세요!")
            break
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", "종료"}:
            print("안녕히 가세요!")
            break

        history.append({"role": "user", "content": user_input})
        saved_length = len(history) - 1
        try:
            answer = run_turn(client, history, system, tools)
        except anthropic.AuthenticationError:
            print("❌ API 키가 올바르지 않습니다. ANTHROPIC_API_KEY 환경 변수를 확인하세요.")
            sys.exit(1)
        except anthropic.RateLimitError:
            print("⏳ 요청이 너무 많습니다. 잠시 후 다시 시도하세요.")
            del history[saved_length:]  # 실패한 질문은 기록에서 제거
            continue
        except anthropic.APIStatusError as err:
            print(f"❌ API 오류 ({err.status_code}): {err.message}")
            del history[saved_length:]
            continue
        except anthropic.APIConnectionError:
            print("🌐 서버에 연결할 수 없습니다. 인터넷 연결을 확인하세요.")
            del history[saved_length:]
            continue

        print(f"Claude> {answer}\n")


if __name__ == "__main__":
    chat()
