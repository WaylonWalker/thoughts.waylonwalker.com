
from functools import wraps
def htmx(func, templates):
    print('here')
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):

        hx_request_header = request.headers.get("hx-request")
        user_agent = request.headers.get("user-agent", "").lower()
        print('hx_request_header', hx_request_header)
        print('user_agent', user_agent)

        if hx_request_header:
            val = await func(request, *args, **kwargs)

            return templates.TemplateResponse(
            f'{val.__class__.__name__.lower()}_partial.html',
            {
                "request": request,
                "config": config,
                "md": md,
                **val.__dict__
            },
        )
        elif "mozilla" in user_agent or "webkit" in user_agent:
            val = await func(request, *args, **kwargs)
            return templates.TemplateResponse(
            f'{val.__class__.__name__.lower()}.html',
            {
                "request": request,
                "config": config,
                "md": md,
                **val.__dict__
            },
        )
        return await func(request, *args, **kwargs)
    return wrapper
