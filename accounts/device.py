def is_mobile_request(request):
    user_agent = (request.META.get("HTTP_USER_AGENT") or "").lower()
    if not user_agent:
        return False
    mobile_hints = (
        "iphone",
        "ipad",
        "ipod",
        "android",
        "mobile",
        "blackberry",
        "windows phone",
        "opera mini",
    )
    return any(hint in user_agent for hint in mobile_hints)
