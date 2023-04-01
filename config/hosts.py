from django_hosts import patterns, host

host_patterns = patterns(
    '',
    host(r'subekashi', 'subekashi.urls', name='subekashi'),
    host(r'orissa', 'orissa.urls', name='orissa'),
    host(r'iniadmc', 'iniadmc.urls', name='iniadmc'),
)