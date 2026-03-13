from ipware import get_client_ip

def get_user_ip(request):
    """
    Returns the real user IP and a boolean indicating if it's 
    a public/routable IP.
    """
    # client_ip is the actual IP address string
    # is_routable is True if it's a public IP, False if it's private/loopback
    client_ip, is_routable = get_client_ip(request)

    if client_ip is None:
        # Unable to get the client's IP address
        return "Unknown", False
    
    return client_ip, is_routable