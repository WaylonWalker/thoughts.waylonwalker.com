# SPDX-FileCopyrightText: 2023-present Waylon S. Walker <waylon@waylonwalker.com>
#
# SPDX-License-Identifier: MIT
import sys

from thoughts.config import config
from thoughts.optional import _optional_import_

uvicorn = _optional_import_("uvicorn", group="api")

if __name__ == "__main__":
    uvicorn.run(**config.api_server.dict())
