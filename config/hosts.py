from config.settings import ROOT_URLCONF
from django_hosts import patterns, host

host_patterns = patterns(
    '',
    host(r'', ROOT_URLCONF, name='top'),
    host(r'subeana', 'subeana.urls', name='subeana'),
    host(r'xia', 'xia.urls', name='xia'),
    host(r'iniadmc', 'iniadmc.urls', name='iniadmc'),
)