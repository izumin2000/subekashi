class SQLiteIntConverter:
    regex = '[0-9]+'

    def to_python(self, value):
        SQLITE_INT_MAX = 9223372036854775807
        SQLITE_INT_MIN = -9223372036854775808
        val = int(value)
        if not (SQLITE_INT_MIN <= val <= SQLITE_INT_MAX):
            raise ValueError
        return val

    def to_url(self, value):
        return str(value)