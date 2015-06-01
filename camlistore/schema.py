import json
import camlistore.blobclient

class Schema(object):
    """
    Represents a schema blob.

    Schema blobs are JSON objects with at least two attributes always set: 
    camliVersion, which is always 1, and camliType, which tells you the 
    type of metadata the blob contains.
   
    See http://camlistore.org/docs/schema for more 

    This implementation doesn't really do anything special with thus far, and
    is really just a wrapper around a dict, with a dump-to-a-blob helper
    Someday, maybe actually use this as a class hierarchy

    To use:
    import camlistore

    conn = camlistore.connect("http://localhost:3179/")

    schemablob = camlistore.Schema(1, "test")
    schemablob.add_attribute("foo", "zot")

    signed = conn.jsonsign.sign_schema(schemablob)

    print signed
    """

    def __init__(self, version=1, type="AnyBlob"):
        self._data = {}
        self._blob = None
        self._data['camliVersion'] = version
        self._data['camliType'] = type

    def add_attribute(self, k, v):
       self._data[k] = v
    
    def has_attribute(self, k):
       if k in self._data:
          return self._data[k]
       return None

    @property
    def blob(self):
         return camlistore.blobclient.Blob(json.dumps(self._data))

