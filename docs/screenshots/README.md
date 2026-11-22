# 실제 화면 캡처

2026-11-22, GitHub에서 새로 clone한 `submission/` 작업본으로 촬영했습니다.
이미지는 실제 앱 창을 캡처한 원본 JPEG이며 화면 내용을 합성하거나 다시 그리지 않았습니다.

## 실행 방식

게임은 최종 `main.py`를 `python -X utf8 -u main.py`로 실행했습니다. 캡처용 로컬 창이 실행 중인 Python 프로세스의 표준입력·표준출력에 직접 연결됩니다. 실제 메뉴와 문제 데이터를 입력하고 프로그램이 출력한 결과를 표시했습니다. 게임 코드나 점수 계산은 촬영을 위해 바꾸지 않았습니다. 이 창은 일반 터미널을 가장한 것이 아니라, 제목과 상단에 표준입출력 연결임을 표시한 캡처 보조 창입니다.

개발 환경과 Git 그래프는 새 복제본에서 실제로 실행한 명령의 출력을 파일로 보관하고, VS Code 편집기에서 해당 파일을 열어 캡처했습니다. 터미널 창을 촬영했다고 주장하지 않습니다. 원문은 `../evidence/current-environment.txt`와 `../evidence/current-git-log.txt`입니다. Git 그래프는 보완용 문서·이미지를 커밋하기 전의 실제 기존 개발 이력 스냅샷입니다.

캡처 도우미 소스와 실행 파일은 `outputs/`의 로컬 작업 자료로만 보관하며 제출 게임에는 포함하지 않습니다. 게임 실행에는 Python 표준 라이브러리만 필요합니다.

## 이미지 목록

| 이미지 | 확인할 내용 |
| --- | --- |
| [menu.jpg](menu.jpg) | 첫 실행 기본 데이터와 메뉴 |
| [add_quiz.jpg](add_quiz.jpg) | 문제·선택지·정답·힌트 등록 완료 및 파일 저장 |
| [list.jpg](list.jpg) | 기본 5개와 추가한 문제를 합한 6개 목록 |
| [play.jpg](play.jpg) | 문제 수 선택 후 실제 무작위 출제 |
| [hint.jpg](hint.jpg) | 힌트 표시와 10점 감점 안내 |
| [result.jpg](result.jpg) | 정답 처리, 90점 결과, 최고 점수 갱신·저장 |
| [score.jpg](score.jpg) | 점수 메뉴의 최고 점수 90점 조회 |
| [restart.jpg](restart.jpg) | 종료 후 새 프로세스가 퀴즈 6개를 불러옴 |
| [restart_score.jpg](restart_score.jpg) | 재시작 후 최고 점수 90점 유지 |
| [environment.jpg](environment.jpg) | VS Code, Python·Git 버전, Git 작성자·원격·작업본 경로 |
| [git_log.jpg](git_log.jpg) | 실제 `git log --oneline --graph --all` 결과와 기능 브랜치 병합 |

이미지 및 실행 코드의 SHA-256은 `../evidence/capture-manifest.json`에 기록했습니다. 촬영에 사용한 실제 플레이 데이터는 `state.json`에만 남으며 개인 실행 데이터이므로 Git과 제출 ZIP에서 제외합니다.
