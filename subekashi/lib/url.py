from subekashi.constants.constants import *
import re


URL_PATTERN = r'(?:\/|v=)([A-Za-z0-9_-]{11})(?:\?|&|$)'


def re_yt_url(url):
    match = re.search(URL_PATTERN, url)
    return match    


def is_yt_url(url):
    match = re_yt_url(url)
    return not match is None


def format_yt_url(url, id=False):
    match = re_yt_url(url)
    if match is None:
        return url
    videoID = match.group(1)
    if id:
        return videoID
    return "https://youtu.be/" + videoID

def clean_url(url):
    url = url.replace("https://www.google.com/url?q=", "")
    url = url.replace("www.", "")
    url = format_yt_url(url)
    return url