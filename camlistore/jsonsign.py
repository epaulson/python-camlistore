import sys

class JsonSign(object):
    """
    Use the Sign Helper to sign a Json blob. Eventually, also support 
    signing JSON using PyCrypto or something locally

    Callers should not instantiate this class directly. Instead, call
    :py:func:`camlistore.connect` to obtain a
    :py:class:`camlistore.Connection`
    object and access :py:attr:`camlistore.Connection.jsonsign`.
    """

    def __init__(self, http_session, sign_handler, public_key):
        self.http_session = http_session
        self.sign_handler = sign_handler
        self.public_key = public_key


    def sign_schema(self, schemablob):
        """
        Upload a schema blob to camlistore and get it signed.
        """
        import hashlib

        upload_url = self.sign_handler
        if 'camliSigner' not in schemablob.parsed_json:
            schemablob.add_attribute("camliSigner", self.public_key)
        encoded = {u'json': schemablob.blob.data} 
        resp = self.http_session.post(upload_url, data=encoded)
        if resp.status_code != 200:
            from camlistore.exceptions import ServerError
            raise ServerError(
                "Failed to sign blob: got %i %s" % (
                    resp.status_code,
                    resp.reason,
                )
            )

        return resp.text

