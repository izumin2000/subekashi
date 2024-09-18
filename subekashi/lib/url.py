from subekashi.constants.constants import *
import re


URL_PATTERN = r'(?:\/|v=)([A-Za-z0-9_-]{11})(?:\?|&|$)'


def is_yt_link(link):
    videoID = re.search(URL_PATTERN, link)
    return videoID is not None


def format_yt_url(link):
    videoID = re.search(URL_PATTERN, link)
    if is_yt_link(link):
        return "https://youtu.be/" + videoID.group(1)
    else:
        return link