"""저장·재시작·잘못된 입력·게임 중단 등 실제 요구사항을 검증합니다."""

import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from default_quizzes import make_default_quizzes
from input_helpers import get_number, get_text
from main import QuizGame
from quiz import Quiz


class GameTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "state.json"
        self.output = io.StringIO()
        self.redirect = contextlib.redirect_stdout(self.output)
        self.redirect.__enter__()
        self.addCleanup(self.redirect.__exit__, None, None, None)
        self.game = QuizGame(self.path)

    def play(self, values, count=1):
        quizzes = self.game.quizzes[:count]
        with patch("builtins.input", side_effect=values), patch("main.random.sample", return_value=quizzes):
            self.game.play()

    def test_numeric_input_recovers_from_all_invalid_cases(self):
        with patch("builtins.input", side_effect=["", "abc", "0", "9", " 2 "]):
            self.assertEqual(get_number("", 1, 4), 2)
        self.assertIn("아무것도", self.output.getvalue())
        self.assertIn("숫자로", self.output.getvalue())
        self.assertIn("1~4", self.output.getvalue())

    def test_required_text_retries_and_strips(self):
        with patch("builtins.input", side_effect=["", "  ", " 문제 "]):
            self.assertEqual(get_text(""), "문제")

    def test_default_five_valid_questions(self):
        self.assertEqual(len(self.game.quizzes), 5)
        self.assertIsNone(self.game.best_score)
        for quiz in make_default_quizzes():
            self.assertEqual(len(quiz.choices), 4)
            self.assertTrue(quiz.check_answer(quiz.answer))
            self.assertFalse(quiz.check_answer(0))

    def test_quiz_rejects_invalid_shapes_and_boolean_answer(self):
        for args in [("", ["a"] * 4, 1), ("q", ["a"], 1),
                     ("q", ["a", "b", "c", ""], 1), ("q", ["a"] * 4, True)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                Quiz(*args)

    def test_completed_game_and_restart_preserve_score_history(self):
        self.play(["1", "3"])
        restarted = QuizGame(self.path)
        self.assertEqual(restarted.best_score, 100)
        self.assertEqual(restarted.history[0]["correct"], 1)
        self.assertTrue(restarted.history[0]["completed"])

    def test_wrong_answer_does_not_lower_best(self):
        self.play(["1", "3"])
        self.play(["1", "1"])
        self.assertEqual(self.game.best_score, 100)
        self.assertEqual(self.game.history[-1]["score"], 0)

    def test_hint_repeated_only_deducts_once(self):
        self.play(["1", "0", "0", "3"])
        self.assertEqual(self.game.best_score, 90)
        self.assertEqual(self.game.history[-1]["hints_used"], 1)

    def test_hint_wrong_answer_score_has_zero_floor(self):
        self.play(["1", "0", "1"])
        self.assertEqual(self.game.best_score, 0)

    def test_question_count_retries(self):
        self.play(["", "abc", "0", "6", " 1 ", "3"])
        self.assertEqual(self.game.history[-1]["total"], 1)

    def test_add_restart_delete_restart(self):
        with patch("builtins.input", side_effect=["추가 문제", "가", "나", "다", "라", "2", "힌트"]):
            self.game.add_quiz()
        restarted = QuizGame(self.path)
        self.assertEqual(restarted.quizzes[-1].question, "추가 문제")
        self.assertEqual(restarted.quizzes[-1].hint, "힌트")
        with patch("builtins.input", side_effect=["6", "1"]):
            restarted.delete_quiz()
        self.assertEqual(len(QuizGame(self.path).quizzes), 5)

    def test_delete_cancel(self):
        for values in (["0"], ["1", "2"]):
            with patch("builtins.input", side_effect=values):
                self.game.delete_quiz()
            self.assertEqual(len(self.game.quizzes), 5)

    def test_empty_list_survives_restart(self):
        self.game.quizzes = []
        self.game.save()
        restarted = QuizGame(self.path)
        self.assertEqual(restarted.quizzes, [])
        restarted.play()
        restarted.show_list()
        restarted.delete_quiz()
        self.assertIn("등록된 퀴즈가 없습니다", self.output.getvalue())

    def test_unplayed_displays_distinct_message(self):
        self.game.show_score()
        self.game.show_history()
        self.assertIn("아직 끝까지", self.output.getvalue())
        self.assertIn("아직 게임 기록", self.output.getvalue())

    def test_interruption_records_partial_game_without_high_score(self):
        for interrupt in (EOFError, KeyboardInterrupt):
            with self.subTest(interrupt=interrupt):
                with self.assertRaises(interrupt):
                    self.play(["2", "3", interrupt], count=2)
                record = self.game.history[-1]
                self.assertFalse(record["completed"])
                self.assertEqual(record["answered"], 1)
                self.assertEqual(record["score"], 50)
                self.assertIsNone(self.game.best_score)
        self.assertEqual(len(QuizGame(self.path).history), 2)

    def test_interrupt_during_registration_does_not_add_partial_quiz(self):
        with patch("builtins.input", side_effect=["문제", EOFError]), self.assertRaises(EOFError):
            self.game.add_quiz()
        self.assertEqual(len(self.game.quizzes), 5)

    def test_run_handles_eof_and_keyboard_interrupt_and_saves(self):
        for interrupt in (EOFError, KeyboardInterrupt):
            with patch("builtins.input", side_effect=interrupt):
                self.game.run()
            self.assertTrue(self.path.exists())

    def test_corrupt_json_utf8_and_schema_are_backed_up(self):
        for content in (b'{broken', b'\xff', b'[]', b'{"quizzes": [], "best_score": true}'):
            with self.subTest(content=content):
                self.path.write_bytes(content)
                restarted = QuizGame(self.path)
                self.assertEqual(len(restarted.quizzes), 5)
                backups = list(self.path.parent.glob("state.json.corrupt-*"))
                self.assertTrue(any(p.read_bytes() == content for p in backups))
                self.assertTrue(restarted.save())

    def test_malformed_history_recovers_all_data(self):
        data = {"quizzes": [], "best_score": None, "history": [{"date": "bad"}]}
        self.path.write_text(json.dumps(data), encoding="utf-8")
        restarted = QuizGame(self.path)
        self.assertEqual(len(restarted.quizzes), 5)
        self.assertEqual(restarted.history, [])

    def test_read_error_blocks_overwrite(self):
        with patch.object(Path, "open", side_effect=PermissionError("test denial")):
            restarted = QuizGame(self.path)
        self.assertTrue(restarted.storage_blocked)
        self.assertFalse(restarted.save())

    def test_backup_failure_blocks_overwrite(self):
        self.path.write_text("bad", encoding="utf-8")
        with patch("main.shutil.copy2", side_effect=PermissionError("test denial")):
            restarted = QuizGame(self.path)
        self.assertFalse(restarted.save())
        self.assertEqual(self.path.read_text(encoding="utf-8"), "bad")

    def test_write_failure_preserves_previous_file(self):
        self.game.save()
        before = self.path.read_bytes()
        self.game.quizzes.clear()
        with patch.object(Path, "replace", side_effect=PermissionError("test denial")):
            self.assertFalse(self.game.save())
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])

    def test_random_selection_does_not_change_bank(self):
        before = [quiz.question for quiz in self.game.quizzes]
        with patch("builtins.input", side_effect=["2", "1", "1"]), patch("main.random.sample", wraps=__import__("random").sample) as sample:
            self.game.play()
        sample.assert_called_once_with(self.game.quizzes, 2)
        self.assertEqual([quiz.question for quiz in self.game.quizzes], before)

    def test_subprocess_restart_and_foreign_working_directory(self):
        # 별도 프로세스에서 실제 진입점을 실행해 저장 위치를 확인합니다.
        project = Path(self.temp.name) / "project"
        project.mkdir()
        source = Path(__file__).resolve().parents[1]
        for name in ("main.py", "quiz.py", "default_quizzes.py", "input_helpers.py"):
            shutil.copy2(source / name, project / name)
        command = [sys.executable, "-X", "utf8", str(project / "main.py")]
        first = subprocess.run(command, input="3\n5\n", text=True, encoding="utf-8", capture_output=True, cwd=self.temp.name, timeout=10)
        second = subprocess.run(command, input="4\n5\n", text=True, encoding="utf-8", capture_output=True, cwd=self.temp.name, timeout=10)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("저장된 데이터를 불러왔습니다", second.stdout)
        self.assertTrue((project / "state.json").exists())
        self.assertFalse((Path(self.temp.name) / "state.json").exists())


if __name__ == "__main__":
    unittest.main()
