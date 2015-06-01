
import json
import pkg_resources
import os
import sys


version = pkg_resources.get_distribution("camlistore").version
user_agent = "python-camlistore/%s" % version


class Connection(object):
    """
    Represents a logical connection to a camlistore server.

    Most callers should not instantiate this directly, but should instead
    use :py:func:`connect`, which implements the Camlistore server discovery
    protocol to auto-configure an instance of this class.

    Note that this does not imply a TCP or any other kind of socket connection,
    but merely some persistent state that will be used when making requests
    to the server. In particular, several consecutive requests via the
    same connection may be executed via a single keep-alive HTTP connection,
    reducing round-trip time.
    """

    #: Provides access to the server's blob store via an instance of
    #: :py:class:`camlistore.blobclient.BlobClient`.
    blobs = None

    #: Provides access to the server's search interface via an instance of
    #: :py:class:`camlistore.searchclient.SearchClient`.
    searcher = None

    def __init__(
        self,
        http_session=None,
        blob_root=None,
        search_root=None,
        sign_handler=None,
        public_key_ref=None,
        public_key_id=None,
        public_key=None,
        client_config=None,
    ):
        self.http_session = http_session
        self.blob_root = blob_root
        self.search_root = search_root
        self.sign_handler = sign_handler
        self.public_key_ref = public_key_ref
        self.public_key_id = public_key_id
        self.public_key = public_key
        self.client_config = client_config

        from camlistore.blobclient import BlobClient
        self.blobs = BlobClient(
            http_session=http_session,
            base_url=blob_root,
        )

        from camlistore.searchclient import SearchClient
        self.searcher = SearchClient(
            http_session=http_session,
            base_url=search_root,
        )

        from camlistore.jsonsign import JsonSign
        self.jsonsign = JsonSign(
            http_session=http_session,
            sign_handler=sign_handler,
            public_key_ref=public_key_ref,
            public_key_id=public_key_id,
            public_key=public_key,
            client_config=client_config
        )


# Internals of the public "connect" function, split out so we can easily test
# it with a mock http_session while not making the public interface look weird.
def _connect(base_url, http_session):
    from urlparse import urljoin

    config_url = urljoin(base_url, '?camli.mode=config')
    config_resp = http_session.get(config_url)

    if config_resp.status_code != 200:
        from camlistore.exceptions import NotCamliServerError
        raise NotCamliServerError(
            "Configuration request returned %i %s" % (
                config_resp.status_code,
                config_resp.reason,
            )
        )

    # FIXME: Should verify that the response has the right Content-Type,
    # but right now the reference camlistore implementation returns
    # text/javascript rather than application/json, so want to confirm
    # that's expected before hard-coding it.

    try:
        raw_config = json.loads(config_resp.content)
    except ValueError:
        # Assume ValueError means JSON decoding failed, which means this
        # thing is not acting like a valid camli server.
        from camlistore.exceptions import NotCamliServerError
        raise NotCamliServerError(
            "Server did not return valid JSON at %s" % config_url
        )

    # If we were redirected anywhere during loading, use the final URL
    # as the basis for the rest of our work below.
    config_url = config_resp.url

    blob_root = None
    search_root = None
    sign_root = None

    if "blobRoot" in raw_config:
        blob_root = urljoin(config_url, raw_config["blobRoot"])

    if "searchRoot" in raw_config:
        search_root = urljoin(config_url, raw_config["searchRoot"])

    if "signing" in raw_config:
        if "signHandler" in raw_config["signing"]:
          sign_handler = urljoin(config_url, raw_config["signing"]["signHandler"])
        if "publicKeyBlobRef" in raw_config["signing"]:
          public_key_ref = raw_config["signing"]["publicKeyBlobRef"]
        if "publicKeyId" in raw_config["signing"]:
          public_key_id = raw_config["signing"]["publicKeyId"]
        if "publicKey" in raw_config["signing"]:
          public_key_url = raw_config["signing"]["publicKey"]


    public_key_resp = http_session.get(urljoin(base_url, public_key_url))
    if public_key_resp.status_code != 200:
        from camlistore.exceptions import NotFoundError
        raise NotFoundError(
            "Public Key request returned %i %s" % (
                public_key_resp.status_code,
                public_key_resp.reason,
            )
        )
    public_key = public_key_resp.text

    client_config = {}
    config_dir_path = os.environ.get("CAMLI_CONFIG_DIR", os.path.join(os.path.expanduser('~'), ".config","camlistore"))
    client_config_file = os.path.join(config_dir_path, "client-config.json")
   
    if os.path.isfile(client_config_file):
        with open(client_config_file) as f:
            client_config = json.load(f)

    secretRingPath = os.path.join(config_dir_path, "identity-secring.gpg")
    if 'identitySecretRing' in client_config:
      secretRingPath = client_config['identitySecretRing']
    secretRingPath = os.environ.get("CAMLI_SECRET_RING", secretRingPath)
    client_config['identitySecretRing'] = secretRingPath

    return Connection(
        http_session=http_session,
        blob_root=blob_root,
        search_root=search_root,
        sign_handler=sign_handler,
        public_key_ref=public_key_ref,
        public_key_id=public_key_id,
        public_key=public_key,
        client_config=client_config,
    )


def connect(base_url):
    """
    Create a connection to the Camlistore instance at the given base URL.

    This function implements the Camlistore discovery protocol to recognize
    a server and automatically determine which features are available,
    ultimately instantiating and returning a :py:class:`Connection` object.

    For now we assume an unauthenticated connection, which is generally
    only possible when connecting via ``localhost``. In future this function
    will be extended with some options for configuring authentication.
    """
    import requests
    import logging

   # these two lines enable debugging at httplib level (requests->urllib3->httplib)
   # you will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
   # the only thing missing will be the response.body which is not logged.
    if False:
      import httplib
      httplib.HTTPConnection.debuglevel = 1

      logging.basicConfig() # you need to initialize logging, otherwise you will not see anything from requests
      logging.getLogger().setLevel(logging.DEBUG)
      requests_log = logging.getLogger("requests.packages.urllib3")
      requests_log.setLevel(logging.DEBUG)
      requests_log.propagate = True

    http_session = requests.Session()
    http_session.trust_env = False
    http_session.headers["User-Agent"] = user_agent
    # TODO: let the caller pass in a trusted SSL cert and then turn
    # on SSL cert verification. Until we do that we're vulnerable to
    # certain types of MITM attack on our SSL connections.

    return _connect(
        base_url,
        http_session=http_session,
    )
