import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
from openai import AzureOpenAI
import requests
import xml.etree.ElementTree as ET
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
import json
import re

# 1. .env 로드
load_dotenv()

# 2. arXiv 검색 설정
BASE_URL = 'https://export.arxiv.org/api/query'
BASE_OFFSET = 0
MAX_RESULTS = 100
PROCESS_DAYS = 7  # 최근 N일 논문만 처리
PAPER_PATH = "papers/"

SEARCHES = [
    {'search_query': 'all:"prompt%20injection"+AND+cat:cs.*', 'start': BASE_OFFSET, 'max_results': MAX_RESULTS},
    {'search_query': 'all:"jailbreak"+AND+"llm"+AND+cat:cs.*', 'start': BASE_OFFSET, 'max_results': MAX_RESULTS},
    {'search_query': 'all:"attack"+AND+"llm"+AND+cat:cs.*', 'start': BASE_OFFSET, 'max_results': MAX_RESULTS},
    {'search_query': 'all:"vulnerability"+AND+"llm"+AND+cat:cs.*', 'start': BASE_OFFSET, 'max_results': MAX_RESULTS},
    {'search_query': 'all:"malware"+AND+"llm"+AND+cat:cs.*', 'start': BASE_OFFSET, 'max_results': MAX_RESULTS},
    {'search_query': 'all:"vulnerability"+AND+"mcp"+AND+cat:cs.*', 'start': BASE_OFFSET, 'max_results': MAX_RESULTS},
    {'search_query': 'all:"security"+AND+"llm"+AND+cat:cs.*', 'start': BASE_OFFSET, 'max_results': MAX_RESULTS},
    {'search_query': 'all:"security"+AND+"mcp"+AND+cat:cs.*', 'start': BASE_OFFSET, 'max_results': MAX_RESULTS},
    {'search_query': 'all:"security"+AND+"agentic%20ai"+AND+cat:cs.*', 'start': BASE_OFFSET, 'max_results': MAX_RESULTS},
    {'search_query': 'all:"Gen%20AI"+AND+"security"+AND+cat:cs.*', 'start': BASE_OFFSET, 'max_results': MAX_RESULTS},
    {'search_query': 'all:"SOC"+AND+"agentic%20ai"+AND+cat:cs.*', 'start': BASE_OFFSET, 'max_results': MAX_RESULTS},
    {'search_query': 'all:"SOC"+AND+"ai%20agent"+AND+cat:cs.*', 'start': BASE_OFFSET, 'max_results': MAX_RESULTS},
]

# 3. 환경 변수 로드 함수
def get_email_list():
    email_list_str = (os.environ.get("EMAIL_LIST") or "").strip()
    if not email_list_str:
        raise ValueError("EMAIL_LIST 환경 변수가 비어있습니다. .env 파일을 확인하세요.")
    recipients = [email.strip() for email in email_list_str.split(",") if email.strip()]
    if not recipients:
        raise ValueError("EMAIL_LIST에 유효한 이메일 주소가 없습니다.")
    print("EMAIL_LIST: ", os.environ.get("EMAIL_LIST")) # Delete
    return recipients

def get_sender_info():
    sender = os.environ.get("GOOG_APP_EMAIL", "").strip()
    password = os.environ.get("GOOG_APP_PASSKEY", "").strip()
    if not sender or not password:
        raise ValueError("GOOG_APP_EMAIL 또는 GOOG_APP_PASSKEY 환경 변수가 비어있습니다.")
    return sender, password

# 4. 이메일 발송 (HTML 지원)
def send_email(subject, body_html):
    sender, password = get_sender_info()
    recipients = get_email_list()
    msg = MIMEText(body_html, "html", "utf-8")  # HTML 형식으로 변경
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, recipients, msg.as_string())

# 5. MongoDB 연결
def get_mongo_collection():
    mongo_uri = os.environ.get("MONGO_URI", "").strip()
    mongo_db = os.environ.get("MONGO_DB", "").strip()
    mongo_col = os.environ.get("MONGO_COLLECTION", "").strip()
    if not mongo_uri or not mongo_db or not mongo_col:
        raise ValueError("MongoDB 환경 변수가 비어있습니다.")
    client = MongoClient(mongo_uri)
    return client[mongo_db][mongo_col]

# 6. arXiv API 검색
def search_arxiv(search_query, start, max_results):
    url = f"{BASE_URL}?search_query={search_query}&start={start}&max_results={max_results}"
    response = requests.get(url)
    if response.status_code != 200:
        raise RuntimeError(f"arXiv API 요청 실패: {response.status_code}")
    root = ET.fromstring(response.text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    papers = []
    for entry in root.findall("atom:entry", ns):
        published_date = datetime.strptime(entry.find("atom:published", ns).text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if published_date < datetime.now(timezone.utc) - timedelta(days=PROCESS_DAYS):
            continue
        paper = {
            "id": safe_text(entry.find("atom:id", ns)),
            "title": safe_text(entry.find("atom:title", ns)),
            "summary": safe_text(entry.find("atom:summary", ns)),
            "published": published_date,
            "link": entry.find("atom:link", ns).attrib.get("href", "")
        }
        papers.append(paper)
    return papers

def safe_text(element):
    return (element.text or "").strip() if element is not None else ""

# 7. MongoDB 저장 (중복 방지)
def save_papers_to_mongo(papers):
    col = get_mongo_collection()
    saved_count = 0
    for paper in papers:
        if not col.find_one({"id": paper["id"]}):
            paper["saved_at"] = datetime.now(timezone.utc)
            col.insert_one(paper)
            saved_count += 1
    return saved_count

# 8. Azure OpenAI 초기화
OAI = AzureOpenAI(
    api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
    api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT")
)

# 9. 논문 요약
def summarize_paper(paper):
    prompt = f"""
    다음 논문 초록을 기반으로, 의미상 중요한 내용을 3개의 Bullet Point로 요약해줘.
    - 반드시 한국어로 작성해
    - 각 Bullet Point는 줄을 구분해줘
    - "요약", "요지, "다음은 논문의 핵심 요약입니다." 등 불필요한 서두 문구는 포함하지 말아줘
    - 출력은 HTML <ul><li>...</li><ul> 형식으로 해줘

    제목: {paper['title']}
    초록: {paper['summary']}
    """
    response = OAI.chat.completions.create(
        model=os.environ.get("AZURE_OPENAI_DEPLOYMENT"),
        messages=[
            {"role": "system", "content": "당신은 전문 논문 요약가입니다."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

# 10. 중요도 평가 함수 추가
def rank_top_papers(papers_with_summaries, top_n=10):
    summaries_text = "\n\n".join(
        [f"{i+1}. 제목: {p['title']}\n요약: {p['summary_html_plain']}" for i, p in enumerate(papers_with_summaries)]
    )
    prompt = f"""
    다음 논문 요약 목록을 보고, 각 논문의 중요도를 1~10으로 평가해. 중요도는 기술 혁신성, 영향력, 실용성을 기준으로 합니다. 결과는 추가 설명, 코드 블록 등 없이 반드시 JSON만 출력해.
    
    #출력 예시:
    [
        {{"index": 1, "title": "논문 제목", "score": 9}},
        {{"index": 2, "title": "논문 제목", "score": 5}},
        ...
    ]

    논문 목록:
    {summaries_text}
    """
    response = OAI.chat.completions.create(
        model=os.environ.get("AZURE_OPENAI_DEPLOYMENT"),
        messages=[
            {"role": "system", "content": "당신은 논문 평가 전문가입니다."},
            {"role": "user", "content": prompt}
        ]
    )
    #scores = json.loads(response.choices[0].message.content)
    raw_content = getattr(response.choices[0].message, "content", "").strip()
    if not raw_content:
        raise ValueError("LLM 응답이 비어있습니다.")
    try:
        scores = json.loads(raw_content)
    except json.JSONDecodeError:
        print("JSON 파싱 실패: ", raw_content)
        raise
    scores_sorted = sorted(scores, key=lambda x: x["score"], reverse=True)
    return [papers_with_summaries[item["index"] - 1] for item in scores_sorted[:top_n]]

# 12. 메인 실행
if __name__ == "__main__":
    all_papers = []
    for search in SEARCHES:
        print(f"🔍 검색: {search['search_query']}")
        papers = search_arxiv(search["search_query"], search["start"], search["max_results"])
        if papers:
            saved_count = save_papers_to_mongo(papers)
            print(f"💾 MongoDB에 {saved_count}개 저장")
            all_papers.extend(papers)

    if not all_papers:
        print("📭 새로운 논문이 없습니다.")
    else:
        papers_with_summaries = []
        for paper in all_papers:
            summary = summarize_paper(paper)  # 이미 HTML bullet list
            papers_with_summaries.append({
                **paper,
                "summary_html": summary,  # HTML 그대로 사용
                "summary_html_plain": re.sub(r'<[^>]+>', '', summary)  # 태그 제거한 텍스트
            })
             
        unique_papers = []
        seen_pairs = set()

        for paper in papers_with_summaries:
            title = paper.get("title", "").strip().lower()
            content = paper.get("summary", "").strip().lower()

            key = (title, content)
            if title and content and key not in seen_pairs:
                seen_pairs.add(key)
                unique_papers.append(paper)

        top_papers = rank_top_papers(unique_papers, top_n=10)
        # HTML 시작
        email_body = """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; }
                .paper-card {
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    padding: 15px;
                    margin-bottom: 20px;
                    background-color: #f9f9f9;
                }
                .paper-title { font-size: 18px; font-weight: bold; color: #333; }
                .paper-meta { font-size: 14px; color: #666; margin-bottom: 10px; }
                .paper-summary { font-size: 15px; }
                a { color: #1a73e8; text-decoration: none; }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
        <h2>📄 최신 AI 보안 논문 요약</h2>
        """

        for paper in top_papers: #all_papers
            #summary = summarize_paper(paper)
            #summary_html = format_summary_html(summary)
            email_body += f"""
            <div class="paper-card">
                <div class="paper-title"><a href="{paper['link']}" target="_blank">{paper['title']}</a></div>
                <div class="paper-meta">발행일: {paper['published'].strftime('%Y-%m-%d')}</div>
                <div class="paper-summary">{paper['summary_html']}</div>
            </div>
            """

        email_body += """
        </body>
        </html>
        """

        send_email("[Weekly Security News] 최신 AI Security 논문", email_body + "<br> Powered by gpt-5")
        print("✅ 논문 요약 메일 발송 완료")
