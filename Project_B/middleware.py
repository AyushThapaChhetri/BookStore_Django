from django.contrib import messages
from django.shortcuts import redirect

# Define a mapping of URL prefixes to required permissions
# Each tuple contains a URL prefix and the permission codename required to access it
URL_PERMISSIONS = [
    ('/books/', 'books.can_view_books'),  # Permission needed for URLs starting with 'books/'
    ('/users/', 'users.can_view_users'),  # Permission needed for URLs starting with 'users/'
    # Add more mappings here as your project grows (e.g., 'books/create/' or 'users/profile/')
]

# EXEMPT_PATHS_EXACT = {'/', '/login/', '/signup/', '/reset_password/', '/reset_password_sent/', '/reset/<uuid>/<token>/',
#                       '/reset_password_complete/', '/about/', '/activate/'}
# EXEMPT_PATHS_PREFIX = {'/media/', '/static/', '/reset/', '/activate/', }

# Only check permission under these prefixes
ADMIN_PREFIXES = [
    "/admin-panel/",  # all book admin URLs
    # later if you add: "/admin-users/", "/admin-orders/", etc.
]

LOGGED_IN_REDIRECT = [
    '/login/',
    '/signup/',
    '/reset_password/',
    '/reset_password_sent/',
    '/reset_password_complete/',
    '/activate/',
]
LOGGED_OUT_ONLY_PATHS = [
    '/login/',
    '/signup/',
    '/reset_password/',
    '/reset_password_sent/',
    '/reset_password_complete/',
]

EXEMPT_PATHS_EXACT = ['/', '/about/']
EXEMPT_PATHS_PREFIX = ['/media/', '/static/', '/__reload__/', '/reset/', '/activate/']


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

        # print("Path is these", path)
        # 1. Skip admin, media, reload
        if self.should_skip_checks(path):
            return self.get_response(request)

        # 2. Allow superusers
        if request.user.is_authenticated and request.user.is_superuser:
            return self.get_response(request)

        # Allow logged-out-only paths only for unauthenticated users
        if path in LOGGED_OUT_ONLY_PATHS:
            if request.user.is_authenticated:
                return redirect('home')  # logged-in users can't access these
            return self.get_response(request)

        # Allow fully exempt paths for everyone
        if path in EXEMPT_PATHS_EXACT or any(path.startswith(p) for p in EXEMPT_PATHS_PREFIX):
            return self.get_response(request)

        #  Require authentication for other pages

        if not request.user.is_authenticated:
            return redirect('login_view')

        # 6. Require extra permissions for admin-panel paths
        if any(path.startswith(p) for p in ADMIN_PREFIXES):
            # required_perm = self.get_required_permission(path)
            # if required_perm and not request.user.has_perm(required_perm):
            #     return HttpResponseForbidden("You don't have permission.")
            if not request.user.is_superuser:
                messages.error(request, "You are not allowed to access the admin panel.")
                return redirect('home')

                # return HttpResponseForbidden("You are not allowed to access the admin panel.")

        # 7. Check other permission-based URLs (optional)
        # required_perm = self.get_required_permission(path)
        # if required_perm and not request.user.has_perm(required_perm):
        #     return HttpResponseForbidden("You don't have permission.")

        # 8. Fallback
        return self.get_response(request)

    @staticmethod
    def should_skip_checks(path):
        return any(path.startswith(p) for p in ['/admin/', '/media/', '/__reload__/'])

    @staticmethod
    def get_required_permission(path):
        for prefix, perm in URL_PERMISSIONS:
            if path.startswith(prefix):
                return perm
        return None

        # Redirect unauthenticated users to the login page with 'next' parameter
        # if not request.user.is_authenticated:
        #
        #     # Allow if it's exactly in the public list
        #     if path in EXEMPT_PATHS_EXACT:
        #         return self.get_response(request)
        #
        #     # Allow if it starts with a public prefix (optional case)
        #     if any(path.startswith(prefix) for prefix in EXEMPT_PATHS_PREFIX):
        #         return self.get_response(request)
        #
        #     return redirect('login_view')
        # return redirect(reverse('login_view') + '?next=' + request.path)

        # Determine the required permission for this URL
        # required_permission = self.get_required_permission(request.path)
        #
        # # Allow superadmins to access any URL
        # if request.user.is_superuser:
        #     return self.get_response(request)
        #
        # # If no permission is required, allow any authenticated user
        # if required_permission is None:
        #     return self.get_response(request)
        #
        # # Check if the user has the required permission
        # if request.user.has_perm(required_permission):
        #     return self.get_response(request)
        # else:
        #     # Deny access with a 403 Forbidden response if permission is missing
        #     return HttpResponseForbidden("You don't have permission to access this page.")

    # def should_skip_checks(self, path):
    #     """
    #     Check if permission checks should be skipped for this path.
    #     Returns True for admin, media, and debug reload URLs.
    #     """
    #     # List of URL prefixes where we skip custom permission checks
    #     skip_prefixes = [
    #         '/admin/',  # Admin site has its own permission system
    #         '/media/',  # Media files are typically public or handled by the server
    #         '/__reload__/',  # Debug reload URLs for development (django-browser-reload)
    #     ]
    #     for prefix in skip_prefixes:
    #         if path.startswith(prefix):
    #             return True
    #     return False
    #
    # def get_required_permission(self, path):
    #     """
    #     Find the required permission for the given path.
    #     Returns the permission codename if the path matches a prefix in URL_PERMISSIONS, else None.
    #     """
    #     for prefix, permission in URL_PERMISSIONS:
    #         if path.startswith(f"/{prefix}"):
    #             return permission
    #     return None  # No permission required if no match is found
