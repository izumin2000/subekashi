from markdown import markdown
from bs4 import BeautifulSoup
import re


# Markdownで特別な意味を持つ記号をバックスラッシュでエスケープする。
def escape_markdown(text):
    # Markdownの特殊文字一覧
    special_chars = [
        '\\', '`', '*', '_', '{', '}', '[', ']', '(', ')',
        '#', '+', '-', '.', '!', '|', '>', '<'
    ]

    # 正規表現で特殊文字を置換
    pattern = re.compile(r'([{}])'.format(re.escape(''.join(special_chars))))
    escaped = pattern.sub(r'\\\1', text)
    return escaped


# マークダウンをtableをdiv要素のwrapperで囲んだHTMLとしての文字列に変換する
def md2changes(md):
    html = markdown(md, extensions=['tables'])

    # BeautifulSoupでパース
    soup = BeautifulSoup(html, 'html.parser')

    # <table>を<div class="change_table_wrapper">で囲む
    for table in soup.find_all('table'):
        wrapper = soup.new_tag('div', **{'class': 'change_table_wrapper'})
        table.replace_with(wrapper)
        wrapper.append(table)

    # 結果のHTML
    wrapped_html = str(soup)
    return wrapped_html