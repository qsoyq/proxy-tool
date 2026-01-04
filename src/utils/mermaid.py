import importlib
from functools import wraps
from typing import Callable

import fastapi
import fastapi.applications
import fastapi.openapi.docs
from fastapi.responses import HTMLResponse


def add_mermaid_support(func: Callable[..., HTMLResponse]):
    """在</head>标签前插入mermaid js

    https://mermaid-js.github.io/mermaid/#/n00b-gettingStarted?id=requirements-for-the-mermaid-api
    """
    mermaid_js = """
    <script type="module">
      import mermaid from 'https://unpkg.com/mermaid@9/dist/mermaid.esm.min.mjs';
      mermaid.initialize({ startOnLoad: true});
    </script>

    <style type="text/css">
        pre.mermaid {
            background-color: lightsteelblue !important;
        }
    </style>
    """

    @wraps(func)
    def decorator(*args, **kwargs) -> HTMLResponse:
        res = func(*args, **kwargs)
        if isinstance(res.body, bytes):
            content = res.body.decode(res.charset)
            index = content.find('</head>')
            if index != -1:
                content = content[:index] + mermaid_js + content[index:]

            return HTMLResponse(content)
        else:
            return res

    return decorator


def load_mermaid_plugin():
    fastapi.openapi.docs.get_swagger_ui_html = add_mermaid_support(fastapi.openapi.docs.get_swagger_ui_html)
    fastapi.openapi.docs.get_redoc_html = add_mermaid_support(fastapi.openapi.docs.get_redoc_html)
    importlib.reload(fastapi.applications)
