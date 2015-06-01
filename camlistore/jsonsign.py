import sys
import shutil
import os.path
import gnupg

class JsonSign(object):
    """
    Use the Sign Helper to sign a Json blob. Eventually, also support 
    signing JSON using PyCrypto or something locally

    Callers should not instantiate this class directly. Instead, call
    :py:func:`camlistore.connect` to obtain a
    :py:class:`camlistore.Connection`
    object and access :py:attr:`camlistore.Connection.jsonsign`.
    """

    def __init__(self, http_session, sign_handler, public_key_ref, public_key_id, public_key, client_config):
        self.http_session = http_session
        self.sign_handler = sign_handler
        self.public_key_ref = public_key_ref
        self.public_key_id = public_key_id
        self.public_key = public_key
        self.client_config = client_config


    def sign_schema(self, schemablob):
        """
        Upload a schema blob to camlistore and get it signed.
        """
        if schemablob.has_attribute('camliSigner'):
          pass
        else:
          schemablob.add_attribute('camliSigner', self.public_key_ref)
        t = schemablob.blob.data.rstrip()
        if not t.endswith('}'):
          print "Error, t is bogus: %s" % (t)
        t = t[:-1]

        #alas, this makes lots of temporary files
        import tempfile  
        home = tempfile.mkdtemp() 
        try:
          gpg = gnupg.GPG(gnupghome=home, keyring='tempkeyring', 
                          secret_keyring=self.client_config['identitySecretRing'],
                          options=['--no-default-keyring'])
          import_result = gpg.import_keys(self.public_key)
          signature = gpg.sign(t, detach=True)
       
          # this next part is cribbed nearly exactly from the golang impl 
          sig = str(signature) 
          index1 = sig.index("\n\n")
          index2 = sig.index("\n-----")

          if index1 == -1 or index2 == -1:
            print "Failed to parse signature from gpg."
          inner = sig[index1+2:index2]
	  inner = inner.translate(None, '\n')

	  return "%s,\"camliSig\":\"%s\"}\n" % (t, inner)
        except Exception as e:
          print e
        finally:
          shutil.rmtree(home) 
