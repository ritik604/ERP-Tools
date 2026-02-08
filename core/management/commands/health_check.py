from django.core.management.base import BaseCommand
from django.urls import URLPattern, URLResolver, get_resolver
from django.test import Client
from django.contrib.auth import get_user_model
from django.conf import settings
import re

class Command(BaseCommand):
    help = 'Crawls all URLs in the project and checks their response status.'

    def handle(self, *args, **options):
        self.stdout.write("Starting health check...")
        
        # Create a test superuser for testing protected views
        User = get_user_model()
        username = 'healthcheck_admin'
        password = 'healthcheck_password'
        email = 'healthcheck@example.com'
        
        try:
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_superuser(username, email, password)
                user.role = 'ADMIN'
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Created temporary superuser '{username}'"))
            else:
                user = User.objects.get(username=username)
                if user.role != 'ADMIN':
                    user.role = 'ADMIN'
                    user.save()
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not create/get superuser: {e}. Proceeding as anonymous."))
            user = None

        # Add testserver to ALLOWED_HOSTS dynamically to avoid 400 errors
        if 'testserver' not in settings.ALLOWED_HOSTS:
             settings.ALLOWED_HOSTS += ['testserver']

        client = Client()
        if user:
            client.force_login(user)

        # Collect all URLs
        urls_to_test = []
        
        def extract_urls(patterns, prefix=''):
            for pattern in patterns:
                # Get the route string
                # pattern.pattern is usually RoutePattern or RegexPattern
                # RoutePattern has `_route`
                # RegexPattern has `_regex` (or regex.pattern)
                
                route = ''
                if hasattr(pattern.pattern, '_route'):
                    route = pattern.pattern._route
                elif hasattr(pattern.pattern, 'regex'):
                    route = pattern.pattern.regex.pattern
                else:
                    route = str(pattern.pattern)
                
                # Setup proper slash handling
                # prefix usually ends with slash if it's a path
                # route usually doesn't start with slash if inside include
                
                # Just robustly join
                full_route = prefix + route
                
                # Clean up regex artifacts (e.g. ^, $)
                clean_route = full_route.replace('^', '').replace('$', '')
                
                if isinstance(pattern, URLResolver):
                    # It's an include
                    extract_urls(pattern.url_patterns, clean_route)
                elif isinstance(pattern, URLPattern):
                    # It's a view
                    name = pattern.name or 'unnamed'
                    urls_to_test.append((clean_route, name))

        resolver = get_resolver()
        extract_urls(resolver.url_patterns)
        
        self.stdout.write(f"Found {len(urls_to_test)} URL patterns.")
        
        # Test URLs
        for url_pattern, name in urls_to_test:
            # Prepare mock URL
            # Replace common parameter patterns
            # Note: This is a best-effort approach. 
            # Real parameterized URLs need valid DB IDs.
            
            mock_url = url_pattern
            
            # Simple replacements for standard path converters
            replacements = [
                (r'<int:[^>]+>', '1'),
                (r'<str:[^>]+>', 'test-string'),
                (r'<slug:[^>]+>', 'test-slug'),
                (r'<uuid:[^>]+>', '00000000-0000-0000-0000-000000000000'),
                (r'<path:[^>]+>', 'test/path'),
                # Handle raw regex named groups (?P<name>...)
                (r'\(\?P<[^>]+>[^)]+\)', '1'), # overly aggressive but catches IDs
            ]
            
            for regex, repl in replacements:
                mock_url = re.sub(regex, repl, mock_url)
                
            # Remove any remaining regex chars that might break URL (like special chars)
            # This is tricky without breaking valid chars
            
            if not mock_url.startswith('/'):
                mock_url = '/' + mock_url

            # Skip media/static if not properly setup in test client
            if mock_url.startswith(settings.MEDIA_URL) or mock_url.startswith(settings.STATIC_URL):
                continue

            try:
                response = client.get(mock_url)
                status = response.status_code
                
                msg = f"[{status}] {name}: {mock_url}"
                if status == 200:
                    self.stdout.write(self.style.SUCCESS(msg))
                elif status in [301, 302]:
                    target = response.url if hasattr(response, 'url') else '?'
                    self.stdout.write(self.style.WARNING(f"{msg} -> {target}"))
                elif status == 404:
                    self.stdout.write(self.style.ERROR(msg))
                elif status >= 500:
                    self.stdout.write(self.style.ERROR(f"SERVER ERROR {msg}"))
                else:
                    self.stdout.write(msg)
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"EXCEPTION {name}: {mock_url} - {str(e)}"))
