from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape, Undefined

class SilentUndefined(Undefined):
    def _fail_with_undefined_error(self, *args, **kwargs):
        return ''

env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(),
    undefined=SilentUndefined,
)



templates = Path().glob("templates/*.html")
tailwind_content_dir = Path(".tailwind")
tailwind_content_dir.mkdir(parents=True, exist_ok=True)

from thoughts.models.post import Posts
from thoughts.config import config

for template in templates:
    html = env.get_template(template.name).render(posts=Posts(__root__=[]), page=1, config=config)
    tailwind_content_dir.joinpath(template.name).write_text(html)


