"""
PythonAnywhere (like most hosts) puts every request through its own
reverse proxy, so by default request.META["REMOTE_ADDR"] is always the
proxy's own internal address (observed in production as 10.0.4.129) -
never the real visitor's IP. Anything keyed by IP address downstream
(django-axes' login lockout, django-ratelimit on the forgot-password
endpoint, the reCAPTCHA remoteip check) was therefore treating every
visitor as the same single client: a few failed logins from anyone
locked out everyone else too, since axes' failure count was really
counting failures from "10.0.4.129" as a whole rather than per-visitor.

This middleware corrects REMOTE_ADDR from the X-Forwarded-For header
before anything else in the stack sees the request, so every IP-based
check downstream (axes, ratelimit, reCAPTCHA) automatically gets the
real per-visitor address without needing separate proxy configuration
in each of those libraries individually.

Trusts exactly one proxy hop (PythonAnywhere's own edge), matching the
real deployment topology - not configurable, since this project has
only ever run behind exactly that one proxy. Takes the right-most
entry in X-Forwarded-For (the address PythonAnywhere's own proxy itself
observed connecting to it), never the left-most one, because the
left-most entries are whatever the client itself sent and can be
freely spoofed - the right-most entry is the only one a single trusted
proxy hop guarantees is real.
"""


class RealIpMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded_for:
            real_ip = forwarded_for.split(",")[-1].strip()
            if real_ip:
                request.META["REMOTE_ADDR"] = real_ip
        return self.get_response(request)
