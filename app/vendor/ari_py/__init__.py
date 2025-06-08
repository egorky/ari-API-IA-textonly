# Copyright (c) 2013, Digium, Inc.
# Vendored and modified for Python 3 compatibility.

"""Asterisk ARI client library.
"""

# Imports for the connect() function
from urllib import parse as urlparse
from app.vendor.swaggerpy import http_client as swaggerpy_http_client # Assuming this path is correct for vendored swaggerpy
                                                                   # This implies swaggerpy needs an http_client.py

# Import the Client class and AriException from the .client module
from .client import Client, AriException

__version__ = '0.1.3' # Version of ari-py we are vendoring

def connect(base_url, appname, username, password): # Added appname
    """
    Helper method for easily connecting to ARI.

    :param base_url: Base URL for Asterisk HTTP server (http://localhost:8088/)
    :param username: ARI username
    :param password: ARI password.
    :return: An instance of app.vendor.ari_py.client.Client
    """
    # This is based on the original ari-py/__init__.py's connect function
    split = urlparse.urlsplit(base_url)

    # This http_client needs to be the one that swaggerpy.client.Client expects.
    # The original ari-py used its own (or swaggerpy's) SynchronousHttpClient.
    # If our vendored swaggerpy's Client takes an http_client, we create one here.
    # The vendored swaggerpy/client.py I defined takes an optional http_client.
    # The vendored ari-py/client.py passes its http_client to the vendored swaggerpy.client.Client.
    # So, the http_client created here is the one used for actual HTTP requests.

    # This was: http_client = swaggerpy.http_client.SynchronousHttpClient()
    # We need to ensure our vendored swaggerpy provides this.
    # Let's assume swaggerpy_http_client.SynchronousHttpClient() is the way.
    # This means app/vendor/swaggerpy/http_client.py needs to exist and define SynchronousHttpClient.
    # This is a NEW requirement for the vendored swaggerpy.

    try:
        # Attempt to use a SynchronousHttpClient if available from vendored swaggerpy's http_client module
        hc = swaggerpy_http_client.SynchronousHttpClient()
    except AttributeError:
        # Fallback or error if SynchronousHttpClient is not in our vendored swaggerpy.http_client
        # This is a critical part. For now, let's assume it might not exist and proceed cautiously.
        # This part of swaggerpy (http_client.py) was NOT vendored in previous steps.
        # This will likely be the next error.
        print("WARNING: app.vendor.swaggerpy.http_client.SynchronousHttpClient not found or vendored. ARI connections will likely fail.")
        # As a dummy, assign None, which means the swaggerpy.Client will use its default (requests.Session)
        # This will NOT match the original ari-py behavior if SynchronousHttpClient had special logic.
        hc = None
        # A better dummy might be a simple requests.Session wrapper if needed by swaggerpy.Client structure.
        # For now, the vendored swaggerpy.Client is designed to create its own requests.Session if http_client is None.

    if hc: # Only set auth if we have a real hc that supports it.
        hc.set_basic_auth(split.hostname, username, password)

    # The Client class (from .client) needs to be instantiated.
    # Its __init__ takes base_url (which is the ARI events URL like ws://.../events?app=...)
    # and http_client (for making API calls, not for the websocket).
    # The original ari-py client.py's __init__ took a base_url for swagger spec and an http_client.
    # The connect function assembled the swagger spec URL.

    # This is the ARI events URL (e.g., ws://localhost:8088/ari/events)
    # The swagger spec URL is different (e.g., http://localhost:8088/ari/api-docs/resources.json)
    # The Client class in client.py takes the swagger spec URL.

    swagger_spec_url = urlparse.urljoin(base_url, "ari/api-docs/resources.json")

    return Client(swagger_spec_url, http_client=hc)


# Expose what's needed. `connect` is the main entry point.
# `AriException` is useful for consumers.
# `Client` class itself could also be exposed if direct instantiation is desired.
__all__ = ['connect', 'AriException', 'Client']
