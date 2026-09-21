"""네이버 검색 결과(반도체)에서 뉴스 기사 제목/링크를 수집하고, 각 기사 본문을 크롤링한다.

설치: pip install requests beautifulsoup4 openpyxl
실행: python naver_news_crawler.py
"""
import time

import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Font

SEARCH_URL = (
    "https://search.naver.com/search.naver"
    "?where=nexearch&sm=top_hty&fbm=0&ie=utf8&query=%EB%B0%98%EB%8F%84%EC%B2%B4&ackey=fx3rpu4u"
)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
}


def get_soup(url):
    res = requests.get(url, headers=HEADERS, timeout=10)
    res.raise_for_status()
    return BeautifulSoup(res.text, "html.parser")


def get_article_list(url=SEARCH_URL):
    """검색 결과 페이지에서 (제목, 링크) 목록을 추출한다."""
    soup = get_soup(url)
    articles, seen = [], set()

    # 1순위: 뉴스 제목 링크(구 마크업 news_tit / 신 마크업 data-heatmap-target)
    anchors = soup.select("a.news_tit, a[data-heatmap-target='.tit']")
    # 2순위: 마크업이 바뀐 경우 네이버 뉴스 링크 전체에서 제목처럼 보이는 것만
    if not anchors:
        anchors = [
            a for a in soup.select("a[href]")
            if "news.naver.com" in a["href"] and len(a.get_text(strip=True)) > 10
        ]

    for a in anchors:
        title = a.get_text(strip=True)
        link = a["href"]
        if title and link not in seen:
            seen.add(link)
            articles.append((title, link))
    return articles


def get_article_body(url):
    """기사 본문 텍스트를 반환한다. 네이버 뉴스(n.news.naver.com) 형식을 우선 지원."""
    soup = get_soup(url)
    body = soup.select_one("#dic_area, #newsct_article, #articleBodyContents, article")
    if body is None:
        # 언론사 자체 사이트 등 알 수 없는 구조: <p> 텍스트를 이어 붙인다.
        return "\n".join(p.get_text(strip=True) for p in soup.select("p") if p.get_text(strip=True))
    for tag in body.select("script, style, .img_desc, .end_photo_org"):
        tag.decompose()
    return body.get_text("\n", strip=True)


def save_to_excel(rows, path):
    """rows: (제목, 링크, 본문) 목록을 엑셀 파일로 저장한다."""
    wb = Workbook()
    ws = wb.active
    ws.title = "뉴스"
    ws.append(["번호", "제목", "링크", "본문"])
    for cell in ws[1]:
        cell.font = Font(bold=True)

    def clean(text):
        # 엑셀이 허용하지 않는 제어문자 제거, 셀 최대 길이(32767자) 제한
        return ILLEGAL_CHARACTERS_RE.sub("", text)[:32000]

    for i, (title, link, body) in enumerate(rows, 1):
        ws.append([i, clean(title), link, clean(body)])
    ws.column_dimensions["B"].width = 60
    ws.column_dimensions["C"].width = 50
    ws.column_dimensions["D"].width = 100
    ws.freeze_panes = "A2"
    wb.save(path)


def main():
    articles = get_article_list()
    print(f"기사 {len(articles)}건 발견\n")

    for i, (title, link) in enumerate(articles, 1):
        print(f"[{i}] {title}\n    {link}")
        try:
            body = get_article_body(link)
            print(f"    본문: {body[:200].replace(chr(10), ' ')}...\n")
        except requests.RequestException as e:
            print(f"    본문 수집 실패: {e}\n")
        time.sleep(1)  # 서버 부담을 줄이기 위한 지연


if __name__ == "__main__":
    main()
