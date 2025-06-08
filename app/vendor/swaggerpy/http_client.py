# Simplified placeholder for app/vendor/swaggerpy/http_client.py
import logging
import requests # For a basic http client behavior
import json

log = logging.getLogger(__name__)

class SynchronousHttpClient(object):
    """
    A very simplified synchronous HTTP client, mimicking the one potentially
    used by the original swaggerpy or ari-py's version of it.
    The original swaggerpy.http_client.SynchronousHttpClient was a bit more complex
    and handled an eventlet event if running in an eventlet environment.
    """
    def __init__(self):
        self.session = requests.Session()
        self.auth = None
        log.info("Vendored SynchronousHttpClient initialized.")

    def set_basic_auth(self, host, username, password):
        # Note: requests.Session().auth takes a tuple (username, password)
        # and applies it to all requests. The host is not strictly needed here
        # unless we were managing multiple auths for multiple hosts.
        self.auth = (username, password)
        log.info(f"Basic auth set for vendored SynchronousHttpClient (host: {host} - not used by this simplified client).")

    def request(self, method, url, params=None, data=None, headers=None, timeout=10):
        """
        Makes an HTTP request.
        The original swaggerpy.http_client.HttpClient (base for SynchronousHttpClient)
        defined request to return (json_obj, http_response_meta_obj).
        This simplified version will try to return parsed JSON directly if successful,
        which was an issue noted for ari-py's promote() function.
        Let's try to return a (json_data, mock_response_object) tuple to be more
        compatible with what a more complete swagger client might provide, and what
        ari-py's promote() might have actually dealt with if swaggerpy was forked.
        """
        req_headers = {'Content-Type': 'application/json'}
        if headers:
            req_headers.update(headers)

        log.debug(f"Vendored SyncHttpClient: {method} {url} PARAMS: {params} DATA: {data} AUTH: {self.auth is not None}")
        try:
            response = self.session.request(
                method,
                url,
                params=params,
                data=data, # Assumes data is already a JSON string if it's for POST/PUT body
                headers=req_headers,
                auth=self.auth,
                timeout=timeout
            )
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

            json_data = None
            if response.content:
                try:
                    json_data = response.json()
                except ValueError: # json.JSONDecodeError is ValueError in older requests
                    log.warning(f"Response from {url} was not valid JSON: {response.text[:100]}")
                    json_data = response.text # Or handle as an error appropriately

            # Return tuple: (parsed_json_body, response_object_with_status_code)
            # This is to align with what the original swaggerpy might have returned to ari-py's client.
            return json_data, response

        except requests.exceptions.HTTPError as e:
            log.error(f"HTTP error during request by vendored SyncHttpClient to {url}: {e.response.status_code} {e.response.text}")
            # To allow promote() to potentially handle this, we might need to return a mock object
            # or ensure that the exception raised is what ari-py expects (e.g. AriException)
            # For now, re-raise.
            raise # Or convert to a custom exception if ari-py's promote expects it
        except Exception as e:
            log.error(f"Error during request by vendored SyncHttpClient to {url}: {e}")
            raise

    def get(self, url, params=None, headers=None, timeout=10):
        # Convenience method, uses self.request
        return self.request('GET', url, params=params, headers=headers, timeout=timeout)

    def close(self):
        self.session.close()
        log.info("Vendored SynchronousHttpClient session closed.")

# It's also possible that other specific methods like post, put, delete were called directly.
# For now, assuming 'request' and 'get' are the primary ones used by the vendored swaggerpy.client.Client.
# The vendored swaggerpy.Client uses self.http_client.get() and also passes self.http_client to SimplifiedResource,
# which then uses self.http_client.request().
# So, these two methods (get, request) are important.
