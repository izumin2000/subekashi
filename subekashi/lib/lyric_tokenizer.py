from janome.tokenizer import Tokenizer
from subekashi.models import Word

_tokenizer = Tokenizer()

# SubeteJanomeNoSeidesu側のREPLACEABLE_HINSHISと合わせている。
# 一致していないと、外部リポジトリが計算した副詞・連体詞のWord候補が
# subekashi側で一切使われず無駄になる
REPLACEABLE_HINSHIS = ("名詞", "動詞", "形容詞", "副詞", "連体詞")


def _tokenize_text(text):
    # katsuyouの計算規約はSubeteJanomeNoSeidesu側のtokenizer_janome()と合わせている。
    # 一致していないと、Wordテーブルのkatsuyouと突き合わせても一致せず、
    # 候補が一切ヒットしなくなる
    tokens = []
    for tok in _tokenizer.tokenize(text):
        hinshi = tok.part_of_speech.split(",")[0]
        if hinshi in ("動詞", "形容詞"):
            katsuyou = tok.infl_form
        elif hinshi == "名詞":
            katsuyou = tok.part_of_speech
        else:
            katsuyou = ""
        tokens.append({"surface": tok.surface, "hinshi": hinshi, "katsuyou": katsuyou})
    return tokens


def tokenize_ai_instances(ai_queryset):
    """
    Aiインスタンス群の歌詞を単語ごとに分割する。
    Word候補が実在する（word, hinshi）の単語だけ is_replaceable=True になる
    （クリック可能な単語として表示するため）。N+1を避けるため一括で判定する。
    """
    ai_list = list(ai_queryset)
    tokenized_lines = [_tokenize_text(ai.lyrics) for ai in ai_list]

    pair_set = {
        (token["surface"], token["hinshi"])
        for tokens in tokenized_lines
        for token in tokens
        if token["hinshi"] in REPLACEABLE_HINSHIS
    }

    existing_pairs = set()
    if pair_set:
        words = {word for word, hinshi in pair_set}
        db_pairs = set(Word.objects.filter(word__in=words).values_list("word", "hinshi"))
        existing_pairs = db_pairs & pair_set

    result = []
    for ai, tokens in zip(ai_list, tokenized_lines):
        for index, token in enumerate(tokens):
            token["index"] = index
            token["is_replaceable"] = (token["surface"], token["hinshi"]) in existing_pairs
        result.append({"id": ai.id, "lyrics": ai.lyrics, "tokens": tokens})

    return result


def tokenize_lyrics_with_index(lyrics):
    """
    歌詞1件分を単語ごとに分割し、連番のindexを付与して返す。
    AiWordSwapView側で、クライアントが指定したtoken_indexに対応する単語を
    特定するために使う。
    """
    tokens = _tokenize_text(lyrics)
    for index, token in enumerate(tokens):
        token["index"] = index
    return tokens
