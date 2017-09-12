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
import sh

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
        missing = []
        for c in changesets:
            try:
                sh.git('rev-parse', c, _cwd=path)
            except sh.ErrorReturnCode:
                missing.append(c)
        return missing

    def grab_changesets(self, path, url, changesets):
        """
        Inherited method :func:`~DepotOperations.grab_changesets`
        """
        logger.debug('Grabbing changesets from %s to %s' % (url, path))
        # Force handling it as a bare repository so even current branch can be
        # overwritten by fetch
        git_path = os.path.join(
            path,
            sh.git('rev-parse', '--git-dir', _cwd=path).strip())
        sh.git('-c', 'core.bare=true', 'fetch', url, '+refs/*:refs/*', _cwd=git_path)
        if sh.git('rev-parse', '--is-bare-repository', _cwd=path).strip() == 'false':
            self._clear_working_copy(path)
        self._save_state(path)

        for c in changesets:
            try:
                sh.git('log', '-1', c, _cwd=path)
            except sh.ErrorReturnCode:
                return False
        return True

    def init_depot(self, path, parent=None, source=None):
        """
        Inherited method :func:`~DepotOperations.init_depot`
        """
        logger.info('Initializing Depot %s with parent %s' % (
                    path, parent))
 
        sh.git('init', path, bare=not parent)

        logger.info('Done initializing depot')
        return self.get_depot_from_path(path, parent)

    def is_a_depot(self, path):
        """
        Inherited method :func:`~DepotOperations.is_a_depot`
        """
        try:
            sh.git('rev-parse', _cwd=path)
            return True
        except:
            return False

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
        index_lock_path = os.path.join(self._git_path(path), 'index.lock')
        if os.path.exists(index_lock_path):
            os.remove(index_lock_path)

    def _clear_working_copy(self, path):
        sh.git("reset", "--hard", _cwd=path)
        sh.git("clean", "-fdx", _cwd=path)

    def _git_path(self, path):
        git_dir = sh.git('rev-parse', '--git-dir', _cwd=path).strip()
        return os.path.join(path, git_dir)

    def clear_depot(self, path):
        """
        Inherited method :func:`~DepotOperations.clear_depot`
        """
        logger.debug("Clearing depot %s" % path)
        self._restore_state(path)
        self._clear_working_copy(path)

    def _save_state(self, path):
        self._save_state_refs(self._git_path(path))
        self._save_state_head(self._git_path(path))

    def _restore_state(self, path):
        self._restore_state_refs(self._git_path(path))
        self._restore_state_head(self._git_path(path))

    def set_source(self, path, source):
        """
        Inherited method :func:`~DepotOperations.set_source`
        """
        remotes = sh.git("remote")
        if "origin" in remotes:
            sh.git("remote", "set-url", "origin", source)
        else:
            sh.git("remote", "add", "origin", source)
