"""입력 검사를 공통 함수로 묶어 메뉴와 정답 입력에서 재사용합니다."""


def get_number(message, minimum, maximum):
    """앞뒤 공백을 제거하고 허용 범위 안의 정수를 반환합니다."""
    while True:
        text = input(message).strip()
        if not text:
            print("아무것도 입력하지 않았습니다.")
            continue
        try:
            number = int(text)
        except ValueError:
            print("숫자로 입력해 주세요.")
            continue
        if minimum <= number <= maximum:
            return number
        print(f"{minimum}~{maximum} 사이의 번호를 입력해 주세요.")


def get_text(message):
    """문제와 선택지처럼 비어 있으면 안 되는 글자를 입력받습니다."""
    while True:
        text = input(message).strip()
        if text:
            return text
        print("내용을 입력해 주세요.")
