"""저장·재시작·잘못된 입력·게임 중단 등 실제 요구사항을 검증합니다.

이 파일은 '자동 검사(테스트)' 코드입니다. 사람이 직접 게임을 해 보지
않아도, 입력을 흉내 내서 기능이 의도대로 동작하는지 확인합니다.
실행: python -m unittest discover -s tests -v
"""

import contextlib  # print 출력을 가로채기 위해 사용
import io  # 가로챈 출력을 메모리에 담는 그릇(StringIO)
import json
import shutil
import subprocess  # 별도 프로세스로 main.py를 실제 실행
import sys
import tempfile  # 테스트용 임시 폴더(실제 state.json을 건드리지 않음)
import unittest  # 파이썬 기본 테스트 도구
from pathlib import Path
from unittest.mock import patch  # input() 등을 가짜로 바꿔치기

from default_quizzes import make_default_quizzes
from input_helpers import get_number, get_text
from main import QuizGame
from quiz import Quiz


class GameTests(unittest.TestCase):
    """퀴즈 게임의 기능들을 하나씩 검사하는 테스트 묶음입니다."""

    def setUp(self):
        """각 테스트 전에 깨끗한 임시 폴더와 새 게임을 준비하는 기능입니다."""
        # 임시 폴더를 만들고, 테스트가 끝나면 자동으로 지우게 합니다.
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "state.json"
        # 게임이 print 하는 내용을 화면 대신 self.output에 모읍니다.
        self.output = io.StringIO()
        self.redirect = contextlib.redirect_stdout(self.output)
        self.redirect.__enter__()
        self.addCleanup(self.redirect.__exit__, None, None, None)
        self.game = QuizGame(self.path)

    def play(self, values, count=1):
        """입력값 목록(values)을 차례로 넣어 게임 한 판을 대신 진행합니다.

        무작위 선택은 앞에서부터 count개를 고르도록 고정해,
        정답이 무엇인지 미리 알 수 있게 합니다.
        """
        quizzes = self.game.quizzes[:count]
        with (
            patch("builtins.input", side_effect=values),
            patch("main.random.sample", return_value=quizzes),
        ):
            self.game.play()

    def test_numeric_input_recovers_from_all_invalid_cases(self):
        """빈 값·글자·범위 밖 숫자를 넣어도 다시 물어보는지 확인합니다."""
        with patch("builtins.input", side_effect=["", "abc", "0", "9", " 2 "]):
            self.assertEqual(get_number("", 1, 4), 2)
        self.assertIn("아무것도", self.output.getvalue())
        self.assertIn("숫자로", self.output.getvalue())
        self.assertIn("1~4", self.output.getvalue())

    def test_required_text_retries_and_strips(self):
        """빈 글자는 거부하고, 앞뒤 공백은 지워서 받는지 확인합니다."""
        with patch("builtins.input", side_effect=["", "  ", " 문제 "]):
            self.assertEqual(get_text(""), "문제")

    def test_default_five_valid_questions(self):
        """기본 문제가 5개이고 모두 올바른 형태인지 확인합니다."""
        self.assertEqual(len(self.game.quizzes), 5)
        self.assertIsNone(self.game.best_score)
        for quiz in make_default_quizzes():
            self.assertEqual(len(quiz.choices), 4)
            self.assertTrue(quiz.check_answer(quiz.answer))
            self.assertFalse(quiz.check_answer(0))

    def test_quiz_rejects_invalid_shapes_and_boolean_answer(self):
        """빈 문제·선택지 부족·True 정답 등을 막는지 확인합니다."""
        for args in [
            ("", ["a"] * 4, 1),
            ("q", ["a"], 1),
            ("q", ["a", "b", "c", ""], 1),
            ("q", ["a"] * 4, True),
        ]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                Quiz(*args)

    def test_completed_game_and_restart_preserve_score_history(self):
        """게임을 끝낸 뒤 다시 실행해도 점수·기록이 남아 있는지 확인합니다."""
        # "1" = 1문제 풀기, "3" = 정답 3번 선택
        self.play(["1", "3"])
        restarted = QuizGame(self.path)
        self.assertEqual(restarted.best_score, 100)
        self.assertEqual(restarted.history[0]["correct"], 1)
        self.assertTrue(restarted.history[0]["completed"])

    def test_wrong_answer_does_not_lower_best(self):
        """나중에 틀려도 최고 점수가 내려가지 않는지 확인합니다."""
        self.play(["1", "3"])
        self.play(["1", "1"])
        self.assertEqual(self.game.best_score, 100)
        self.assertEqual(self.game.history[-1]["score"], 0)

    def test_hint_repeated_only_deducts_once(self):
        """같은 문제에서 힌트를 두 번 봐도 10점만 깎이는지 확인합니다."""
        self.play(["1", "0", "0", "3"])
        self.assertEqual(self.game.best_score, 90)
        self.assertEqual(self.game.history[-1]["hints_used"], 1)

    def test_hint_wrong_answer_score_has_zero_floor(self):
        """힌트를 보고 틀려도 점수가 0점 아래로 내려가지 않는지 확인합니다."""
        self.play(["1", "0", "1"])
        self.assertEqual(self.game.best_score, 0)

    def test_question_count_retries(self):
        """문제 수를 잘못 입력하면 다시 물어보는지 확인합니다."""
        self.play(["", "abc", "0", "6", " 1 ", "3"])
        self.assertEqual(self.game.history[-1]["total"], 1)

    def test_add_restart_delete_restart(self):
        """문제 추가·삭제 결과가 재실행 후에도 유지되는지 확인합니다."""
        with patch(
            "builtins.input",
            side_effect=["추가 문제", "가", "나", "다", "라", "2", "힌트"],
        ):
            self.game.add_quiz()
        restarted = QuizGame(self.path)
        self.assertEqual(restarted.quizzes[-1].question, "추가 문제")
        self.assertEqual(restarted.quizzes[-1].hint, "힌트")
        # "6" = 6번 문제 선택, "1" = 삭제 확인
        with patch("builtins.input", side_effect=["6", "1"]):
            restarted.delete_quiz()
        self.assertEqual(len(QuizGame(self.path).quizzes), 5)

    def test_delete_cancel(self):
        """삭제 중 0번 취소나 확인 단계 취소가 동작하는지 확인합니다."""
        for values in (["0"], ["1", "2"]):
            with patch("builtins.input", side_effect=values):
                self.game.delete_quiz()
            self.assertEqual(len(self.game.quizzes), 5)

    def test_empty_list_survives_restart(self):
        """문제를 모두 지워도 저장되고 오류가 없는지 확인합니다."""
        self.game.quizzes = []
        self.game.save()
        restarted = QuizGame(self.path)
        self.assertEqual(restarted.quizzes, [])
        restarted.play()
        restarted.show_list()
        restarted.delete_quiz()
        self.assertIn("등록된 퀴즈가 없습니다", self.output.getvalue())

    def test_unplayed_displays_distinct_message(self):
        """아직 게임을 안 했을 때 안내 문구가 나오는지 확인합니다."""
        self.game.show_score()
        self.game.show_history()
        self.assertIn("아직 끝까지", self.output.getvalue())
        self.assertIn("아직 게임 기록", self.output.getvalue())

    def test_interruption_records_partial_game_without_high_score(self):
        """도중 중단 시 '중단' 기록만 남고 최고 점수는 그대로인지 봅니다."""
        for interrupt in (EOFError, KeyboardInterrupt):
            with self.subTest(interrupt=interrupt):
                with self.assertRaises(interrupt):
                    # 2문제 중 1문제만 풀고 중단 신호를 보냅니다.
                    self.play(["2", "3", interrupt], count=2)
                record = self.game.history[-1]
                self.assertFalse(record["completed"])
                self.assertEqual(record["answered"], 1)
                self.assertEqual(record["score"], 50)
                self.assertIsNone(self.game.best_score)
        self.assertEqual(len(QuizGame(self.path).history), 2)

    def test_interrupt_during_registration_does_not_add_partial_quiz(self):
        """문제 추가 도중 중단하면 미완성 문제가 들어가지 않는지 확인합니다."""
        with (
            patch("builtins.input", side_effect=["문제", EOFError]),
            self.assertRaises(EOFError),
        ):
            self.game.add_quiz()
        self.assertEqual(len(self.game.quizzes), 5)

    def test_run_handles_eof_and_keyboard_interrupt_and_saves(self):
        """메뉴에서 중단해도 프로그램이 정상 종료되고 저장되는지 확인합니다."""
        for interrupt in (EOFError, KeyboardInterrupt):
            with patch("builtins.input", side_effect=interrupt):
                self.game.run()
            self.assertTrue(self.path.exists())

    def test_corrupt_json_utf8_and_schema_are_backed_up(self):
        """망가진 저장 파일은 백업하고 기본 데이터로 복구하는지 확인합니다."""
        for content in (
            b"{broken",  # JSON 문법 오류
            b"\xff",  # 글자 인코딩 오류
            b"[]",  # 구조가 다름(딕셔너리가 아님)
            b'{"quizzes": [], "best_score": true}',  # 값 형식 오류
        ):
            with self.subTest(content=content):
                self.path.write_bytes(content)
                restarted = QuizGame(self.path)
                self.assertEqual(len(restarted.quizzes), 5)
                backups = list(self.path.parent.glob("state.json.corrupt-*"))
                self.assertTrue(
                    any(p.read_bytes() == content for p in backups)
                )
                self.assertTrue(restarted.save())

    def test_malformed_history_recovers_all_data(self):
        """기록 형식이 틀리면 전체를 기본값으로 복구하는지 확인합니다."""
        data = {
            "quizzes": [],
            "best_score": None,
            "history": [{"date": "bad"}],
        }
        self.path.write_text(json.dumps(data), encoding="utf-8")
        restarted = QuizGame(self.path)
        self.assertEqual(len(restarted.quizzes), 5)
        self.assertEqual(restarted.history, [])

    def test_read_error_blocks_overwrite(self):
        """파일을 읽지 못하면 원본 보호를 위해 저장을 막는지 확인합니다."""
        with patch.object(
            Path, "open", side_effect=PermissionError("test denial")
        ):
            restarted = QuizGame(self.path)
        self.assertTrue(restarted.storage_blocked)
        self.assertFalse(restarted.save())

    def test_backup_failure_blocks_overwrite(self):
        """백업에 실패하면 손상 파일을 덮어쓰지 않는지 확인합니다."""
        self.path.write_text("bad", encoding="utf-8")
        with patch(
            "main.shutil.copy2", side_effect=PermissionError("test denial")
        ):
            restarted = QuizGame(self.path)
        self.assertFalse(restarted.save())
        self.assertEqual(self.path.read_text(encoding="utf-8"), "bad")

    def test_write_failure_preserves_previous_file(self):
        """저장 실패 시 이전 파일이 남고 임시 파일은 지워지는지 봅니다."""
        self.game.save()
        before = self.path.read_bytes()
        self.game.quizzes.clear()
        with patch.object(
            Path, "replace", side_effect=PermissionError("test denial")
        ):
            self.assertFalse(self.game.save())
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])

    def test_random_selection_does_not_change_bank(self):
        """무작위로 문제를 골라도 원래 문제 목록은 바뀌지 않는지 확인합니다."""
        before = [quiz.question for quiz in self.game.quizzes]
        with (
            patch("builtins.input", side_effect=["2", "1", "1"]),
            patch(
                "main.random.sample", wraps=__import__("random").sample
            ) as sample,
        ):
            self.game.play()
        sample.assert_called_once_with(self.game.quizzes, 2)
        self.assertEqual([quiz.question for quiz in self.game.quizzes], before)

    def test_subprocess_restart_and_foreign_working_directory(self):
        """다른 폴더에서 실행해도 main.py 옆에 저장되는지 확인합니다."""
        # 별도 프로세스에서 실제 진입점을 실행해 저장 위치를 확인합니다.
        project = Path(self.temp.name) / "project"
        project.mkdir()
        source = Path(__file__).resolve().parents[1]
        # 게임 파일들을 임시 project 폴더로 복사합니다.
        for name in (
            "main.py",
            "quiz.py",
            "default_quizzes.py",
            "input_helpers.py",
        ):
            shutil.copy2(source / name, project / name)
        command = [sys.executable, "-X", "utf8", str(project / "main.py")]
        # 첫 실행: 3번(목록) 보고 5번(종료) → 저장 파일 생성
        first = subprocess.run(
            command,
            input="3\n5\n",
            text=True,
            encoding="utf-8",
            capture_output=True,
            cwd=self.temp.name,
            timeout=10,
        )
        # 두 번째 실행: 4번(점수) 보고 5번(종료) → 저장 파일 불러오기
        second = subprocess.run(
            command,
            input="4\n5\n",
            text=True,
            encoding="utf-8",
            capture_output=True,
            cwd=self.temp.name,
            timeout=10,
        )
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("저장된 데이터를 불러왔습니다", second.stdout)
        self.assertTrue((project / "state.json").exists())
        self.assertFalse((Path(self.temp.name) / "state.json").exists())


# python tests/test_game.py 로 직접 실행할 때 모든 테스트를 돌립니다.
if __name__ == "__main__":
    unittest.main()
