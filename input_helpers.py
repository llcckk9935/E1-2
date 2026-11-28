"""입력 검사를 공통 함수로 묶어 메뉴와 정답 입력에서 재사용합니다.

사용자가 키보드로 잘못된 값을 넣어도 프로그램이 멈추지 않고
"다시 입력해 주세요"라고 안내하며 올바른 값을 받을 때까지 반복합니다.
"""


def get_number(message, minimum, maximum):
    """앞뒤 공백을 제거하고 허용 범위 안의 정수를 반환합니다.

    이 함수는 메뉴 번호·정답 번호처럼 '정해진 범위의 숫자'를
    입력받는 기능입니다. 올바른 숫자가 들어올 때까지 계속 묻습니다.
    """
    # while True: 올바른 값이 나와 return 할 때까지 무한 반복합니다.
    while True:
        # input()으로 입력을 받고 .strip()으로 앞뒤 공백을 지웁니다.
        text = input(message).strip()
        # 아무것도 입력하지 않았으면 안내 후 다시 묻습니다.
        if not text:
            print("아무것도 입력하지 않았습니다.")
            continue
        # 글자를 정수로 바꿔 봅니다. "abc"처럼 숫자가 아니면 오류가 납니다.
        try:
            number = int(text)
        except ValueError:
            print("숫자로 입력해 주세요.")
            continue
        # 범위(minimum~maximum) 안이면 그 숫자를 돌려주고 끝냅니다.
        if minimum <= number <= maximum:
            return number
        # 범위를 벗어나면 허용 범위를 알려 주고 다시 묻습니다.
        print(f"{minimum}~{maximum} 사이의 번호를 입력해 주세요.")


def get_text(message):
    """문제와 선택지처럼 비어 있으면 안 되는 글자를 입력받습니다.

    공백만 입력하면 다시 묻고, 내용이 있으면 공백을 지워 돌려줍니다.
    """
    while True:
        text = input(message).strip()
        # 내용이 있으면 바로 돌려줍니다.
        if text:
            return text
        print("내용을 입력해 주세요.")
