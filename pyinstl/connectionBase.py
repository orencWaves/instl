#!/usr/bin/env python2.7
from __future__ import print_function

import abc
import urllib
import urlparse
import boto

from configVarStack import var_stack

class ConnectionBase(object):
    repo_connection = None # global singleton, holding current connection
    def __init__(self):
        pass

    @abc.abstractmethod
    def open_connection(self, credentials):
        pass

    @abc.abstractmethod
    def translate_url(self, in_bare_url):
        pass

class ConnectionHTTP(ConnectionBase):
    def __init__(self):
        super(ConnectionHTTP, self).__init__()

    def open_connection(self, credentials):
        pass

    @abc.abstractmethod
    def translate_url(self, in_bare_url):
        retVal = urllib.quote(in_bare_url, "$()/:")
        return retVal


class ConnectionS3(ConnectionBase):
    def __init__(self, credentials):
        super(ConnectionS3, self).__init__()
        self.default_expiration = 60*60*24 # in seconds
        self.boto_conn = None
        self.open_connection(credentials)
        self.open_bucket = None

    def open_connection(self, credentials):
        in_access_key, in_secret_key, in_bucket = credentials
        self.boto_conn = boto.connect_s3(in_access_key, in_secret_key)
        self.open_bucket = self.boto_conn.get_bucket(in_bucket)
        var_stack.set_var("S3_BUCKET_NAME", "from command line options").append(in_bucket)

    def translate_url(self, in_bare_url):
        parseResult = urlparse.urlparse(in_bare_url)
        if self.open_bucket is None:
            self.open_bucket = self.boto_conn.get_bucket(parseResult.netloc)
        the_key = self.open_bucket.get_key(parseResult.path, validate=False)
        retVal = the_key.generate_url(self.default_expiration)
        return retVal


def connection_factory(credentials=None):
    if credentials is None:
        ConnectionBase.repo_connection = ConnectionHTTP()
    else:
        cred_split = credentials.split(":")
        if cred_split[0].lower() == "s3":
            ConnectionBase.repo_connection = ConnectionS3(cred_split[1:])
