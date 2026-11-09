"""에이전트 루프를 직접 구현한 학습용 예제.

agent.py는 SDK의 Tool Runner가 반복(loop)을 대신 처리해 줍니다.
이 파일은 그 반복을 직접 작성해서, 에이전트가 내부에서 어떻게 동작하는지 보여줍니다.

실행:  python manual_loop.py "1234 곱하기 5678에 99를 더하면?"
"""

from __future__ import annotations

import sys

import anthropic

from tools import calculate_expression

MODEL = "claude-opus-5-5"

# 도구 설명을 JSON 스키마로 직접 작성합니다. (agent.py에서는 @beta_tool이 자동 생성)
TOOLS = [
    {
        "name": "calculate",
        "description": "수학 식을 정확하게 계산합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": '계산할 식. 예: "123 * 456"'},
            },
            "required": ["expression"],
        },
    }
]


def run_tool(name: str, tool_input: dict) -> str:
    """Claude가 요청한 도구를 실제로 실행합니다."""
    if name == "calculate":
        return calculate_expression(tool_input["expression"])
    raise ValueError(f"알 수 없는 도구: {name}")


def main() -> None:
    question = " ".join(sys.argv[1:]) or "1234 곱하기 5678에 99를 더하면?"
    client = anthropic.Anthropic()
    messages: list = [{"role": "user", "content": question}]
    print(f"나> {question}")

    for step in range(10):  # 최대 10번까지만 반복
        # 1) 대화 기록 전체와 도구 목록을 Claude에게 보냅니다.
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            tools=TOOLS,
            messages=messages,
            output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        # 2) Claude의 응답을 (텍스트만이 아니라 content 전체를) 기록에 추가합니다.
        messages.append({"role": "assistant", "content": response.content})

        # 3) 도구를 부르지 않았다면 최종 답변입니다. 반복을 끝냅니다.
        if response.stop_reason != "tool_use":
            break

        # 4) 응답 안의 모든 tool_use 블록을 실행하고 결과를 모읍니다.
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            print(f"  🔧 [{step + 1}단계] {block.name}({block.input})")
            try:
                result = run_tool(block.name, block.input)
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
            except Exception as err:  # 실패도 Claude에게 알려줘야 스스로 고칠 수 있습니다.
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": str(err), "is_error": True}
                )

        # 5) 모든 결과를 "하나의" user 메시지로 돌려보내고 1)로 돌아갑니다.
        messages.append({"role": "user", "content": tool_results})

    if response.stop_reason == "refusal":
        print("Claude> (이 요청에는 답하지 않았습니다)")
        return
    answer = "".join(block.text for block in response.content if block.type == "text")
    print(f"Claude> {answer}")


if __name__ == "__main__":
    main()
