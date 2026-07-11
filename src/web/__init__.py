"""
web/ -- HTTP route layer
"""

from . import _shared
from . import auth
from . import tunnel
from . import oauth
from . import dashboard
from . import system
from . import meta
from . import search
from . import plans
from . import letters
from . import hooks
from . import buckets
from . import import_api
from . import github
from . import embedding
from . import ollama_local
from . import config_api
from . import v3_debug
from . import xhs


_WEB_MODULES = (
    ("web.auth", auth.register),
    ("web.tunnel", tunnel.register),
    ("web.oauth", oauth.register),
    ("web.dashboard", dashboard.register),
    ("web.system", system.register),
    ("web.meta", meta.register),
    ("web.search", search.register),
    ("web.plans", plans.register),
    ("web.letters", letters.register),
    ("web.hooks", hooks.register),
    ("web.buckets", buckets.register),
    ("web.import_api", import_api.register),
    ("web.github", github.register),
    ("web.embedding", embedding.register),
    ("web.ollama_local", ollama_local.register),
    ("web.config_api", config_api.register),
    ("web.v3_debug", v3_debug.register),
    ("web.xhs", xhs.register)
)


def register_all(mcp) -> None:
    """register all web route modules"""
    def _register():
        for _name, register in _WEB_MODULES:
            register(mcp)

    return _shared.run_v3_web_operation(
        "register_all",
        {"modules": [name for name, _register_fn in _WEB_MODULES]},
        _register,
        module="web.*",
    )
