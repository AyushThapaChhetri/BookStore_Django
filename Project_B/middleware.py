from django.http import HttpResponseForbidden
from django.shortcuts import redirect

# Define a mapping of URL prefixes to required permissions
# Each tuple contains a URL prefix and the permission codename required to access it
URL_PERMISSIONS = [
    ('/books/', 'books.can_view_books'),  # Permission needed for URLs starting with 'books/'
    ('/users/', 'users.can_view_users'),  # Permission needed for URLs starting with 'users/'
    # Add more mappings here as your project grows (e.g., 'books/create/' or 'users/profile/')
]
# EXEMPT_PATHS = [
#     '/',
#     '/login/',
#     '/signup/',
#     # '/admin/',
#     # '/media/',
#     # '/__reload__/',
# ]

EXEMPT_PATHS_EXACT = {'/', '/login/', '/signup/', '/reset_password/', '/reset_password_sent/', '/reset/<uuid>/<token>/',
                      '/reset_password_complete/', '/about/', '/activate/'}
EXEMPT_PATHS_PREFIX = {'/media/', '/static/', '/reset/', '/activate/', }


class PermissionMiddleware:
    """
        Middleware to enforce permission checks on URL requests.
        - Allows superadmins (is_superadmin=True) to access all URLs.
        - Redirects unauthenticated users to the login page.
        - Skips checks for admin, media, and debug reload URLs.
        - For other URLs, checks permissions; if none defined, allows authenticated users.
        """

    def __init__(self, get_response):
        """Initialize the middleware with the get_response callable."""
        self.get_response = get_response

    def __call__(self, request):
        """
                Process each request before it reaches the view.
                - Skips checks for specific paths (admin, media, reload).
                - Enforces authentication and permission rules.
                """
        path = request.path

        # Check if we should skip permission checks for this path
        if self.should_skip_checks(request.path):
            return self.get_response(request)

        # Redirect unauthenticated users to the login page with 'next' parameter
        if not request.user.is_authenticated:
            # if any(path.startswith(prefix) for prefix in EXEMPT_PATHS):
            #     return self.get_response(request)
            # Allow if it's exactly in the public list
            if path in EXEMPT_PATHS_EXACT:
                return self.get_response(request)

            # Allow if it starts with a public prefix (optional case)
            if any(path.startswith(prefix) for prefix in EXEMPT_PATHS_PREFIX):
                return self.get_response(request)

            return redirect('login_view')
        # return redirect(reverse('login_view') + '?next=' + request.path)

        # Determine the required permission for this URL
        required_permission = self.get_required_permission(request.path)

        # Allow superadmins to access any URL
        if request.user.is_superuser:
            return self.get_response(request)

        # If no permission is required, allow any authenticated user
        if required_permission is None:
            return self.get_response(request)

        # Check if the user has the required permission
        if request.user.has_perm(required_permission):
            return self.get_response(request)
        else:
            # Deny access with a 403 Forbidden response if permission is missing
            return HttpResponseForbidden("You don't have permission to access this page.")

    def should_skip_checks(self, path):
        """
        Check if permission checks should be skipped for this path.
        Returns True for admin, media, and debug reload URLs.
        """
        # List of URL prefixes where we skip custom permission checks
        skip_prefixes = [
            '/admin/',  # Admin site has its own permission system
            '/media/',  # Media files are typically public or handled by the server
            '/__reload__/',  # Debug reload URLs for development (django-browser-reload)
        ]
        for prefix in skip_prefixes:
            if path.startswith(prefix):
                return True
        return False

    def get_required_permission(self, path):
        """
        Find the required permission for the given path.
        Returns the permission codename if the path matches a prefix in URL_PERMISSIONS, else None.
        """
        for prefix, permission in URL_PERMISSIONS:
            if path.startswith(f"/{prefix}"):
                return permission
        return None  # No permission required if no match is found
