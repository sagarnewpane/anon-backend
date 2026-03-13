from .models import DeviceUser

class DeviceUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        device_id = request.headers.get('X-Device-ID')
        print(device_id)
        print(request)

        if device_id:
            user, created = DeviceUser.objects.get_or_create(device_id=device_id)
            
            request.device_user = user
        else:
            request.device_user = None

        return self.get_response(request)