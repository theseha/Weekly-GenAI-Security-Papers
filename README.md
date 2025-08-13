# 📄 Weekly AI Security Papers Summary

이 프로젝트는 **arXiv**에서 최신 AI 보안 관련 논문을 자동으로 수집하고,  
**Azure OpenAI**를 이용해 한글로 3개의 핵심 Bullet Point로 요약한 뒤,  
이메일로 발송하는 자동화 스크립트입니다.

원문(영어)는 여기서 확인 가능하고, 요약 방식 및 검색 키워드 등 일부 수정하였습니다. (https://github.com/9b/applied-gai-secnews/blob/main/README.md)

---

## ✨ 주요 기능
- arXiv API를 통해 최근 N일간의 AI 보안 관련 논문 검색
- MongoDB에 논문 메타데이터 저장 (중복 방지)
- Azure OpenAI를 이용한 한글 요약 (3개의 Bullet Point, HTML 형식)
- 논문 중요도 평가 후 상위 N개만 이메일 발송
- Gmail SMTP를 이용한 HTML 이메일 전송

---

## 📦 설치 방법

### 1. 저장소 클론
```bash
git clone https://github.com/your-username/weekly-ai-security-papers.git
cd weekly-ai-security-papers

### 2. 가상환경 생성 및 활성화
BASH
python -m venv venv
source venv/bin/activate   # macOS / Linux
venv\Scripts\activate      # Windows

###3. 필수 패키지 설치
BASH
pip install -r requirements.txt
⚙️ 환경 변수 설정
.env 파일을 프로젝트 루트에 생성하고 아래 내용을 채워주세요.

ENV
# Azure OpenAI 설정
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_API_VERSION=2024-06-01
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=your_deployment_name

# MongoDB 설정
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net
MONGO_DB=your_database_name
MONGO_COLLECTION=your_collection_name

# 이메일 발송 설정 (Gmail)
GOOG_APP_EMAIL=your_email@gmail.com
GOOG_APP_PASSKEY=your_google_app_password
EMAIL_LIST=recipient1@example.com,recipient2@example.com
참고: Gmail 발송을 위해서는 Google App Password를 발급받아야 합니다.

🚀 실행 방법
BASH
python main.py
스크립트 실행 시 arXiv에서 논문을 검색하고, MongoDB에 저장 후 요약을 생성합니다.
중요도 평가를 거쳐 상위 10개의 논문이 HTML 이메일로 발송됩니다.
📂 프로젝트 구조
TEXT
.
├── main.py                # 메인 실행 스크립트
├── requirements.txt       # 필요한 Python 패키지 목록
├── .env                   # 환경 변수 파일 (Git에 업로드 금지)
└── README.md              # 프로젝트 설명 문서
🛠 사용 기술
Python 3.9+
Azure OpenAI API
MongoDB
arXiv API
Gmail SMTP
📧 결과 예시
이메일에는 다음과 같이 논문 제목(영문)과 한글 요약이 포함됩니다.

TEXT
제목: Selective KV-Cache Sharing to Mitigate Timing Side-Channels in LLM Inference
- 글로벌 KV-캐시 공유는 LLM 추론 속도를 높이는 핵심 최적화 기법입니다.
- 그러나 새로운 타이밍 사이드 채널 공격 가능성을 노출합니다.
- 기존 방어 기법은 성능 저하 문제로 대규모 배포에 부적합합니다.
📜 라이선스
이 프로젝트는 MIT 라이선스를 따릅니다.