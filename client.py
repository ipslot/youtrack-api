# vim: set fileencoding=utf-8
from __future__ import unicode_literals

import time
import json
import http
import http.client
import urllib.parse
import urllib.request
from base64 import b64encode

from .parser import extract_task_list, extract_spent_time_list

ISSUE_URI = "/rest/issue"
TIME_TRACKING_URI = ISSUE_URI + "/{issue_id}/timetracking/workitem"


class YTClient:

    def __init__(self, uid, secret, scope, api_host, api_port=443,
                 auth_host=None, auth_port=None):
        self._uid = uid
        self._secret = secret
        self._scope = scope
        self._api_host = api_host
        self._api_port = api_port
        self._auth_key = None
        self._auth_key_expired = 0
        self._auth_host = auth_host if auth_host else api_host
        self._auth_port = auth_port if auth_port else api_port

    def is_authenticated(self):
        timestamp = int(time.time())
        return self._auth_key and self._auth_key_expired > timestamp

    def auth(self):
        if not self.is_authenticated():
            auth_host = self._auth_host.split("/")[0]
            auth_uri = (self._auth_host.replace(auth_host, "/") + "/").\
                replace("//", "/")
            conn = http.client.HTTPSConnection(
                host=auth_host,
                port=self._auth_port)
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization":
                    "{type} {token}".format(
                        type="Basic",
                        token=b64encode(
                            "{uid}:{secret}".
                            format(uid=self._uid, secret=self._secret).
                            encode("ascii")).
                        decode("utf8"))}
            params = urllib.parse.urlencode({
                "grant_type": "client_credentials",
                "scope": self._scope})
            conn.request("POST",
                         auth_uri + "api/rest/oauth2/token",
                         params,
                         headers=headers)
            resp = conn.getresponse()
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf8"))
                self._auth_key = data.get("access_token", None)
                self._auth_key_expired = \
                    int(time.time()) + int(data.get("expires_in", 0))
        return self._auth_key

    def make_basic_request(self):
        conn = http.client.HTTPSConnection(
            host=self._api_host,
            port=self._api_port)
        headers = {"Authorization": "{type} {token}".format(
            type="Bearer",
            token=self.auth())}
        return conn, headers

    def get_flagged_tasks(self, flag_name):
        return self.get_queried_tasks("tag:{flag}".format(flag=flag_name))

    def get_queried_tasks(self, query):
        conn, headers = self.make_basic_request()
        conn.request(
            "GET",
            ISSUE_URI + "?filter=" + urllib.request.quote(query),
            headers=headers)
        resp = conn.getresponse()
        if resp.status == 200:
            return extract_task_list(resp.read())
        else:
            return None

    def get_spent_time_for_task(self, task_id):
        conn, headers = self.make_basic_request()
        conn.request(
            "GET",
            TIME_TRACKING_URI.format(issue_id=task_id),
            headers=headers)
        resp = conn.getresponse()
        if resp.status == 200:
            return extract_spent_time_list(resp.read())
        else:
            return None