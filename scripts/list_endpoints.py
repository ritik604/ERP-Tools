import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'construction_erp.settings')
django.setup()

from django.urls import get_resolver, URLPattern, URLResolver

def get_urls(patterns, prefix=''):
    url_list = []
    for pattern in patterns:
        if isinstance(pattern, URLResolver):
            url_list.extend(get_urls(pattern.url_patterns, prefix + str(pattern.pattern)))
        elif isinstance(pattern, URLPattern):
            full_path = prefix + str(pattern.pattern)
            url_list.append((full_path, pattern.name, pattern.callback))
    return url_list

if __name__ == '__main__':
    resolver = get_resolver()
    urls = get_urls(resolver.url_patterns)
    print(f"Total endpoints found: {len(urls)}")
    for path, name, callback in urls:
        cb_name = getattr(callback, '__name__', str(callback))
        if hasattr(callback, 'view_class'):
            cb_name = callback.view_class.__name__
        print(f"/{path:50} | name: {str(name):30} | view: {cb_name}")
