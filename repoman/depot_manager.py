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
import os
import tempfile

from repoman.depot import Depot
from repoman.depot_operations import DepotOperations
from repoman.roster import Roster, RosterError

logger = logging.getLogger(__name__)


class CloneProvisionError(Exception):
    """ Raised when a repo cannot be provisioned. """
    pass


class DepotManager(object):
    """
    Acts as an public facing API for working with managed clones.

    :param main_workspace: directory where all the workspaces will be
        created.
    :type main_workspace: string
    :param repo_kind: Repository type
    :type repo_kind: string
    :param main_source: FIXME
    :type main_source: string
    """

    # Name of the main repo cache.
    cache_name = 'main_cache'

    # Name of the file storing the roster.
    squadron_roster_name = 'squadron_roster.db'

    # Prefix for the clones used by the workers.
    workspaces_prefix = 'workspace'

    def __init__(self,
                 main_workspace="~/.repo",
                 repo_kind='hg',
                 main_source=None):
        self.dvcs = DepotOperations.get_depot_operations(repo_kind)
        try:
            self.main_work_path = os.path.expanduser(main_workspace)
            logger.debug('Main workspace: %s' % self.main_work_path)
            self.main_cache_path = os.path.join(self.main_work_path,
                                                DepotManager.cache_name)
            self.squadron_roster_path = os.path.join(
                self.main_work_path, DepotManager.squadron_roster_name)

            # Create the environment.
            if not os.path.isdir(self.main_work_path):
                os.makedirs(self.main_work_path)

            # Create main cache.
            if not self.dvcs.is_a_depot(self.main_cache_path):
                self.main_cache = self.dvcs.init_depot(self.main_cache_path,
                                                       source=main_source)
            else:
                self.main_cache = Depot(self.main_cache_path, None, self.dvcs)

            self.roster = Roster(self.squadron_roster_path)

        except Exception, e:
            raise CloneProvisionError(e)

    def _provision_new_clone(self):
        try:
            # Create a new safe directory for the clone.
            clone_directory = tempfile.mkdtemp(
                prefix=DepotManager.workspaces_prefix,
                dir=self.main_work_path)

            # Create repo (Using the cache)
            result = self.dvcs.init_depot(
                clone_directory, parent=self.main_cache)

        except Exception:
            logger.exception("Error provisioning new clone")
            raise CloneProvisionError("Error provisioning new clone")
        return result

    def give_me_depot(self, task_guid, task_name,
                      requirements=None, default_source=None):
        """
        Reserves or prepares a new repository workspace.

        :param task_guid: Identifier of the task reserving the clone.
        :param task_name: Name of the task for information purposes
        :param requirements: requirements to pull
        :param default_source: default clone source
        :returns: a free repo.
        :rtype: :py:class:`~repoman.depot.Depot`
        :raises RepoProvisionError: When a new repo cannot be provisioned.
        """
        assert task_guid, "Error getting clone, task_guid is mandatory"
        assert task_name, "Error getting clone, task_name is mandatory"
        try:
            roster_entry = self.roster.reserve_clone(task_guid, task_name)
            logger.debug('roster: %s' % roster_entry)
            clone = self.dvcs.get_depot_from_path(
                roster_entry.path, parent=self.main_cache)
        except RosterError:
            logger.debug('no roster entry found, cloning')
            # Create a new clone in the squadron if none are free
            clone = self._provision_new_clone()
            self.roster.add(clone.path, task_guid, task_name)

        if default_source is not None:
            clone.set_source(default_source)

        if requirements is not None:
            # Request the refresh to comply with the requirements.
            clone.request_refresh(requirements)

        return clone

    def give_me_depot_from_path(self, path):
        """
        Gets a repository from the current path without checking its state, no
        matter if it's FREE or INUSE

        :param path: depot path to get
        :type path: string
        """
        if self.dvcs.is_a_depot(path):
            return self.dvcs.get_depot_from_path(path, parent=self.main_cache)
        raise CloneProvisionError(
            "Error getting clone from path %s, it doesn't exist" % path)

    def free_depot(self, depot, task_guid):
        """
        Frees a repository for new uses.

        :param clone: a RepoWorkspace to be freed from use.
        :param task_guid: Identifier of the task reserving the clone.
        :raises RepoFreeError: When a repo cannot be freed.
        """
        self.dvcs.clear_depot(depot.path)
        self.roster.free_clone(
            self.get_not_available_clone(depot.path), task_guid)

    @staticmethod
    def _get_first_matching_clone(clone_list, path):
        for clone in clone_list:
            if clone.path == path:
                return clone
        return None

    def get_available_clone(self, path):
        """
        :returns: a clone with the available clone specified by path
        :rtype: RepoWorkspace
        """
        clone_list = self.roster.get_available()
        return self._get_first_matching_clone(clone_list, path)

    def get_not_available_clone(self, path):
        """
        :returns: a clone with the not available clone specified by path
        :rtype: RepoWorkspace
        """
        clone_list = self.roster.get_not_available()
        return self._get_first_matching_clone(clone_list, path)
