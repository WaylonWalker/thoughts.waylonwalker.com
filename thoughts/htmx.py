from functools import wraps

from fastapi import Request

from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    RedirectResponse,
    JSONResponse,
)

from thoughts.config import config


def htmx(template=None):
    def htmx(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            hx_request_header = request.headers.get("hx-request")
            user_agent = request.headers.get("user-agent", "").lower()
            print("hx_request_header", hx_request_header)
            print("user_agent", user_agent)

            if hx_request_header:
                val = await func(request, *args, **kwargs)
                if template is None:
                    _template = val.__class__.__name__.lower()
                else:
                    _template = template

                return config.templates.TemplateResponse(
                    f"{_template}_partial.html",
                    {"request": request, "config": config, **dict(val)},
                )
            elif "mozilla" in user_agent or "webkit" in user_agent:
                val = await func(request, *args, **kwargs)
                if template is None:
                    _template = val.__class__.__name__.lower()
                else:
                    _template = template
                return config.templates.TemplateResponse(
                    f"{_template}.html",
                    {"request": request, "config": config, **dict(val)},
                )
            return await func(request, *args, **kwargs)

        return wrapper

    return htmx
