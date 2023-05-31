from django_hosts import patterns, host

host_patterns = patterns(
    '',
    host(r'subekashi', 'subekashi.urls', name='subekashi'),
    host(r'recruit', 'recruit.urls', name='recruit'),
)