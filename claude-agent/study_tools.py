"""학습 코치 에이전트가 사용하는 도구.

- 로드맵(배울 주제 목록)은 roadmap.json 파일에서 읽습니다. 내용은 직접 바꿔 쓰세요.
- 학습 진도는 progress.json 파일에 저장됩니다. (각 주제의 점수와 완료 여부)

로드맵 '내용'과 코드를 분리했기 때문에, roadmap.json만 바꾸면
어떤 주제(파이썬, 영어, 자격증 등)의 학습 코치든 만들 수 있습니다.
"""

from __future__ import annotations

import json
from pathlib import Path

from anthropic import beta_tool

HERE = Path(__file__).resolve().parent
ROADMAP_PATH = HERE / "roadmap.json"
PROGRESS_PATH = HERE / "progress.json"


def load_roadmap() -> dict:
    return json.loads(ROADMAP_PATH.read_text(encoding="utf-8"))


def _topics_index(roadmap: dict) -> dict[str, dict]:
    """topic_id -> {단계 이름, 주제 정보} 로 빠르게 찾기 위한 색인."""
    index = {}
    for stage in roadmap["stages"]:
        for topic in stage["topics"]:
            index[topic["id"]] = {"stage": stage["name"], **topic}
    return index


def load_progress() -> dict:
    if PROGRESS_PATH.exists():
        return json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
    return {}


def save_progress(progress: dict) -> None:
    PROGRESS_PATH.write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# 도구들
# ---------------------------------------------------------------------------
@beta_tool
def get_roadmap() -> str:
    """전체 학습 로드맵(단계와 주제 목록)과 각 주제의 현재 완료 상태를 보여줍니다.
    학습을 어디서 시작할지, 다음에 무엇을 배울지 정할 때 먼저 호출하세요.
    """
    roadmap = load_roadmap()
    progress = load_progress()
    lines = [f"📚 {roadmap['title']} (통과 기준: {roadmap.get('pass_score', 70)}점)\n"]
    for stage in roadmap["stages"]:
        lines.append(stage["name"])
        for topic in stage["topics"]:
            record = progress.get(topic["id"])
            if record and record.get("passed"):
                mark = f"✅ 완료 ({record['score']}점)"
            elif record:
                mark = f"🔶 진행 중 ({record['score']}점)"
            else:
                mark = "⬜ 시작 전"
            lines.append(f"  - [{topic['id']}] {topic['title']} … {mark}")
        lines.append("")
    return "\n".join(lines)


@beta_tool
def get_topic(topic_id: str) -> str:
    """특정 주제의 학습 목표와 추천 자료를 자세히 보여줍니다.
    퀴즈를 내기 전에 이 도구로 그 주제의 학습 목표를 먼저 확인하세요.

    Args:
        topic_id: 주제 ID. get_roadmap 결과의 대괄호 안 값. 예: "variables"
    """
    index = _topics_index(load_roadmap())
    topic = index.get(topic_id)
    if topic is None:
        return f"'{topic_id}' 주제를 찾을 수 없습니다. get_roadmap으로 올바른 ID를 확인하세요."
    goals = "\n".join(f"  - {g}" for g in topic["goals"])
    resources = "\n".join(f"  - {r}" for r in topic.get("resources", []))
    return f"[{topic['stage']}] {topic['title']}\n\n학습 목표:\n{goals}\n\n추천 자료:\n{resources}"


@beta_tool
def record_quiz_result(topic_id: str, score: int) -> str:
    """퀴즈 채점이 끝난 뒤 그 주제의 점수를 저장합니다. 점수는 0~100 사이입니다.
    통과 기준 이상이면 그 주제를 '완료'로 표시합니다.

    Args:
        topic_id: 주제 ID. 예: "variables"
        score: 퀴즈 점수 (0~100)
    """
    roadmap = load_roadmap()
    index = _topics_index(roadmap)
    if topic_id not in index:
        return f"'{topic_id}' 주제를 찾을 수 없습니다. get_roadmap으로 ID를 확인하세요."
    score = max(0, min(100, int(score)))
    pass_score = roadmap.get("pass_score", 70)
    passed = score >= pass_score

    progress = load_progress()
    progress[topic_id] = {"score": score, "passed": passed}
    save_progress(progress)

    status = "통과했습니다! ✅" if passed else f"아직 통과 기준({pass_score}점)에 못 미칩니다. 복습 후 다시 도전해 보세요."
    return f"'{index[topic_id]['title']}' 주제에 {score}점을 저장했습니다. {status}"


@beta_tool
def suggest_next_topic() -> str:
    """아직 완료하지 않은 주제 중, 로드맵 순서상 가장 먼저 배워야 할 주제를 추천합니다.

    Args:
    """
    roadmap = load_roadmap()
    progress = load_progress()
    for stage in roadmap["stages"]:
        for topic in stage["topics"]:
            record = progress.get(topic["id"])
            if not (record and record.get("passed")):
                return f"다음 추천 주제: [{topic['id']}] {topic['title']} ({stage['name']})"
    return "축하합니다! 로드맵의 모든 주제를 완료했습니다. 🎉"


STUDY_TOOLS = [get_roadmap, get_topic, record_quiz_result, suggest_next_topic]
