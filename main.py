"""기초 상식 퀴즈 게임. 실행: python main.py"""

import json
import os
import random
from pathlib import Path
import shutil
import tempfile
from datetime import datetime

from default_quizzes import make_default_quizzes
from input_helpers import get_number, get_text
from quiz import Quiz

STATE_PATH = Path(__file__).resolve().parent / "state.json"


class QuizGame:
    """게임 전체의 메뉴, 퀴즈 목록과 점수를 관리합니다."""

    def __init__(self, state_path=STATE_PATH):
        self.state_path = Path(state_path)
        self.quizzes = make_default_quizzes()
        self.best_score = None
        self.storage_blocked = False
        self.load()

    def load(self):
        try:
            with self.state_path.open(encoding="utf-8") as file:
                data = json.load(file)
            if not isinstance(data, dict) or not isinstance(data["quizzes"], list):
                raise ValueError("저장 데이터 구조가 잘못되었습니다.")
            best = data["best_score"]
            if best is not None and (type(best) is not int or not 0 <= best <= 100):
                raise ValueError("최고 점수가 잘못되었습니다.")
            quizzes = []
            for item in data["quizzes"]:
                if not isinstance(item, dict):
                    raise ValueError("퀴즈는 객체여야 합니다.")
                quizzes.append(Quiz(item["question"], item["choices"], item["answer"],
                                    item.get("hint", "힌트가 없습니다.")))
            # 전체 데이터 검사 후 한 번에 적용합니다.
            self.quizzes, self.best_score = quizzes, best
            print(f"저장된 데이터를 불러왔습니다. (퀴즈 {len(quizzes)}개)")
        except FileNotFoundError:
            print("저장 파일이 없어 기본 퀴즈로 시작합니다.")
        except (ValueError, KeyError, TypeError, RecursionError) as error:
            print(f"저장 데이터가 손상되어 기본 데이터로 복구합니다: {error}")
            backup = self.state_path.with_name(
                self.state_path.name + ".corrupt-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            )
            try:
                shutil.copy2(self.state_path, backup)
                print(f"원본 보관: {backup.name}")
            except OSError:
                self.storage_blocked = True
                print("손상 파일을 보관할 수 없어 이번 실행에서는 저장하지 않습니다.")
        except OSError as error:
            self.storage_blocked = True
            print(f"파일 읽기 실패. 원본 보호를 위해 저장하지 않습니다: {error}")

    def save(self):
        if self.storage_blocked:
            print("파일 접근 문제로 저장하지 못했습니다. 메모리의 데이터만 유지됩니다.")
            return False
        data = {"quizzes": [quiz.to_dict() for quiz in self.quizzes],
                "best_score": self.best_score}
        temporary_path = None
        try:
            # 먼저 임시 파일을 완성하고 교체해 쓰기 실패 시 기존 파일을 보호합니다.
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False,
                                             dir=self.state_path.parent,
                                             prefix=self.state_path.name + ".", suffix=".tmp") as file:
                temporary_path = Path(file.name)
                json.dump(data, file, ensure_ascii=False, indent=2)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())
            temporary_path.replace(self.state_path)
        except OSError as error:
            print(f"파일 저장에 실패했습니다. 메모리의 데이터만 유지됩니다: {error}")
            return False
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass
        print("파일에 저장했습니다.")
        return True

    def show_menu(self):
        print("\n=== 기초 상식 퀴즈 ===")
        print("1. 퀴즈 풀기\n2. 퀴즈 추가\n3. 퀴즈 목록\n4. 점수 확인\n5. 종료")
        print("6. 퀴즈 삭제")

    def play(self):
        if not self.quizzes:
            print("등록된 퀴즈가 없습니다.")
            return
        count = get_number(f"풀 문제 수 (1~{len(self.quizzes)}): ", 1, len(self.quizzes))
        selected = random.sample(self.quizzes, count)
        correct = 0
        hints_used = 0
        for index, quiz in enumerate(selected, start=1):
            print(f"\n[문제 {index}/{count}]")
            quiz.show()
            hint_used = False
            while True:
                answer = get_number("정답 번호 (1~4, 힌트 0): ", 0, 4)
                if answer != 0:
                    break
                print(f"힌트: {quiz.hint}")
                if not hint_used:
                    hints_used += 1
                    hint_used = True
                    print("힌트 사용으로 최종 점수에서 10점 차감합니다.")
                else:
                    print("이미 확인한 힌트입니다. 추가 감점은 없습니다.")
            if quiz.check_answer(answer):
                print("정답입니다!")
                correct += 1
            else:
                print(f"오답입니다. 정답은 {quiz.answer}번입니다.")
        score = max(0, round(correct / count * 100) - hints_used * 10)
        print(f"결과: {count}문제 중 {correct}개 정답, {score}점")
        if self.best_score is None or score > self.best_score:
            self.best_score = score
            print("새로운 최고 점수입니다!")
        self.save()

    def show_score(self):
        if self.best_score is None:
            print("아직 끝까지 완료한 게임이 없습니다.")
        else:
            print(f"최고 점수: {self.best_score}점")

    def add_quiz(self):
        question = get_text("문제: ")
        choices = [get_text(f"선택지 {number}: ") for number in range(1, 5)]
        answer = get_number("정답 번호 (1~4): ", 1, 4)
        hint = get_text("힌트: ")
        # 입력을 모두 마친 뒤 추가하므로 중간 종료 시 미완성 문제가 남지 않습니다.
        self.quizzes.append(Quiz(question, choices, answer, hint))
        print("퀴즈를 추가했습니다.")
        self.save()

    def show_list(self):
        if not self.quizzes:
            print("등록된 퀴즈가 없습니다.")
            return
        print(f"\n등록된 퀴즈 목록 (총 {len(self.quizzes)}개)")
        for number, quiz in enumerate(self.quizzes, start=1):
            print(f"{number}. {quiz.question}")

    def delete_quiz(self):
        if not self.quizzes:
            print("등록된 퀴즈가 없습니다.")
            return
        self.show_list()
        number = get_number("삭제할 문제 번호 (취소 0): ", 0, len(self.quizzes))
        if number == 0:
            print("삭제를 취소했습니다.")
            return
        quiz = self.quizzes[number - 1]
        print(f"삭제할 문제: {quiz.question}")
        if get_number("삭제 확인 (1: 삭제, 2: 취소): ", 1, 2) == 2:
            print("삭제를 취소했습니다.")
            return
        self.quizzes.pop(number - 1)
        print("퀴즈를 삭제했습니다.")
        self.save()

    def run(self):
        try:
            while True:
                self.show_menu()
                menu = get_number("선택 (1~6): ", 1, 6)
                if menu == 5:
                    break
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
        except (KeyboardInterrupt, EOFError):
            print("\n입력이 중단되었습니다.")
        finally:
            self.save()
            print("게임을 종료합니다.")


if __name__ == "__main__":
    try:
        QuizGame().run()
    except (KeyboardInterrupt, EOFError):
        print("\n시작 또는 종료 작업이 중단되었습니다. 게임을 종료합니다.")
