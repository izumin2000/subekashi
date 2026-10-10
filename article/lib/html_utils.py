from html.parser import HTMLParser


# 正規表現では属性値に>を含むタグ（title="a>b"など）を正しく外せないため、HTMLParserで解析してaタグだけを除く
# 開始タグは元の文字列のまま出力し、終了タグと文字参照は組み立て直す（終了タグのタグ名は小文字になり、;の無い文字参照には;が付く）
# タイトルで使わない<!DOCTYPE>などの宣言は出力しない
class LinkRemover(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            self.parts.append(self.get_starttag_text())

    # 既定の実装はhandle_starttagとhandle_endtagを呼ぶため、<br/>などに終了タグが付かないよう上書きする
    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag != "a":
            self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        self.parts.append(data)

    def handle_entityref(self, name):
        self.parts.append(f"&{name};")

    def handle_charref(self, name):
        self.parts.append(f"&#{name};")

    def handle_comment(self, data):
        self.parts.append(f"<!--{data}-->")


def remove_links(html):
    remover = LinkRemover()
    remover.feed(html)
    remover.close()
    return "".join(remover.parts)
