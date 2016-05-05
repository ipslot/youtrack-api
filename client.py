# vim: set fileencoding=utf-8
from __future__ import unicode_literals

import ssl
import time
import json
import http
import http.client
import urllib.parse
import urllib.request
from base64 import b64encode
from tornado.httpclient import AsyncHTTPClient

from .parser import extract_task_list, extract_spent_time_list, extract_users, \
    extract_user

ISSUE_URI = "/rest/issue"
USERS_URI = "/rest/admin/user"
USER_URI = "/rest/admin/user/{user}"
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
                port=self._auth_port,
                # for untrusted https.
                context=ssl._create_unverified_context())
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

    # todo: not tested
    def make_async_request(self, method, uri, callback):
        return AsyncHTTPClient().fetch(**{
            "request": "{}:{}{}".format(self._api_host, self._api_port, uri),
            "method": method,
            "ssl_options": ssl._create_unverified_context(),
            "headers": {
                "Authorization": "{type} {token}".format(
                    type="Bearer",
                    token=self.auth())}
        })

    def make_basic_request(self):
        conn = http.client.HTTPSConnection(
            host=self._api_host,
            port=self._api_port,
            # for untrusted https.
            context=ssl._create_unverified_context())
        headers = {"Authorization": "{type} {token}".format(
            type="Bearer",
            token=self.auth())}
        return conn, headers

    def get_queried_tasks(self, query):
        conn, headers = self.make_basic_request()
        conn.request(
            "GET",
            ISSUE_URI + "?filter=" + urllib.request.quote(query) +
            # todo: this hack for getting all issues per one request
            "&max=10000",
            headers=headers)
        resp = conn.getresponse()
        if resp.status == 200:
            return extract_task_list(resp.read())
        else:
            return None

    def get_flagged_tasks(self, flag_name):
        return self.get_queried_tasks("tag:{flag}".format(flag=flag_name))

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
            return []

    def get_user_info(self, user_login):
        conn, headers = self.make_basic_request()
        conn.request(
            "GET",
            USER_URI.format(user=user_login),
            headers=headers)
        resp = conn.getresponse()
        if resp.status == 200:
            return extract_user(resp.read())
        else:
            return []

    def get_users(self):
        def get_users_page(start):
            conn, headers = self.make_basic_request()
            conn.request(
                "GET",
                USERS_URI +
                "?start={}".format(start),
                headers=headers)
            resp = conn.getresponse()
            if resp.status == 200:
                return extract_users(resp.read())
            else:
                return []

        page = 1
        result = []
        users_list = get_users_page(page)

        while users_list:
            page += 1
            result += users_list
            users_list = get_users_page(page)

        return result

    def get_users_full_info(self):
        users = self.get_users()
        for user in users:
            user['name'] = \
                self.get_user_info(user.get("login")).get('name', None)
        return users
