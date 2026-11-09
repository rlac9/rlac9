# 🤖 Claude 에이전트 만들기 (Python)

Anthropic의 공식 Python SDK(`anthropic`)로 **도구를 사용하는 Claude 에이전트**를 만드는 예제와 가이드입니다.

## 1. 에이전트란?

일반 챗봇은 질문을 받으면 바로 답만 합니다.
**에이전트**는 필요하면 스스로 **도구(tool)** 를 골라 사용하고, 그 결과를 보고 다음 행동을 정하는 것을 반복합니다.

```
에이전트 = 모델(Claude) + 도구(파이썬 함수) + 반복(loop)

  사용자 질문
      │
      ▼
 ┌─────────┐   "calculate('123*456') 호출해줘"   ┌──────────────┐
 │ Claude  │ ─────────────────────────────────▶ │ 내 파이썬 코드 │
 │         │ ◀───────────────────────────────── │  (도구 실행)   │
 └─────────┘          결과: "56088"              └──────────────┘
      │   (도구가 더 필요 없을 때까지 반복)
      ▼
  최종 답변: "123 × 456 = 56,088 입니다."
```

중요한 점: **Claude는 직접 코드를 실행하지 않습니다.** "이 도구를 이 값으로 불러줘"라고 요청만 하고, 실제 실행은 여러분의 프로그램이 합니다.

## 2. 파일 구성

| 파일 | 설명 |
|---|---|
| `agent.py` | 메인 에이전트. 터미널에서 대화합니다. SDK의 **Tool Runner**가 반복을 자동 처리 |
| `tools.py` | 에이전트가 쓰는 도구들 (계산기, 현재 시각, 파일 목록, 파일 읽기) |
| `manual_loop.py` | 학습용: 반복(loop)을 **직접** 구현한 예제 |
| `study_coach.py` | 학습 코치 에이전트. 로드맵 안내 + 퀴즈 채점 + 진도 저장 |
| `study_tools.py` | 코치가 쓰는 도구 (로드맵 보기, 주제 상세, 점수 저장, 다음 추천) |
| `roadmap.json` | 배울 주제 목록. **내용을 직접 바꿔 쓰세요** (샘플: 파이썬 입문) |
| `android-agent-design.md` | 📱 안드로이드 기기 제어 에이전트 **설계 문서** |
| `requirements.txt` | 필요한 패키지 |
| `.env.example` | API 키 설정 예시 |

## 3. 설치와 실행

**준비물:** Python 3.10 이상, Anthropic API 키

1. API 키 발급: <https://platform.claude.com> 에 가입 → **API Keys** 메뉴에서 키 생성 (사용량만큼 요금이 나옵니다)
2. 설치:

   ```bash
   cd claude-agent
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. API 키 설정 (터미널을 새로 열 때마다 필요):

   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."      # Windows PowerShell: $env:ANTHROPIC_API_KEY="sk-ant-..."
   ```

4. 실행:

   ```bash
   python agent.py
   ```

**대화 예시**

```
🤖 Claude 에이전트입니다. 무엇이든 물어보세요! (종료: exit)

나> 123456 곱하기 789는?
  🔧 도구 호출: calculate({'expression': '123456 * 789'})
Claude> 123,456 × 789 = 97,406,784 입니다.

나> 지금 뉴욕은 몇 시야?
  🔧 도구 호출: get_current_time({'timezone': 'America/New_York'})
Claude> 뉴욕은 지금 오전 1시 43분입니다.

나> 이 폴더에 무슨 파일이 있어? tools.py는 무슨 일을 해?
  🔧 도구 호출: list_files({'directory': '.'})
  🔧 도구 호출: read_file({'path': 'tools.py'})
Claude> ...
```

## 4. 나만의 도구 추가하기

`tools.py`에 함수를 하나 만들고 `@beta_tool`을 붙인 뒤, `ALL_TOOLS` 목록에 넣으면 끝입니다.

```python
@beta_tool
def roll_dice(sides: int = 6) -> str:
    """주사위를 굴려 나온 숫자를 알려줍니다.

    Args:
        sides: 주사위 면의 개수. 기본값 6
    """
    import random
    return str(random.randint(1, sides))


ALL_TOOLS = [calculate, get_current_time, list_files, read_file, roll_dice]
```

SDK가 **함수 이름 · 타입 힌트 · docstring**을 읽어 Claude에게 보낼 도구 설명을 자동으로 만듭니다.
그래서 **docstring을 잘 쓰는 것이 곧 프롬프트를 잘 쓰는 것**입니다. 언제 이 도구를 써야 하는지, 각 인자에 어떤 값을 넣어야 하는지 분명하게 적어 주세요.

> ⚠️ 도구는 여러분의 컴퓨터에서 실제로 실행됩니다. 파일 삭제나 명령어 실행처럼 위험한 도구를 만들 때는 범위를 제한하세요.
> (예: `tools.py`의 파일 도구는 `claude-agent` 폴더 밖을 읽지 못하게 막아 두었습니다.)

## 4-1. 학습 코치 에이전트: `study_coach.py`

같은 루프(`agent.py`의 `chat()`)에 **시스템 프롬프트와 도구만 바꿔 끼운** 두 번째 에이전트입니다.
로드맵을 안내하고, 퀴즈를 내서 채점하고, 진도를 `progress.json`에 저장합니다.

```bash
python study_coach.py
```

```
🎓 학습 코치입니다. '로드맵 보여줘' ...
나> 오늘 뭐 배우면 돼?
  🔧 도구 호출: suggest_next_topic({})
Claude> 다음 추천 주제는 '변수와 자료형'이에요. 퀴즈를 내볼게요. 3.14는 무슨 자료형일까요?
나> 실수요
Claude> 정답! ... (3~5문제 후) 85점으로 통과입니다. 다음은 '조건문과 반복문'이에요.
```

**배울 주제는 `roadmap.json`에 들어 있습니다.** 코드와 분리돼 있어서, 이 파일만 바꾸면
파이썬 말고 영어·자격증·무엇이든 학습 코치로 바꿀 수 있습니다. 구조는 이렇습니다.

```json
{
  "title": "로드맵 제목",
  "pass_score": 70,
  "stages": [
    { "name": "1단계", "topics": [
      { "id": "unique-id", "title": "주제 이름",
        "goals": ["학습 목표 1", "학습 목표 2"],
        "resources": ["추천 자료 링크"] }
    ]}
  ]
}
```

코치가 쓰는 도구(`study_tools.py`): `get_roadmap`(전체 진도), `get_topic`(주제 상세), `record_quiz_result`(점수 저장), `suggest_next_topic`(다음 추천). `progress.json`은 학습자마다 다른 기록이라 `.gitignore`에 들어 있습니다.

## 4-2. 📱 안드로이드 기기 제어 에이전트 설계

화면을 읽고 사람처럼 터치하는 안드로이드 에이전트의 **설계 문서**는 [`android-agent-design.md`](./android-agent-design.md)에 있습니다.
접근성 서비스로 화면을 읽고, LLM이 "탭/스와이프" 도구를 호출하는 구조로, 이 폴더의 파이썬 루프와 같은 원리입니다. (자신의 기기에서 합법적인 범위로만 사용하세요.)

## 5. 내부 동작 이해하기: `manual_loop.py`

Tool Runner 없이 반복을 직접 짜면 이런 흐름입니다.

```bash
python manual_loop.py "1234 곱하기 5678에 99를 더하면?"
```

1. 대화 기록 + 도구 목록을 `messages.create()`로 보냅니다.
2. 응답의 `content` **전체**를 대화 기록에 추가합니다.
3. `stop_reason`이 `"tool_use"`가 아니면 → 최종 답변이므로 끝.
4. 응답 안의 `tool_use` 블록마다 도구를 실행합니다. 실패하면 `is_error: True`로 알려줍니다.
5. 모든 `tool_result`를 **한 개의** user 메시지로 보내고 1번으로 돌아갑니다.

`agent.py`의 Tool Runner는 이 과정을 대신 해 줍니다. 원리를 이해했다면 실제 프로젝트에서는 Tool Runner를 쓰는 편이 간단합니다.

## 6. 설정 설명

| 설정 | 값 | 의미 |
|---|---|---|
| `model` | `claude-opus-5-5` | 사용할 Claude 모델 |
| `output_config.effort` | `"medium"` | 얼마나 깊이 생각할지. `"low"`는 빠르고 저렴, `"high"`는 더 꼼꼼함 |
| `max_iterations` | `10` | 도구 호출을 최대 몇 번까지 반복할지 (무한 반복 방지) |
| `fallbacks="default"` | 베타 기능 | 안전 필터가 요청을 거절하면 서버가 자동으로 다른 모델로 재시도. 원치 않으면 `betas`와 `fallbacks` 두 줄을 지우면 됩니다 |

## 7. 다른 방법들

| 방법 | 특징 | 문서 |
|---|---|---|
| **Claude API + Tool Runner** (이 예제) | 내가 만든 도구만 사용. 가장 기본적이고 유연함 | [Tool use 문서](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview) |
| **Claude Agent SDK** | Claude Code를 라이브러리로 쓰는 것. 파일 읽기/쓰기, 명령 실행, 웹 검색 도구가 기본 내장 | [Agent SDK 문서](https://code.claude.com/docs/en/agent-sdk) |
| **Managed Agents** (베타) | Anthropic 서버가 에이전트 루프와 작업용 컨테이너까지 대신 운영 | [Managed Agents 문서](https://platform.claude.com/docs/en/managed-agents/overview) |

## 8. 주의사항

- 🔑 **API 키는 절대 코드나 GitHub에 올리지 마세요.** 환경 변수로만 사용하세요. (`.gitignore`에 `.env`가 들어 있습니다)
- 💸 API는 사용한 토큰만큼 요금이 나옵니다. [사용량 대시보드](https://platform.claude.com)에서 확인하고, 필요하면 지출 한도를 설정하세요.
- 🧪 처음에는 `effort`를 `"low"`로 두고 실험하면 비용을 아낄 수 있습니다.
