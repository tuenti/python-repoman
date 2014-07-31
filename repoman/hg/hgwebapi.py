#!/usr/bin/env python
#
# Copyright 2014 Tuenti Technologies S.L.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import logging
import urllib2
import urlparse

logger = logging.getLogger(__name__)


class HGWebApi(object):

    _opener = None
    _base_url = None
    _user = None
    _password = None
    _raw_style = "?style=raw"

    def __init__(self, base_url, user, password):
        self._base_url = base_url
        self._user = user
        self._password = password

    def get_branches(self, repository, limit=None):
        """
        Get the branches for the given repository

        :param repository: repository name
        :type repository: string
        :param limit: max search
        :type limit: int

        :returns: generator with the branch names
        """
        url_param = "%s/%s" % (repository, 'branches')
        url = self._build_url(url_param)
        lines = self.opener.open(url).readlines()

        for line in enumerate(lines):
            if limit and limit <= line[0]:
                break
            yield line[1].split('\t')[0]

    def _build_url(self, url_params):
        url = urlparse.urljoin(self._base_url,
                               "%s%s" % (url_params, self._raw_style))

        logger.info("HGWebUrl: %s" % url)
        return url

    @property
    def opener(self):
        if not self._opener:
            password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
            password_mgr.add_password(None, self._base_url, self._user,
                                      self._password)
            auth_handler = urllib2.HTTPBasicAuthHandler()
            auth_handler.passwd = password_mgr
            self._opener = urllib2.build_opener(auth_handler,
                                                urllib2.HTTPHandler())
        return self._opener
