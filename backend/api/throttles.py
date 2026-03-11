from rest_framework.throttling import UserRateThrottle

class DeviceIDThrottle(UserRateThrottle):
    # This name links to the setting in settings.py
    scope = 'device_user'

    def get_cache_key(self, request, view):
        # We look for the user object attached by your middleware
        user = getattr(request, 'device_user', None)
        
        if user:
            # Use the unique device_id as the key for the throttle
            # This ensures two phones on one Wi-Fi are treated separately
            return self.cache_format % {
                'scope': self.scope,
                'ident': user.device_id
            }

        # If no device user (e.g. middleware failed), fallback to IP address
        return self.get_ident(request)