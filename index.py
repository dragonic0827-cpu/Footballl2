"""Repository-root deployment entrypoint.

Vercel lists ``index.py`` as a conventional Python entrypoint.  Keeping this
adapter at the selected project root also makes a wrong ``src``/``tests`` root
immediately distinguishable from the supported deployment layout.
"""

from api.index import app, application

__all__ = ["app", "application"]
