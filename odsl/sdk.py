"""Client for the OpenDataDSL (ODSL) HTTP API.

This module exposes the :class:`ODSL` class, which is the main entry point
for the SDK. Typical usage is to construct an ``ODSL()`` instance, call one
of the ``login*`` methods to authenticate, and then use ``get``, ``list``,
``function``, or ``update`` to interact with the API::

    from odsl import sdk

    odsl = sdk.ODSL()
    odsl.loginWithAPIKey(userid, apikey)
    obj = odsl.get('object', 'public', '#ECB')
"""

import requests
from msal import PublicClientApplication, ConfidentialClientApplication
import json
from odsl import cache
from urllib.parse import quote
import base64

class ODSL:
    """Client for the ODSL API.

    An ``ODSL`` instance holds the target environment (``url``) and the
    current credentials, and provides methods to authenticate and then
    read/write data through the API.

    Before calling any of ``get``, ``function``, ``list``, ``headers``, or
    ``update``, you must authenticate by calling one of ``login``,
    ``loginWithSecret``, ``loginWithAPIKey``, or ``loginWithToken``. Each of
    those methods sets ``self.credentials`` to the HTTP ``Authorization``
    header to send with subsequent requests.
    """

    url = 'https://api.opendatadsl.com/api/'
    token = None
    credentials = None
    cache = cache.TokenCacheAspect()
    app = PublicClientApplication(client_id='d3742f5f-3d4d-4565-a80a-ebdefaab8d08', authority="https://login.microsoft.com/common", token_cache=cache.getCache())

    def _checkError(self, r):
        """Print the server's error detail if a response wasn't successful.

        The ODSL API returns an ``x-odsl-error`` response header with a
        human-readable explanation whenever a request fails, which is
        easy to miss since the failure response body (``r.text``) alone
        often isn't very informative (e.g. a plain "Bad Request"). Every
        request-making method below runs its response through this before
        returning, so a failure prints something like::

            ODSL error 400: The event property must be in the format OBJECTID:EVENTID

        to help explain *why* a call failed, without changing what that
        method returns -- it's still up to the caller to check the
        response the way each method already documents.

        Args:
            r: The ``requests`` ``Response`` to check.

        Returns:
            ``r``, unchanged, so this can wrap a request call inline.
        """
        if not str(r.status_code).startswith('2'):
            error = r.headers.get('x-odsl-error')
            if error:
                print("ODSL error " + str(r.status_code) + ": " + error)
            else:
                print("ODSL error " + str(r.status_code) + " (no x-odsl-error header in the response)")
        return r

    def setStage(self, stage):
        """Point this client at a different ODSL environment.

        Args:
            stage: One of ``'dev'``, ``'local'``, or ``'prod'``. Any other
                value is silently ignored and ``self.url`` is left
                unchanged. Defaults to the production API if never called.
        """
        if stage == 'dev':
            self.url = 'https://odsl-dev.azurewebsites.net/api/'
        if stage == 'local':
            self.url = 'http://localhost:7071/api/'
        if stage == 'prod':
            self.url = 'https://api.opendatadsl.com/api/'

    def get(self, service, source, id, params=None):
        """Retrieve a single record by id.

        Args:
            service: The ODSL service to query, e.g. ``'object'``,
                ``'data'``, or ``'process'``.
            source: The data source/scope to look in, typically
                ``'public'`` or ``'private'``. Pass ``None`` to query the
                service without a source segment in the URL (used for
                services such as ``'process'``/``'process-task'``).
            id: The id of the record to retrieve, e.g. ``'#ECB'`` or
                ``'AAA.PYTHON'``. Will be URL-quoted automatically.
            params: Optional dict of extra query string parameters, e.g.
                ``{'_range': 'from(2024-07-01)'}``.

        Returns:
            The decoded JSON response (dict/list) on success (HTTP 200),
            the raw response text (str) if the request did not succeed
            (also printing the server's ``x-odsl-error`` detail, if any --
            see `_checkError`), or ``None`` if this client has not been
            logged in.
        """
        if self.credentials == None:
            print("Not logged in: call login() first")
            return
        headers = self.credentials
        eid = quote(id)
        u = self.url + service
        if source == None:
            u = self.url + service + "/v1/" + eid
        else:
            u = self.url + service + "/v1/" + source + "/" + eid
        r = self._checkError(requests.get(u, headers=headers, params=params))
        if r.status_code == 200:
            return r.json()
        return r.text

    def function(self, service, name, id=None, params=None):
        """Invoke a named server-side function on a service.

        Args:
            service: The ODSL service that exposes the function, e.g.
                ``'calendar'``.
            name: The function name, e.g. ``'holidays'``.
            id: Optional id to scope the function call to, e.g.
                ``'#HENG'``. If it starts with ``'#'`` it is treated as a
                public id, otherwise as a private id. When omitted, the
                function is called without an id segment in the URL.
            params: Optional dict of extra query string parameters to pass
                as function arguments. ``'_function'`` is added/overwritten
                automatically with ``name``. Note: if a dict is passed in,
                it is mutated in place.

        Returns:
            The decoded JSON response (dict/list) on success (HTTP 200),
            the raw response text (str) if the request did not succeed
            (also printing the server's ``x-odsl-error`` detail, if any --
            see `_checkError`), or ``None`` if this client has not been
            logged in.
        """
        if self.credentials == None:
            print("Not logged in: call login() first")
            return
        headers = self.credentials
        if params == None:
            params = {'_function':name}
        else:
            params['_function'] = name
        url = self.url + service + "/v1"
        if id != None:
            source = 'private'
            if id.startswith('#'):
                source = 'public'
            eid = quote(id)
            url = url + "/" + source + "/" + eid
            print(url)
        r = self._checkError(requests.get(url, headers=headers, params=params))
        if r.status_code == 200:
            return r.json()
        return r.text

    def list(self, service, source='private', params=None):
        """List/search records in a service.

        Args:
            service: The ODSL service to query, e.g. ``'object'``,
                ``'data'``, or ``'event'``.
            source: The data source/scope to search in, typically
                ``'public'``, ``'private'``, or ``'all'``. Defaults to
                ``'private'``.
            params: Optional dict of extra query string parameters, e.g.
                ``{'_filter': ..., '_sort': ..., '_limit': ..., '_skip':
                ..., '_aggregate': ..., '_project': ...}``.

        Returns:
            The decoded JSON response (typically a list of records) on
            success (HTTP 200), the raw response text (str) if the request
            did not succeed (also printing the server's ``x-odsl-error``
            detail, if any -- see `_checkError`), or ``None`` if this
            client has not been logged in.
        """
        if self.credentials == None:
            print("Not logged in: call login() first")
            return
        headers = self.credentials.copy()
        headers['Accept-Encoding'] = 'gzip'
        r = self._checkError(requests.get(self.url + service + "/v1/" + source, headers=headers, params=params))
        if r.status_code == 200:
            return r.json()
        return r.text

    def headers(self, service, source='private', params=None):
        """Fetch only the HTTP response headers for a list query.

        Useful for cheaply checking result metadata (e.g. total counts)
        without paying for the full response body. Internally this forces
        ``_limit`` to ``1`` on the request.

        Args:
            service: The ODSL service to query, e.g. ``'object'`` or
                ``'event'``.
            source: The data source/scope to search in. Defaults to
                ``'private'``.
            params: Optional dict of extra query string parameters. Note:
                if a dict is passed in, it is mutated in place (its
                ``'_limit'`` key is overwritten with ``1``).

        Returns:
            The response headers (a ``requests`` headers mapping) on
            success (HTTP 200), the raw response text (str) if the request
            did not succeed (also printing the server's ``x-odsl-error``
            detail, if any -- see `_checkError`), or ``None`` if this
            client has not been logged in.
        """
        if self.credentials == None:
            print("Not logged in: call login() first")
            return
        headers = self.credentials
        if params == None:
            params = {}
        params["_limit"] = 1
        r = self._checkError(requests.get(self.url + service + "/v1/" + source, headers=headers, params=params))
        if r.status_code == 200:
            return r.headers
        return r.text

    def update(self, service, source, var, params=None):
        """Create or update a record.

        Args:
            service: The ODSL service to write to, e.g. ``'object'``.
            source: The data source/scope to write to, typically
                ``'private'``. Not included in the request URL directly,
                but kept for symmetry with the read methods.
            var: A JSON-serialisable dict representing the record to
                write, e.g. ``{'_id': 'AAA.PYTHON', 'name': 'Example'}``.
            params: Optional dict of extra query string parameters.

        Returns:
            ``None``. The HTTP status code of the response is printed for
            diagnostic purposes; this method does not return the response
            body. Prints "Not logged in: call login() first" instead of
            making a request if this client has not been logged in. On a
            non-2xx response, also prints the server's ``x-odsl-error``
            detail (see `_checkError`) -- e.g. a malformed body often
            fails with a 400 whose ``r.text``/status code alone don't say
            why, but the error header usually does.
        """
        if self.credentials == None:
            print("Not logged in: call login() first")
            return
        headers = self.credentials
        body = json.JSONEncoder().encode(o=var)
        r = self._checkError(requests.post(self.url + service, headers=headers, data=body, params=params))
        print(r.status_code)

    def login(self):
        """Authenticate interactively via Microsoft identity platform (MSAL).

        Uses a cached account/token if one is available (via
        ``TokenCacheAspect``), silently refreshing it if possible;
        otherwise triggers an interactive login prompt. On success, sets
        ``self.token`` and ``self.credentials`` (a Bearer ``Authorization``
        header). On failure, prints the error description returned by
        MSAL and leaves ``self.credentials`` unset.
        """
        accounts = self.app.get_accounts()
        s = ["api://opendatadsl/api_user"]
        if accounts:
            self.token = self.app.acquire_token_silent(scopes=s, account=accounts[0])
        else:
            self.token = self.app.acquire_token_interactive(scopes=s)
        if "access_token" in self.token:
            self.credentials = {'Authorization':'Bearer ' + self.token["access_token"]}
            return
        print("Token acquisition failed: " + self.token["error_description"])

    def loginWithSecret(self, tenant, clientId, secret):
        """Authenticate as an application using a client secret (client credentials flow).

        Suitable for unattended/service-to-service scenarios. On success,
        sets ``self.token`` and ``self.credentials`` (a Bearer
        ``Authorization`` header). On failure, prints the error
        description returned by MSAL and leaves ``self.credentials``
        unset.

        Args:
            tenant: The Azure AD tenant id or domain the app is registered
                in.
            clientId: The application (client) id.
            secret: The application's client secret. Treat this as a
                sensitive credential -- do not hardcode it in source
                files; load it from an environment variable or secret
                store.
        """
        authority = "https://login.microsoft.com/" + tenant
        s = ["api://opendatadsl/.default"]
        ccapp = ConfidentialClientApplication(client_id=clientId, client_credential=secret, authority=authority)
        self.token = ccapp.acquire_token_for_client(scopes=s)
        if "access_token" in self.token:
            self.credentials = {'Authorization':'Bearer ' + self.token["access_token"]}
            return
        print("Token acquisition failed: " + self.token["error_description"])

    def loginWithAPIKey(self, userid, apikey):
        """Authenticate using a user id and API key (HTTP Basic auth).

        Sets ``self.credentials`` to a Basic ``Authorization`` header built
        from ``userid:apikey``. Does not contact the server or validate the
        credentials -- failures will only surface on the first subsequent
        API call.

        Args:
            userid: The ODSL user id (typically an email address).
            apikey: The API key for that user. Treat this as a sensitive
                credential -- do not hardcode it in source files; load it
                from an environment variable or secret store.
        """
        b = base64.b64encode(bytes(userid+':'+apikey, 'utf-8'))
        self.credentials = {'Authorization':'Basic ' + str(b, 'utf-8')}

    def loginWithToken(self, token):
        """Authenticate using a pre-acquired bearer token.

        Useful when a token has already been obtained elsewhere (e.g. by
        another process or an earlier MSAL call) and you want to reuse it
        directly. Sets both ``self.token`` and ``self.credentials`` (a
        Bearer ``Authorization`` header). Does not validate the token --
        failures will only surface on the first subsequent API call.

        Args:
            token: A valid ODSL access token string.
        """
        self.credentials = {'Authorization':'Bearer ' + token}
        self.token = token

    def logout(self):
        """Clear credentials and remove the local MSAL token cache.

        Resets ``self.token`` and ``self.credentials`` to ``None`` and
        deletes the on-disk token cache file used by ``login()``.
        """
        self.token = None
        self.credentials = None
        self.cache.logout()
