from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor
import xml.etree.ElementTree as etree


# マークダウンの画像を横スクロールできる枠（span.article-image）で囲む
# HTMLで直接書かれた画像（Googleドキュメントから書き出した記事など）は独自のレイアウトが崩れないよう対象外にする
class ArticleImageTreeprocessor(Treeprocessor):
    def run(self, root):
        images = [(parent, index) for parent in root.iter() for index, child in enumerate(parent) if child.tag == "img"]
        for parent, index in images:
            image = parent[index]
            wrapper = etree.Element("span", {"class": "article-image"})
            wrapper.tail, image.tail = image.tail, None
            wrapper.append(image)
            parent[index] = wrapper


class ArticleImageExtension(Extension):
    def extendMarkdown(self, md):
        # 画像のimg要素を生成するinline（優先度20）の後に実行する
        md.treeprocessors.register(ArticleImageTreeprocessor(md), "article_image", 15)


# タイトルは見出しやリンクの中に表示するため、1つの段落だけのときはp要素で囲まない
# （p要素のフォントサイズが適用されて記事ページの見出しが小さくなるのを防ぐ）
class UnwrapParagraphTreeprocessor(Treeprocessor):
    def run(self, root):
        if len(root) != 1 or root[0].tag != "p":
            return
        paragraph = root[0]
        children = list(paragraph)
        root.remove(paragraph)
        root.text = paragraph.text
        root.extend(children)


class UnwrapParagraphExtension(Extension):
    def extendMarkdown(self, md):
        # 太字やリンクの要素を生成するinline（優先度20）の後に実行する
        md.treeprocessors.register(UnwrapParagraphTreeprocessor(md), "unwrap_paragraph", 15)
