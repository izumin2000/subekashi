from django_hosts import patterns, host

host_patterns = patterns(
    '',
    host(r'', 'top.urls', name='top'),
    host(r'subekashi', 'subekashi.urls', name='subekashi'),
    host(r'xia', 'xia.urls', name='xia'),
    host(r'iniadmc', 'iniadmc.urls', name='iniadmc'),
)