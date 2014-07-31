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

from repoman.repository import repository_factory

logger = logging.getLogger(__name__)


class Depot(object):
    """ Manages a depot. """
    def __init__(self, path, parent, dvcs):
        self.path = path
        self.ops = dvcs
        self.parent = parent
        self._repository = None

    @property
    def repo_kind(self):
        return self.ops.KIND

    @property
    def repository(self):
        if self._repository is None:
            self._repository = repository_factory(self.path,
                                                  repo_kind=self.repo_kind)
        return self._repository

    def request_refresh(self, requirements):
        """
        Refresh a clon with the required changesets from upstream cache.

        :param requirements: requirements with the following type:
            {'repository_path': [changeset1, changeset2,...],...}
        :type requirements: dict
        :returns: True is successfull.
        """
        logger.info('Requested refresh of %s' % (self.path))
        actually_required = self._filter_missing_changesets(requirements)
        logger.debug('Actually required changesets: %s' %
                     actually_required.values())
        return self.grab_changesets_from_upstream(actually_required)

    def grab_changesets_from_upstream(self, requirements):
        """
        Copy the specified requirements from their origins, add them to this
        repo.

        :param requirements:
            {'repository_path': [changeset1, changeset2, ...],...}
        :type requirements: dict
        """
        logger.debug('(%s) Grabbing changesets from upstream.' % self.path)

        if not self.parent:
            logger.debug('(%s) I am the root cache. Grabbing outside' %
                         self.path)
            for url in requirements:
                logger.debug('Grabbing from %s' % url)
                # TODO: Test Me!!!
                if not self.ops.grab_changesets(
                        self.path, url, requirements[url]):
                    logger.error('Couldn\'t grab required changesets from %s' %
                                 url)
                    return False
        else:
            logger.debug('(%s) I have a root (%s). Requesting from it' % (
                self.path, self.parent.path))
            if not self.parent._grab_changesets_to_(requirements, self.path):
                logger.error(
                    'Couldn\'t grab required changesets %s' % requirements)
                return False
        logger.debug('Grabbing successful from %s' % (self.path))
        return True

    def set_source(self, source):
        """
        Set the default source in the dvcs
        """
        self.ops.set_source(self.path, source)

    def _filter_missing_changesets(self, requirements):
        """
        Compares the actual changesets and return the missing ones.

        :param required: {'repository_path': [changeset1, changeset2,...],...}
        :returns: {'repository_path': [changeset1, changeset2,...],...}
        """
        actually_required = {}
        for repo_url, changesets in requirements.items():
            missing = self.ops.check_changeset_availability(
                self.path, changesets)
            if missing:
                actually_required[repo_url] = missing
        return actually_required

    def _grab_changesets_to_(self, requirements, path):
        # Test Me please!!!!
        logger.debug('Grabbing local changesets from %s to %s' % (
                     self.path, path))
        if not self.grab_changesets_from_upstream(requirements):
            return False

        for url in requirements:
            if not self.ops.grab_changesets(
                    path, self.path, requirements[url]):
                logger.error(
                    '(%s) Couldn\'t grab required changesets from %s' % (
                        self.path, url))
                return False
        return True
