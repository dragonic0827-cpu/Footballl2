"""Conventional root Python entrypoint for Vercel and other WSGI hosts.

The actual HTTP adapter remains in :mod:`api.index`; this small module exists so
deployment platforms can discover the application before importing project code.
"""

from api.index import app, application

__all__ = ["app", "application"]
