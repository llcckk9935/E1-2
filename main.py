"""기초 상식 퀴즈 게임. 실행: python main.py

이 파일은 게임의 '본체'입니다. 메뉴를 보여 주고, 퀴즈 풀기·추가·
목록·점수·삭제·기록 기능을 실행하며, 데이터를 state.json에
저장하고 다시 불러옵니다.
"""

# --- 파이썬 기본 도구(표준 라이브러리) 가져오기 ---
import json  # 데이터를 JSON 파일로 저장/불러오기
import os  # 파일을 디스크에 확실히 기록(fsync)
import random  # 문제를 무작위로 고르기
import shutil  # 손상된 파일을 복사해 백업
import tempfile  # 임시 파일 만들기(안전한 저장용)
from datetime import datetime  # 게임 기록 날짜·시간
from pathlib import Path  # 파일 경로를 편하게 다루기

# --- 우리가 직접 만든 다른 파일에서 기능 가져오기 ---
from default_quizzes import make_default_quizzes  # 기본 문제 5개
from input_helpers import get_number, get_text  # 안전한 입력 함수
from quiz import Quiz  # 문제 한 개의 설계도

# 저장 파일 위치: 이 main.py가 있는 폴더 안의 state.json
# (어느 폴더에서 실행하든 항상 같은 위치에 저장되도록 합니다.)
STATE_PATH = Path(__file__).resolve().parent / "state.json"


class QuizGame:
    """게임 전체의 메뉴, 퀴즈 목록과 점수를 관리합니다."""

    def __init__(self, state_path=STATE_PATH):
        """게임 시작 시 기본값을 준비하고 저장 파일을 읽는 기능입니다."""
        self.state_path = Path(state_path)  # 저장 파일 경로
        self.quizzes = make_default_quizzes()  # 우선 기본 문제로 시작
        self.best_score = None  # 최고 점수(아직 없음)
        self.history = []  # 지금까지의 게임 기록 목록
        # 파일에 문제가 있어 저장하면 위험할 때 True로 바꿉니다.
        self.storage_blocked = False
        # 저장 파일이 있으면 불러와 기본값을 덮어씁니다.
        self.load()

    def load(self):
        """state.json을 읽어 문제·최고 점수·기록을 복원하는 기능입니다.

        파일이 없거나 망가져 있어도 프로그램이 멈추지 않고
        기본 데이터로 시작하며, 망가진 파일은 백업해 둡니다.
        """
        try:
            # 저장 파일을 열어 JSON 내용을 파이썬 데이터로 읽습니다.
            with self.state_path.open(encoding="utf-8") as file:
                data = json.load(file)
            # 전체 구조가 {"quizzes": [...], ...} 형태인지 확인합니다.
            if not isinstance(data, dict) or not isinstance(
                data["quizzes"], list
            ):
                raise ValueError("저장 데이터 구조가 잘못되었습니다.")
            # 최고 점수는 없거나(None) 0~100 정수여야 합니다.
            best = data["best_score"]
            if best is not None and (
                type(best) is not int or not 0 <= best <= 100
            ):
                raise ValueError("최고 점수가 잘못되었습니다.")
            # 저장된 문제들을 하나씩 Quiz 객체로 다시 만듭니다.
            # (Quiz가 값 검사를 하므로 이상한 문제는 여기서 걸러집니다.)
            quizzes = []
            for item in data["quizzes"]:
                if not isinstance(item, dict):
                    raise ValueError("퀴즈는 객체여야 합니다.")
                quizzes.append(
                    Quiz(
                        item["question"],
                        item["choices"],
                        item["answer"],
                        item.get("hint", "힌트가 없습니다."),
                    )
                )
            # 게임 기록도 형식이 올바른지 검사합니다.
            history = data.get("history", [])
            self.validate_history(history)
            # 전체 데이터 검사 후 한 번에 적용합니다.
            self.quizzes, self.best_score = quizzes, best
            self.history = history
            print(f"저장된 데이터를 불러왔습니다. (퀴즈 {len(quizzes)}개)")
        except FileNotFoundError:
            # 처음 실행이라 저장 파일이 없는 경우입니다.
            print("저장 파일이 없어 기본 퀴즈로 시작합니다.")
        except (ValueError, KeyError, TypeError, RecursionError) as error:
            # 파일 내용이 깨졌거나 형식이 틀린 경우입니다.
            print(f"저장 데이터가 손상되어 기본 데이터로 복구합니다: {error}")
            # 원본을 잃지 않도록 날짜·시간을 붙인 백업 파일 이름을 만듭니다.
            backup = self.state_path.with_name(
                self.state_path.name
                + ".corrupt-"
                + datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            )
            try:
                shutil.copy2(self.state_path, backup)
                print(f"원본 보관: {backup.name}")
            except OSError:
                # 백업조차 실패하면 원본을 덮어쓰지 않도록 저장을 막습니다.
                self.storage_blocked = True
                print(
                    "손상 파일을 보관할 수 없어 "
                    "이번 실행에서는 저장하지 않습니다."
                )
        except OSError as error:
            # 권한 문제 등으로 파일을 읽지 못한 경우: 저장을 막아 보호합니다.
            self.storage_blocked = True
            print(
                f"파일 읽기 실패. 원본 보호를 위해 저장하지 않습니다: {error}"
            )

    def save(self):
        """문제·최고 점수·기록을 state.json에 안전하게 저장합니다.

        저장에 성공하면 True, 실패하면 False를 돌려줍니다.
        """
        # 파일에 문제가 있었던 실행이라면 저장하지 않습니다.
        if self.storage_blocked:
            print(
                "파일 접근 문제로 저장하지 못했습니다. "
                "메모리의 데이터만 유지됩니다."
            )
            return False
        # 저장할 내용을 하나의 딕셔너리로 모읍니다.
        data = {
            "quizzes": [quiz.to_dict() for quiz in self.quizzes],
            "best_score": self.best_score,
            "history": self.history,
        }
        temporary_path = None
        try:
            # 임시 파일을 완성하고 교체합니다.
            # 쓰기 실패 시 기존 파일을 보호합니다.
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                delete=False,
                dir=self.state_path.parent,
                prefix=self.state_path.name + ".",
                suffix=".tmp",
            ) as file:
                temporary_path = Path(file.name)
                # ensure_ascii=False: 한글을 그대로 저장
                # indent=2: 사람이 읽기 쉽게 들여쓰기
                json.dump(data, file, ensure_ascii=False, indent=2)
                file.write("\n")
                file.flush()  # 버퍼에 남은 내용을 파일로 보냅니다.
                os.fsync(file.fileno())  # 디스크에 실제로 기록합니다.
            # 다 쓴 임시 파일로 기존 state.json을 한 번에 바꿔치기합니다.
            temporary_path.replace(self.state_path)
        except OSError as error:
            print(
                "파일 저장에 실패했습니다. "
                f"메모리의 데이터만 유지됩니다: {error}"
            )
            return False
        finally:
            # 성공·실패와 상관없이 남은 임시 파일이 있으면 지웁니다.
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass
        print("파일에 저장했습니다.")
        return True

    def show_menu(self):
        """메인 메뉴(1~7번)를 화면에 출력하는 기능입니다."""
        print("\n=== 기초 상식 퀴즈 ===")
        print(
            "1. 퀴즈 풀기\n2. 퀴즈 추가\n3. 퀴즈 목록\n4. 점수 확인\n5. 종료"
        )
        print("6. 퀴즈 삭제\n7. 게임 기록")

    @staticmethod
    def validate_history(history):
        """저장된 게임 기록이 올바른 형식·값인지 검사하는 기능입니다.

        문제가 있으면 ValueError 등을 일으켜 load()가 복구하게 합니다.
        """
        # 기록 전체는 리스트여야 합니다.
        if not isinstance(history, list):
            raise ValueError("게임 기록은 목록이어야 합니다.")
        for record in history:
            # 기록 한 건은 딕셔너리여야 합니다.
            if not isinstance(record, dict):
                raise ValueError("게임 기록 형식이 잘못되었습니다.")
            # 날짜는 글자이고 실제 날짜 형식(ISO)이어야 합니다.
            if not isinstance(record["date"], str):
                raise ValueError("기록 날짜는 글자여야 합니다.")
            datetime.fromisoformat(record["date"])
            # 숫자 항목들은 모두 정수여야 합니다.
            for key in ("total", "answered", "correct", "hints_used", "score"):
                if type(record[key]) is not int:
                    raise ValueError("게임 기록의 수치는 정수여야 합니다.")
            # 완료 여부는 True/False여야 합니다.
            if type(record["completed"]) is not bool:
                raise ValueError("게임 완료 여부가 잘못되었습니다.")
            # 숫자 관계 확인: 0 ≤ 정답 수 ≤ 응답 수 ≤ 전체 문제 수
            total, answered = record["total"], record["answered"]
            if not (
                total >= 1 and 0 <= record["correct"] <= answered <= total
            ):
                raise ValueError("게임 기록의 문제 수가 잘못되었습니다.")
            # 힌트는 문제 수보다 많이 쓸 수 없습니다.
            if not 0 <= record["hints_used"] <= total:
                raise ValueError("힌트 사용 수가 잘못되었습니다.")
            # 완료한 게임이면 모든 문제에 답했어야 합니다.
            if record["completed"] and answered != total:
                raise ValueError("완료 기록의 응답 수가 잘못되었습니다.")
            # 점수 규칙(정답률×100 - 힌트×10, 최소 0점)으로 다시 계산해
            # 저장된 점수와 같은지 확인합니다.
            expected = max(
                0,
                round(record["correct"] / total * 100)
                - record["hints_used"] * 10,
            )
            if record["score"] != expected:
                raise ValueError("기록 점수가 계산 규칙과 다릅니다.")

    def record_result(self, total, answered, correct, hints_used, completed):
        """한 판의 점수를 계산하고 기록·최고 점수를 저장합니다."""
        # 점수 = 정답률(%) - 힌트 1회당 10점, 단 0점보다 낮아지지 않음
        score = max(0, round(correct / total * 100) - hints_used * 10)
        # 이번 게임 기록을 history 목록에 추가합니다.
        self.history.append(
            {
                "date": datetime.now()
                .astimezone()
                .isoformat(timespec="seconds"),
                "total": total,
                "answered": answered,
                "correct": correct,
                "hints_used": hints_used,
                "score": score,
                "completed": completed,
            }
        )
        status = "완료" if completed else "중단"
        print(
            f"결과 ({status}): {total}문제 중 {answered}개 응답, "
            f"{correct}개 정답, {score}점"
        )
        # 끝까지 완료한 게임만 최고 점수 갱신 대상입니다.
        if completed and (self.best_score is None or score > self.best_score):
            self.best_score = score
            print("새로운 최고 점수입니다!")
        self.save()

    def show_history(self):
        """지금까지 플레이한 게임 기록을 번호순으로 보여 주는 기능입니다."""
        if not self.history:
            print("아직 게임 기록이 없습니다.")
            return
        for number, record in enumerate(self.history, start=1):
            status = "완료" if record["completed"] else "중단"
            print(
                f"{number}. {record['date']} | {status} | "
                f"{record['total']}문제 중 {record['answered']}개 응답, "
                f"{record['correct']}개 정답 | "
                f"힌트 {record['hints_used']}회 | {record['score']}점"
            )

    def play(self):
        """퀴즈를 무작위로 골라 풀게 하고 채점하는 기능입니다(메뉴 1번)."""
        if not self.quizzes:
            print("등록된 퀴즈가 없습니다.")
            return
        # 몇 문제를 풀지 입력받습니다(1 ~ 등록된 문제 수).
        count = get_number(
            f"풀 문제 수 (1~{len(self.quizzes)}): ", 1, len(self.quizzes)
        )
        # 원본 목록은 그대로 두고, 중복 없이 count개를 무작위로 뽑습니다.
        selected = random.sample(self.quizzes, count)
        correct = 0  # 맞힌 문제 수
        hints_used = 0  # 힌트를 본 문제 수
        answered = 0  # 답을 낸 문제 수
        try:
            for index, quiz in enumerate(selected, start=1):
                print(f"\n[문제 {index}/{count}]")
                quiz.show()
                hint_used = False  # 이 문제에서 힌트를 봤는지 여부
                # 0을 누르면 힌트, 1~4를 누르면 정답 제출입니다.
                while True:
                    answer = get_number("정답 번호 (1~4, 힌트 0): ", 0, 4)
                    if answer != 0:
                        break
                    print(f"힌트: {quiz.hint}")
                    # 같은 문제에서 힌트를 여러 번 봐도 감점은 1번만 합니다.
                    if not hint_used:
                        hints_used += 1
                        hint_used = True
                        print("힌트 사용으로 최종 점수에서 10점 차감합니다.")
                    else:
                        print("이미 확인한 힌트입니다. 추가 감점은 없습니다.")
                answered += 1
                # 정답이면 맞힌 수를 1 늘리고, 아니면 정답을 알려 줍니다.
                if quiz.check_answer(answer):
                    correct += 1
                    print("정답입니다!")
                else:
                    print(f"오답입니다. 정답은 {quiz.answer}번입니다.")
        except KeyboardInterrupt, EOFError:
            # Ctrl+C 등으로 도중에 멈추면 '중단' 기록을 남기고
            # 예외를 다시 위로 전달(raise)해 종료 처리를 이어 갑니다.
            self.record_result(
                count, answered, correct, hints_used, completed=False
            )
            raise
        # 모든 문제를 다 풀면 '완료' 기록을 남깁니다.
        self.record_result(
            count, answered, correct, hints_used, completed=True
        )

    def show_score(self):
        """최고 점수를 보여 주는 기능입니다(메뉴 4번)."""
        if self.best_score is None:
            print("아직 끝까지 완료한 게임이 없습니다.")
        else:
            print(f"최고 점수: {self.best_score}점")

    def add_quiz(self):
        """새 문제를 입력받아 목록에 추가하는 기능입니다(메뉴 2번)."""
        question = get_text("문제: ")
        # 선택지 1~4를 차례로 입력받아 리스트로 만듭니다.
        choices = [get_text(f"선택지 {number}: ") for number in range(1, 5)]
        answer = get_number("정답 번호 (1~4): ", 1, 4)
        hint = get_text("힌트: ")
        # 입력을 모두 마친 뒤 추가합니다.
        # 중간 종료 시 미완성 문제가 남지 않습니다.
        self.quizzes.append(Quiz(question, choices, answer, hint))
        print("퀴즈를 추가했습니다.")
        self.save()

    def show_list(self):
        """등록된 문제 목록을 번호와 함께 보여 주는 기능입니다(메뉴 3번)."""
        if not self.quizzes:
            print("등록된 퀴즈가 없습니다.")
            return
        print(f"\n등록된 퀴즈 목록 (총 {len(self.quizzes)}개)")
        for number, quiz in enumerate(self.quizzes, start=1):
            print(f"{number}. {quiz.question}")

    def delete_quiz(self):
        """번호를 골라 문제를 삭제하는 기능입니다(메뉴 6번).

        실수로 지우지 않도록 0번 취소와 한 번 더 확인하는 단계가 있습니다.
        """
        if not self.quizzes:
            print("등록된 퀴즈가 없습니다.")
            return
        self.show_list()
        number = get_number(
            "삭제할 문제 번호 (취소 0): ", 0, len(self.quizzes)
        )
        if number == 0:
            print("삭제를 취소했습니다.")
            return
        # 화면 번호는 1부터, 리스트 위치(인덱스)는 0부터라서 1을 뺍니다.
        quiz = self.quizzes[number - 1]
        print(f"삭제할 문제: {quiz.question}")
        if get_number("삭제 확인 (1: 삭제, 2: 취소): ", 1, 2) == 2:
            print("삭제를 취소했습니다.")
            return
        self.quizzes.pop(number - 1)
        print("퀴즈를 삭제했습니다.")
        self.save()

    def run(self):
        """메뉴를 반복해서 보여 주고 선택한 기능을 실행하는 기능입니다.

        5번(종료)을 고르거나 입력이 중단되면 저장 후 끝냅니다.
        """
        try:
            while True:
                self.show_menu()
                menu = get_number("선택 (1~7): ", 1, 7)
                if menu == 5:
                    break  # 반복을 끝내고 종료합니다.
                # 선택한 번호에 맞는 기능을 실행합니다.
                if menu == 1:
                    self.play()
                elif menu == 2:
                    self.add_quiz()
                elif menu == 3:
                    self.show_list()
                elif menu == 4:
                    self.show_score()
                elif menu == 6:
                    self.delete_quiz()
                elif menu == 7:
                    self.show_history()
        except KeyboardInterrupt, EOFError:
            # Ctrl+C 또는 입력 끝(EOF)이 들어오면 친절하게 안내합니다.
            print("\n입력이 중단되었습니다.")
        finally:
            # 어떤 이유로 끝나든 마지막에 반드시 저장합니다.
            self.save()
            print("게임을 종료합니다.")


# 이 파일을 직접 실행했을 때만(python main.py) 게임을 시작합니다.
# 테스트 코드에서 import 할 때는 실행되지 않습니다.
if __name__ == "__main__":
    try:
        QuizGame().run()
    except KeyboardInterrupt, EOFError:
        # 게임 시작·종료 중에 중단돼도 오류 화면 대신 안내만 보여 줍니다.
        print("\n시작 또는 종료 작업이 중단되었습니다. 게임을 종료합니다.")
