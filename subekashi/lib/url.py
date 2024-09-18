from subekashi.constants.constants import *
import re


URL_PATTERN = r'(?:\/|v=)([A-Za-z0-9_-]{11})(?:\?|&|$)'


def re_yt_link(link):
    match = re.search(URL_PATTERN, link)
    return match    


def is_yt_link(link):
    match = re_yt_link(link)
    return not match is None


def format_yt_url(link, id=False):
    match = re_yt_link(link)
    if match is None:
        return link
    videoID = match.group(1)
    if id:
        return videoID
    return "https://youtu.be/" + videoID