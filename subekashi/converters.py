SQLITE_INT_MAX = 9223372036854775807
SQLITE_INT_MIN = -9223372036854775808


def parse_sqlite_id(value):
    """ASCIIの数字だけで、SQLiteの整数の範囲に収まる文字列を整数にする。それ以外はNoneを返す

    isdigit()は"²"等の上付き数字もTrueになりint()で変換できず、桁数が多すぎる文字列は
    int()がValueErrorになるため、ASCII・桁数を先に確かめる
    """
    if not (value.isascii() and value.isdigit()) or len(value) > len(str(SQLITE_INT_MAX)):
        return None
    number = int(value)
    return number if number <= SQLITE_INT_MAX else None


class SQLiteIntConverter:
    regex = '[0-9]+'

    def to_python(self, value):
        number = parse_sqlite_id(value)
        if number is None:
            raise ValueError
        return number

    def to_url(self, value):
        return str(value)
