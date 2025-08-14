📅 2025.08.14

# Azure Function을 이용한 논문 수집 및 요약 자동화

현재 GitHub Repository에 있는 코드를 로컬에서 실행하면, **arXiv**에서 지정된 검색 키워드에 맞는 논문을 수집한 뒤 **LLM**으로 요약하고, 중요도 순으로 **Top 10개**를 선별하여 메일로 전송하도록 구현할 수 있습니다.  

하지만 매번 수동으로 실행하는 것은 번거롭기 때문에, **특정 날짜/시간에 자동으로 코드가 실행되도록 설정**하는 것이 더 효율적입니다.  
자동화 방법은 다양하지만, 여기서는 **Azure Function**을 활용하는 방법을 소개합니다.

---

## Azure Function 구현 방법
Azure Function을 사용하기 위해서는 다음과 같은 방법이 있습니다.

- **Azure Portal UI**를 통한 설정
- **VS Code Extension**을 이용한 구현
- **Azure CLI** 또는 코드 기반 설정

아래는 순서대로 구현 과정을 설명합니다.

---

## 1. Function App 생성
먼저 **Function App**을 생성합니다.  
여러 옵션을 설정해야 하지만, Python으로 코드를 작성했기 때문에 **Runtime stack**은 반드시 `Python`으로 선택합니다.  
그 외 설정은 프로젝트 환경에 맞게 지정하면 됩니다.

<img width="426" height="443" alt="create-function-app" src="https://github.com/user-attachments/assets/804e31ff-7bd5-46b3-8853-016b2412cc25" />

---

## 2. Timer Trigger Function 생성
다음으로 실제 동작할 **Function**을 생성합니다.  
이때 **Trigger Type**은 `Timer trigger`로 선택합니다.

구현 로직은 다음과 같습니다.

- `genaisecuritynews.py` 실행
- `requirements.txt`에 명시된 모듈 설치
- `.env` 파일의 Key/Value를 `load_dotenv()`로 불러오기
- `function_app.py`에서 실행 함수를 지정하고, 실행 주기를 설정

---

## 3. 코드 구조
`genaisecuritynews.py`의 실행 함수를 `news_sender()`로 감싸고,  
`function_app.py`의 `my_timer_trigger` 함수에서 호출합니다.

아래 예시는 매주 월요일 오전 7시(UTC 기준) 실행되도록 설정한 CRON 표현(`0 0 22 * * 0`)입니다.  
`run_on_startup`은 기본적으로 `False`지만, 테스트 목적으로 Function 생성 또는 재시작 시 즉시 실행하려면 `True`로 설정할 수 있습니다.

<img width="525" height="364" alt="function" src="https://github.com/user-attachments/assets/26dd60d3-fabb-4e76-a3bc-625ff7fc9af4" />

```python
import datetime
import logging
import azure.functions as func
from genaisecuritynews import news_sender
from dotenv import load_dotenv
import os

if os.environ.get("WEBSITE_INSTANCE_ID") is None:  # Azure 환경이 아니면
    load_dotenv()

app = func.FunctionApp()

@app.function_name(name="my_timer_trigger")
@app.timer_trigger(schedule="0 0 22 * * 0", arg_name="mytimer", run_on_startup=True,
              use_monitor=False) 
def my_timer_trigger(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    news_sender()

    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function executed at %s', utc_timestamp)
```

---

## 4. 환경 변수 설정
`.env`의 **Key/Value**를 Azure Function에서 참조하려면,
**Settings → Environment variables → App settings** 탭에서 Key/Value를 하나씩 추가합니다

<img width="824" height="550" alt="environment_variables" src="https://github.com/user-attachments/assets/fb6a9dd7-87ac-43ef-9b33-29b1993af0b4" />

---

## 5. 실행 결과
Function App을 재시작하면 `function_app.py`가 실행되면서 **Environment variables**를 참조하여 `genaisecuritynews.py`를 실행하고, 요약된 논문이 메일로 전송됩니다.

<img width="1093" height="435" alt="email_with_summarized_papers" src="https://github.com/user-attachments/assets/4cd00fe6-b57e-46c8-9a9c-07d960899159" />

