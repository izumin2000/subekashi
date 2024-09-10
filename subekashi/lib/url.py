from subekashi.constants.view import *
import re


def isYouTubeLink(link):
    videoID = re.search(URL_PATTERN, link)
    return videoID is not None


def formatURL(link):
    videoID = re.search(URL_PATTERN, link)
    if isYouTubeLink(link):
        return "https://youtu.be/" + videoID.group(1)
    else:
        return link