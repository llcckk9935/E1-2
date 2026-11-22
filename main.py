"""기초 상식 퀴즈 게임. 실행: python main.py"""

from default_quizzes import make_default_quizzes
from input_helpers import get_number, get_text
from quiz import Quiz


class QuizGame:
    """게임 전체의 메뉴, 퀴즈 목록과 점수를 관리합니다."""

    def __init__(self):
        self.quizzes = make_default_quizzes()
        self.best_score = None

    def show_menu(self):
        print("\n=== 기초 상식 퀴즈 ===")
        print("1. 퀴즈 풀기\n2. 퀴즈 추가\n3. 퀴즈 목록\n4. 점수 확인\n5. 종료")

    def play(self):
        if not self.quizzes:
            print("등록된 퀴즈가 없습니다.")
            return
        correct = 0
        for index, quiz in enumerate(self.quizzes, start=1):
            print(f"\n[문제 {index}/{len(self.quizzes)}]")
            quiz.show()
            answer = get_number("정답 번호 (1~4): ", 1, 4)
            if quiz.check_answer(answer):
                print("정답입니다!")
                correct += 1
            else:
                print(f"오답입니다. 정답은 {quiz.answer}번입니다.")
        score = round(correct / len(self.quizzes) * 100)
        print(f"결과: {len(self.quizzes)}문제 중 {correct}개 정답, {score}점")

    def add_quiz(self):
        question = get_text("문제: ")
        choices = [get_text(f"선택지 {number}: ") for number in range(1, 5)]
        answer = get_number("정답 번호 (1~4): ", 1, 4)
        hint = get_text("힌트: ")
        # 입력을 모두 마친 뒤 추가하므로 중간 종료 시 미완성 문제가 남지 않습니다.
        self.quizzes.append(Quiz(question, choices, answer, hint))
        print("퀴즈를 추가했습니다.")

    def show_list(self):
        if not self.quizzes:
            print("등록된 퀴즈가 없습니다.")
            return
        print(f"\n등록된 퀴즈 목록 (총 {len(self.quizzes)}개)")
        for number, quiz in enumerate(self.quizzes, start=1):
            print(f"{number}. {quiz.question}")

    def run(self):
        try:
            while True:
                self.show_menu()
                menu = get_number("선택 (1~5): ", 1, 5)
                if menu == 5:
                    break
                if menu == 1:
                    self.play()
                elif menu == 2:
                    self.add_quiz()
                elif menu == 3:
                    self.show_list()
                else:
                    print("기능을 준비 중입니다.")
        except (KeyboardInterrupt, EOFError):
            print("\n입력이 중단되었습니다.")
        finally:
            print("게임을 종료합니다.")


if __name__ == "__main__":
    QuizGame().run()
