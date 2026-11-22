"""기초 상식 퀴즈 게임. 실행: python main.py"""

from default_quizzes import make_default_quizzes
from input_helpers import get_number


class QuizGame:
    """게임 전체의 메뉴, 퀴즈 목록과 점수를 관리합니다."""

    def __init__(self):
        self.quizzes = make_default_quizzes()
        self.best_score = None

    def show_menu(self):
        print("\n=== 기초 상식 퀴즈 ===")
        print("1. 퀴즈 풀기\n2. 퀴즈 추가\n3. 퀴즈 목록\n4. 점수 확인\n5. 종료")

    def run(self):
        try:
            while True:
                self.show_menu()
                menu = get_number("선택 (1~5): ", 1, 5)
                if menu == 5:
                    break
                print("기능을 준비 중입니다.")
        except (KeyboardInterrupt, EOFError):
            print("\n입력이 중단되었습니다.")
        finally:
            print("게임을 종료합니다.")


if __name__ == "__main__":
    QuizGame().run()
