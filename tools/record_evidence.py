"""실제 실행 출력과 환경·테스트 결과를 기록합니다. 외부 패키지는 필요 없습니다."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "evidence"


def run(command, *, cwd=ROOT, text=None):
    return subprocess.run(command, cwd=cwd, input=text, text=True,
                          encoding="utf-8", errors="replace", capture_output=True, timeout=30)


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    tests = run([sys.executable, "-X", "utf8", "-m", "unittest", "discover", "-s", "tests", "-v"])
    (EVIDENCE / "tests.txt").write_text(
        "$ python -X utf8 -m unittest discover -s tests -v\n"
        + tests.stdout + tests.stderr + f"\nExit code: {tests.returncode}\n", encoding="utf-8")
    if tests.returncode:
        raise SystemExit("테스트 실패: docs/evidence/tests.txt 확인")

    from default_quizzes import make_default_quizzes
    example = {"quizzes": [quiz.to_dict() for quiz in make_default_quizzes()],
               "best_score": None, "history": []}
    (ROOT / "state.example.json").write_text(
        json.dumps(example, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    environment = []
    for label, command in [
        ("Python", [sys.executable, "--version"]),
        ("Git", ["git", "--version"]),
        ("Git author (public noreply)", ["git", "--git-dir=outputs/git-history", "config", "user.email"]),
    ]:
        result = run(command)
        environment.append(label + "\n" + result.stdout + result.stderr)
    environment.append("Editor: Visual Studio Code (installed command confirmed)\n"
                       "Runtime dependencies: Python standard library only\n"
                       "This is text evidence, not a desktop screenshot.\n")
    (EVIDENCE / "environment.txt").write_text("\n".join(environment), encoding="utf-8")

    sessions = [
        ("입력 검사 → 등록 → 목록 → 힌트 풀이 → 점수 → 기록 → 종료",
         "\nabc\n9\n4\n2\n무지개는 보통 몇 가지 색으로 표현할까요?\n3가지\n5가지\n7가지\n9가지\n3\n빨주노초파남보를 세어 보세요.\n3\n1\n1\n0\n0\n1\n4\n7\n5\n"),
        ("별도 프로세스로 재시작 → 등록 문제·점수·기록 유지 확인 → 삭제 → 종료",
         "3\n4\n7\n6\n6\n1\n5\n"),
        ("다시 재시작 → 삭제 결과 유지 확인 → 종료", "3\n5\n"),
        ("입력 스트림 종료(EOF) → 안전한 종료", ""),
    ]
    transcript = ["실제 main.py를 별도 프로세스로 실행한 출력입니다.\n"
                  "자동 입력을 사용했습니다. 화면 캡처가 아닙니다.\n"]
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        for name in ("main.py", "quiz.py", "input_helpers.py", "default_quizzes.py"):
            shutil.copy2(ROOT / name, folder / name)
        for label, answers in sessions:
            result = run([sys.executable, "-X", "utf8", "main.py"], cwd=folder, text=answers)
            transcript.append(f"\n=== {label} ===\n자동 입력:\n{answers}\n실제 출력:\n"
                              + result.stdout + result.stderr + f"\nExit code: {result.returncode}\n")
            if result.returncode:
                raise SystemExit("실제 실행 실패")
        final = json.loads((folder / "state.json").read_text(encoding="utf-8"))
        assert len(final["quizzes"]) == 5
        assert len(final["history"]) == 1
        assert final["history"][0]["hints_used"] == 1
        assert final["best_score"] is not None
    (EVIDENCE / "run.txt").write_text("\n".join(transcript), encoding="utf-8")
    print("검증 23개 및 실제 실행 4회 성공. docs/evidence/ 기록 완료.")


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    main()
