import os
from config.settings import DEBUG


def get_static_path(path):
    if DEBUG:
        return os.path.join("subekashi", "static", "subekashi", path)
    else:
        return os.path.join("static", "subekashi", path)
    

def get_dynamic_path(path):
    return os.path.join("static", "constants", "dynamic", path)