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

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

from repoman.utils.introspection.dynamic_class_loading import \
    get_class_from_name

logger = logging.getLogger('MultiRepoIndexer')


class MultiRepoIndexer(object):
    """
    MultiRepoIndexer is a repo indexer that search in multiple sources
    ordered by priority. If one doesn't find the data, it will search
    in the next one.
    You can register as many repository indexers as you want

    :param repository_name_matrix: is a dict that represent each repository
                                  name for the registered indexers, the dict
                                  key is the repository id
    :type repository_name_matrix: dict
    :param indexers_list: Every item in the list is a tuple
                         that contains: priority, indexer path, indexer id
                         and another tuple with the auth credentials
    :type indexers_list: list of indexers
    """

    _indexers = None
    _repo_name_matrix = None

    def __init__(self, repository_name_matrix, indexers_list=None):
        self._indexers = OrderedDict()
        self._repo_name_matrix = repository_name_matrix
        if indexers_list:
            for (priority, indexer, id, auth) in indexers_list:
                self.register_indexer(priority, indexer, id, auth)

    def register_indexer(self, priority, indexer, id, auth):
        """
        This method register a new indexer

        :param priority: indexer priority
        :type priority: int
        :param indexer: module plus class name to instantiate,
                        having this form: module1.module2.ClassName
        :type indexer: string
        :param id: repository
        :type id: string
        :param auth: tuple that contains 3 elements: url, user
                and password
        :type auth: tuple
        """
        indexer_clazz = get_class_from_name(indexer)
        if id in self._repo_name_matrix:
            repo_name = self._repo_name_matrix[id]
            self._indexers[priority] = indexer_clazz(
                repo_name, auth[0], auth[1], auth[2])
            self._indexers = self._sort_by_priority(self._indexers)

    def _sort_by_priority(self, indexers):
        sorted_indexers = OrderedDict()
        keys = indexers.keys()
        keys.sort(key=int)
        for key in keys:
            sorted_indexers[key] = indexers[key]

        return sorted_indexers

    def _call_indexers(self, func, *args):
        for (priority, indexer) in self._indexers.iteritems():
            try:
                logger.info("Calling %s from\
                             %s" % (func, indexer.__class__.__name__))
                method = getattr(indexer, func)
                result = method(*args)
                if result:
                    return result
            except Exception:
                logger.info("Error in indexer %s executing\
                             %s" % (indexer.__class__.__name__, func))
        raise RepoIndexerError("Not found in any indexer")

    def get_branches(self, limit=None):
        """
        Returns the branches in the repository, it look for them in all the
        registered repositories by priority

        :param limit:
        :type limit: int
        :returns: list of strings with the name of the branches
        """
        return self._call_indexers('get_branches', limit)

    def get_branch_log(self, branch_name, limit=None):
        """
        Returns the log for the given brancha and limit

        :param branch_name:
        :type branch_name: string
        :param limit:
        :type limit: int
        :returns: list of tuples with the log information
        """
        return self._call_indexers('get_branch_log', branch_name, limit)


class RepoIndexerError(Exception):
    pass
