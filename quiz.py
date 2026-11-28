"""Quiz는 문제 한 개의 데이터와 정답 확인을 담당합니다.

이 파일은 퀴즈 '문제 한 개'를 표현하는 설계도(클래스)를 담고 있습니다.
문제 글, 선택지 4개, 정답 번호, 힌트를 한 묶음으로 보관하고,
화면에 보여 주기·정답 확인·저장용 변환 기능을 제공합니다.
"""


class Quiz:
    """퀴즈 문제 한 개를 나타내는 클래스입니다."""

    def __init__(self, question, choices, answer, hint="힌트가 없습니다."):
        """새 문제를 만들 때 값이 올바른지 검사하고 저장하는 기능입니다.

        잘못된 값이 들어오면 ValueError를 일으켜 문제가 만들어지지
        않도록 막습니다. (예: 빈 문제, 선택지가 4개가 아님)
        """
        # 문제 글이 문자열이 아니거나 공백뿐이면 거부합니다.
        if not isinstance(question, str) or not question.strip():
            raise ValueError("문제는 빈 문자열일 수 없습니다.")
        # 선택지는 반드시 리스트이고 정확히 4개여야 합니다.
        if not isinstance(choices, list) or len(choices) != 4:
            raise ValueError("선택지는 네 개여야 합니다.")
        # 선택지 4개 중 하나라도 비어 있거나 글자가 아니면 거부합니다.
        if any(
            not isinstance(choice, str) or not choice.strip()
            for choice in choices
        ):
            raise ValueError("선택지는 비어 있지 않은 글자여야 합니다.")
        # 정답은 1~4 정수만 허용합니다.
        # type(...) is int 를 쓰는 이유: True/False도 정수로 취급되기
        # 때문에 이를 걸러 내기 위해서입니다.
        if type(answer) is not int or not 1 <= answer <= 4:
            raise ValueError("정답은 1~4 정수여야 합니다.")
        # 힌트도 빈 글자는 허용하지 않습니다.
        if not isinstance(hint, str) or not hint.strip():
            raise ValueError("힌트는 빈 문자열일 수 없습니다.")
        # 검사를 모두 통과하면 앞뒤 공백을 지우고 객체에 저장합니다.
        self.question = question.strip()
        self.choices = [choice.strip() for choice in choices]
        self.answer = answer
        self.hint = hint.strip()

    def show(self):
        """문제와 선택지를 번호와 함께 화면에 출력하는 기능입니다."""
        print(self.question)
        # enumerate(..., start=1)로 1번부터 번호를 붙여 출력합니다.
        for number, choice in enumerate(self.choices, start=1):
            print(f"{number}. {choice}")

    def check_answer(self, user_answer):
        """사용자가 고른 번호가 정답인지 True/False로 알려 주는 기능입니다."""
        return user_answer == self.answer

    def to_dict(self):
        """문제를 JSON 파일에 저장할 수 있도록 딕셔너리로 바꾸는 기능입니다."""
        return {
            "question": self.question,
            "choices": self.choices,
            "answer": self.answer,
            "hint": self.hint,
        }
