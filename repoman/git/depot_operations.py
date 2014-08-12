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

from itertools import ifilter
import os
import shutil
import logging

import pygit2
from repoman.depot_operations import DepotOperations as BaseDepotOps


logger = logging.getLogger(__name__)


class DepotOperations(BaseDepotOps):
    """ Git Mercurial DCVS operations. """

    KIND = 'git'
    CACHE_REPO_ORIGIN = 'origin-all-refs'

    _REFS_DIR = 'refs'
    _REFS_PREVIOUS_DIR = 'refs.prev-state'
    _HEAD_FILE = 'HEAD'
    _HEAD_PREVIOUS_FILE = 'HEAD.prev-state'

    def check_changeset_availability(self, path, changesets):
        """
        Inherited method :func:`~DepotOperations.check_changeset_availability`
        """
        return changesets

    def grab_changesets(self, path, url, changesets):
        """
        Inherited method :func:`~DepotOperations.grab_changesets`
        """
        logger.debug('Grabbing changesets %s from %s to %s' % (
            ",".join(changesets), url, path))
        git_repo = pygit2.Repository(path)
        try:
            origin = self._set_origin_source(git_repo, url)
            result = origin.fetch()
            logger.debug('GIT Done grabbing changesets (%s)' % (result))
            self._save_state(path)
        except pygit2.GitError as e:
            logger.exception('Error Grabbing changesets: %s' % e)
            return False
        return True

    def init_depot(self, path, parent=None, source=None):
        """
        Inherited method :func:`~DepotOperations.init_depot`
        """
        try:
            logger.info('Initializing Depot %s with parent %s' % (
                        path, parent))
            bare = not parent

            pygit2.init_repository(path, bare)

            result = self.get_depot_from_path(path, parent)
            logger.info('Done initializing Depot.')
        except Exception:
            logger.exception('Error Initializing Depot.')
            return False
        return result

    def is_a_depot(self, path):
        """
        Inherited method :func:`~DepotOperations.is_a_depot`
        """
        is_depot = False
        if os.path.isdir(path):
            try:
                pygit2.Repository(path)
                is_depot = True
            except KeyError:
                logger.debug("KeyError initializing pygit2 repo at %s", path)

        logger.info(' %s is_a_depot %s' % (path, is_depot))
        return is_depot

    def _save_state_refs(self, git_path):
        refs_dir = os.path.join(git_path, self._REFS_DIR)
        refs_previous_dir = os.path.join(git_path, self._REFS_PREVIOUS_DIR)
        if os.path.isdir(refs_previous_dir):
            shutil.rmtree(refs_previous_dir)
        shutil.copytree(refs_dir, refs_previous_dir)

    def _restore_state_refs(self, git_path):
        refs_dir = os.path.join(git_path, self._REFS_DIR)
        refs_previous_dir = os.path.join(git_path, self._REFS_PREVIOUS_DIR)
        shutil.rmtree(refs_dir)
        if os.path.isdir(refs_previous_dir):
            logger.debug("Previous state available in %s" % refs_previous_dir)
            shutil.move(refs_previous_dir, refs_dir)
        else:
            os.makedirs(os.path.join(refs_dir, 'heads'))
            os.makedirs(os.path.join(refs_dir, 'tags'))

    def _save_state_head(self, git_path):
        head_file = os.path.join(git_path, self._HEAD_FILE)
        head_previous_file = os.path.join(git_path,
                                          self._HEAD_PREVIOUS_FILE)
        if os.path.isfile(head_previous_file):
            os.remove(head_previous_file)
        shutil.copyfile(head_file, head_previous_file)

    def _restore_state_head(self, git_path):
        head_file = os.path.join(git_path, self._HEAD_FILE)
        head_previous_file = os.path.join(git_path,
                                          self._HEAD_PREVIOUS_FILE)
        if os.path.isfile(head_previous_file):
            logger.debug("Previous HEAD available in %s" % head_previous_file)
            os.remove(head_file)
            shutil.move(head_previous_file, head_file)
        else:
            with open(head_file, 'w') as head:
                # master could not exist, but this would leave HEAD in the
                # same state as doing git init or git init and git fetch
                head.write('ref: refs/heads/master\n')

    def _locks_cleanup(self, path):
        """
        Inherited method :func:`~DepotOperations._locks_cleanup`
        """
        repository = pygit2.Repository(path)
        index_lock_path = os.path.join(repository.path, 'index.lock')
        if os.path.exists(index_lock_path):
            os.remove(index_lock_path)

    def _clear_working_copy(self, path):
        repository = pygit2.Repository(path)
        if repository.head_is_unborn:
            for dirty_file in os.listdir(path):
                if dirty_file != '.git':
                    dirty_file_path = os.path.join(path, dirty_file)
                    if os.path.isdir(dirty_file_path):
                        shutil.rmtree(dirty_file_path)
                    else:
                        os.remove(dirty_file_path)
        else:
            repository.reset(repository.head.target, pygit2.GIT_RESET_HARD)
            repository.checkout_head(
                    pygit2.GIT_CHECKOUT_FORCE |
                    pygit2.GIT_CHECKOUT_REMOVE_UNTRACKED)

    def clear_depot(self, path):
        """
        Inherited method :func:`~DepotOperations.clear_depot`
        """
        logger.debug("Clearing depot %s" % path)
        repository = pygit2.Repository(path)
        self._restore_state_refs(repository.path)
        self._restore_state_head(repository.path)
        self._clear_working_copy(path)

    def _save_state(self, path):
        repository = pygit2.Repository(path)
        self._save_state_refs(repository.path)
        self._save_state_head(repository.path)

    def set_source(self, path, source):
        """
        Inherited method :func:`~DepotOperations.set_source`
        """
        git_repo = pygit2.Repository(path)
        self._set_origin_source(git_repo, source)

    def _set_origin_source(self, git_repo, url):
        remotes = git_repo.remotes
        origin = next(ifilter(lambda r: r.name == 'origin', remotes), None)
        if len(remotes) == 0 or origin is None:
            origin = git_repo.create_remote('origin', url)
        elif origin.url != url:
            origin.url = url
        # Reset all refspecs
        origin.set_fetch_refspecs(['+refs/*:refs/*'])
        origin.save()
        return origin
