from fastapi import Request
from thoughts.config import config


async def image_modal(request: Request, image_url: str):
    return config.templates.TemplateResponse(
        "image_modal.html",
        {"request": request, "image_url": image_url},
    )
