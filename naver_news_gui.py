"""네이버 뉴스 크롤러 GUI (PyQt6).

설치: pip install PyQt6 requests beautifulsoup4 openpyxl
실행: python naver_news_gui.py
"""
import sys
import time
from urllib.parse import quote

import requests
from PyQt6.QtCore import Qt, QThread, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QPushButton, QSplitter, QTextEdit, QVBoxLayout, QWidget,
)

from naver_news_crawler import get_article_body, get_article_list, save_to_excel

SEARCH_URL = "https://search.naver.com/search.naver?where=nexearch&ie=utf8&query={}"


class Worker(QThread):
    """네트워크 작업을 UI 스레드 밖에서 실행한다."""
    done = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, func, *args):
        super().__init__()
        self.func, self.args = func, args

    def run(self):
        try:
            self.done.emit(self.func(*self.args))
        except (requests.RequestException, ValueError) as e:
            self.failed.emit(str(e))


class ExportWorker(QThread):
    """모든 기사 본문을 수집해 엑셀로 저장한다."""
    progress = pyqtSignal(int, int)
    done = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, articles, path):
        super().__init__()
        self.articles, self.path = articles, path

    def run(self):
        rows = []
        total = len(self.articles)
        for i, (title, link) in enumerate(self.articles, 1):
            self.progress.emit(i, total)
            try:
                body = get_article_body(link)
            except requests.RequestException:
                body = ""  # 실패한 기사도 제목/링크는 저장한다
            rows.append((title, link, body))
            time.sleep(0.5)
        try:
            save_to_excel(rows, self.path)
        except OSError as e:  # 파일이 엑셀에서 열려 있는 경우 등
            self.failed.emit(str(e))
            return
        self.done.emit(self.path)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("네이버 뉴스 크롤러")
        self.resize(1000, 650)
        self.worker = None
        self.exporter = None

        self.query = QLineEdit("반도체")
        self.query.setPlaceholderText("검색어 입력")
        self.query.returnPressed.connect(self.search)
        self.search_btn = QPushButton("검색")
        self.search_btn.clicked.connect(self.search)

        self.list = QListWidget()
        self.list.currentItemChanged.connect(self.load_body)
        self.title = QLabel("기사를 선택하세요")
        self.title.setWordWrap(True)
        self.title.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.body = QTextEdit()
        self.body.setReadOnly(True)
        self.open_btn = QPushButton("브라우저에서 열기")
        self.open_btn.setEnabled(False)
        self.open_btn.clicked.connect(self.open_in_browser)

        self.excel_btn = QPushButton("엑셀로 저장")
        self.excel_btn.setEnabled(False)
        self.excel_btn.clicked.connect(self.export_excel)

        top = QHBoxLayout()
        top.addWidget(QLabel("검색어:"))
        top.addWidget(self.query, 1)
        top.addWidget(self.search_btn)
        top.addWidget(self.excel_btn)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.addWidget(self.title)
        rl.addWidget(self.body, 1)
        rl.addWidget(self.open_btn)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self.list)
        split.addWidget(right)
        split.setSizes([380, 620])

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addLayout(top)
        layout.addWidget(split, 1)
        self.setCentralWidget(central)
        self.statusBar().showMessage("준비됨")

    def run_worker(self, func, *args, on_done):
        # 진행 중인 작업이 있으면 결과를 버리고 새 작업을 시작한다.
        if self.worker is not None:
            self.worker.done.disconnect()
            self.worker.failed.disconnect()
        self.worker = Worker(func, *args)
        self.worker.done.connect(on_done)
        self.worker.failed.connect(self.on_error)
        self.worker.start()

    def search(self):
        q = self.query.text().strip()
        if not q:
            return
        self.search_btn.setEnabled(False)
        self.statusBar().showMessage("검색 중...")
        self.run_worker(get_article_list, SEARCH_URL.format(quote(q)), on_done=self.show_list)

    def show_list(self, articles):
        self.search_btn.setEnabled(True)
        self.list.clear()
        self.body.clear()
        self.title.setText("기사를 선택하세요")
        self.open_btn.setEnabled(False)
        for title, link in articles:
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, link)
            self.list.addItem(item)
        self.excel_btn.setEnabled(bool(articles))
        self.statusBar().showMessage(f"기사 {len(articles)}건")

    def load_body(self, item):
        if item is None:
            return
        self.title.setText(item.text())
        self.body.setPlainText("본문 불러오는 중...")
        self.open_btn.setEnabled(True)
        link = item.data(Qt.ItemDataRole.UserRole)
        self.run_worker(get_article_body, link, on_done=self.show_body)

    def show_body(self, text):
        self.body.setPlainText(text or "(본문을 가져오지 못했습니다. 브라우저에서 열어 보세요.)")
        self.statusBar().showMessage("완료")

    def on_error(self, msg):
        self.search_btn.setEnabled(True)
        self.body.setPlainText(f"오류: {msg}")
        self.statusBar().showMessage("오류 발생")

    def export_excel(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "엑셀로 저장", f"{self.query.text().strip()}_뉴스.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        articles = [
            (self.list.item(i).text(), self.list.item(i).data(Qt.ItemDataRole.UserRole))
            for i in range(self.list.count())
        ]
        self.excel_btn.setEnabled(False)
        self.exporter = ExportWorker(articles, path)
        self.exporter.progress.connect(
            lambda i, n: self.statusBar().showMessage(f"본문 수집 중... {i}/{n}"))
        self.exporter.done.connect(self.export_done)
        self.exporter.failed.connect(self.export_failed)
        self.exporter.start()

    def export_done(self, path):
        self.excel_btn.setEnabled(True)
        self.statusBar().showMessage(f"저장 완료: {path}")

    def export_failed(self, msg):
        self.excel_btn.setEnabled(True)
        self.statusBar().showMessage(f"저장 실패: {msg}")

    def open_in_browser(self):
        item = self.list.currentItem()
        if item:
            QDesktopServices.openUrl(QUrl(item.data(Qt.ItemDataRole.UserRole)))


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
