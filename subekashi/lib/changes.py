from markdown import markdown
from bs4 import BeautifulSoup


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