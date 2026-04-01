from .device import is_mobile_request


def device_context(request):
    return {"is_mobile": is_mobile_request(request)}
