import json

class Schema(object):
    """
    Represents a schema blob.

    Schema blobs are JSON objects with at least two attributes always set: 
    camliVersion, which is always 1, and camliType, which tells you the 
    type of metadata the blob contains.
   
    See http://camlistore.org/docs/schema for more 
    """
    def parsed_json_helper(self):
        # Just toss a TypeError here if passed something not JSON
        self._parsed_json = json.loads(self.blob.data)
        if type(self._parsed_json) is not dict or \
            'camliVersion' not in self._parsed_json or \
            'camliType' not in self._parsed_json or \
            self._parsed_json['camliVersion'] != 1:
            from camlistore.exceptions import MissingFieldError
            raise MissingFieldError
             

    def __init__(self, blob):
        self.blob = blob 
        self.parsed_json_helper()

    #
    # this needs to be actually thought out - if a schema element changes, the 
    # underlying  blob has to change, too. I'm not sure what the right interface 
    # into a schema should be - twiddling with the JSON directly, or treating it 
    # always as a dictionary that's only serialized to JSON at the last possible
    # minute. 
    #
    # my original thinking was some magic watching ala the camlistore.Blob, 
    # so if the parsed json changes, update the string, 
    # or if the string changes, reparse the dictionary.
    # at the moment, the only thing I want this for is to add camliSigner
    # For now, just json.dumps back to the string, and assume no one
    # changes the blob.data on us
    #
    #
    def add_attribute(self, k, v):
        self._parsed_json[k]=v
        self.blob.data = json.dumps(self.parsed_json)
        self.parsed_json_helper()

    @property
    def parsed_json(self):
         if self._parsed_json is None:
            self.parsed_json_helper()
         return self._parsed_json

