from django import template


register = template.Library()

@register.filter
def filter_by_tag(song, tag):
    if tag == "joke":
        return song.filter(isjoke = True)
    if tag == "~joke":
        return song.filter(isjoke = False)
    
    return []
