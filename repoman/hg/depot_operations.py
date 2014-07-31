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

import os
import logging
import re

from repoman.depot_operations import DepotOperations as BaseDepotOps
from repoman.hg import hglibext as hglib


logger = logging.getLogger(__name__)


class DepotOperations(BaseDepotOps):
    """ Highlevel Mercurial DCVS operations. """
    KIND = 'hg'

    def check_changeset_availability(self, path, changesets):
        """ Inherited method
        :func:`~repoman.depot_operations.DepotOperations.check_changeset_availability`
        """
        missing = []
        try:
            with hglib.open(path) as dep:
                branches = dep.branches()
                for changeset in changesets:
                    try:
                        if changeset != 'tip':
                            isbranch = any(x[0] == changeset for x in branches)
                            if isbranch:
                                missing.append(changeset)
                            else:
                                log = dep.log(revrange=changeset)
                                if not log:
                                    missing.append(changeset)
                        else:
                            missing.append('tip')

                    except:
                        missing.append(changeset)
                logger.debug(
                    'Checking availability of changesets in %s: Missing %s' % (
                        path, "'".join(missing)))
        except (hglib.util.error.CommandError, hglib.error.ResponseError) as e:
            logger.exception(
                'Error in check_changeset_availability method: %s' % e)
        return missing

    def grab_changesets(self, path, url, changesets):
        """ Inherited method
        :func:`~repoman.depot_operations.DepotOperations.grab_changesets`
        """
        logger.debug('Grabbing changesets %s from %s to %s' % (
            "'".join(changesets), url, path))
        try:
            with hglib.open(path) as dep:
                result = dep.pull(source=url, rev=changesets)
                logger.debug('Done grabbing changesets %s' % result)
                return result
        except (hglib.util.error.CommandError, hglib.error.ResponseError) as e:
            logger.exception('Error Grabbing changesets: %s' % e)
            return False

    def init_depot(self, path, parent=None, source=None):
        """ Inherited method
        :func:`~repoman.depot_operations.DepotOperations.init_depot`
        """
        try:
            logger.info('Initializing Depot %s with parent %s' % (
                path, parent))
            result = hglib.init(dest=path)
            if result:
                result = self.get_depot_from_path(path, parent)
                logger.info('Done initializing Depot.')
        except Exception:
            logger.exception('Error Initializing Depot.')
            result = False
        return result

    def is_a_depot(self, path):
        """ Inherited method
        :func:`~repoman.depot_operations.DepotOperations.is_a_depot`
        """
        is_depot = os.path.isdir(path) and os.path.isdir(
            os.path.join(path, '.hg'))
        logger.info(' %s is_a_depot %s' % (path, is_depot))
        return is_depot

    def _locks_cleanup(self, path):
        """ Inherited method
        :func:`~repoman.depot_operations.DepotOperations._locks_cleanup`
        """
        # Removes repository and working directory locks in the required order
        # http://mercurial.selenic.com/wiki/LockingDesign
        lock_path = os.path.join(path, '.hg/store/lock')
        wlock_path = os.path.join(path, '.hg/wlock')
        for path in (lock_path, wlock_path):
            if os.path.exists(path):
                os.remove(path)

    def clear_depot(self, path):
        """ Inherited method
        :func:`~repoman.depot_operations.DepotOperations.clear_depot`
        """
        logger.debug("Clearing depot %s" % path)
        try:
            with hglib.open(path) as dep:
                status = dep.status()
                try:
                    dep.update(clean=True)
                except hglib.util.error.CommandError:
                    pass
                if status:
                    dep.revert(files="", all=True)
                    dep.purge(all=True)
                outgoing = dep.outgoing()
                if outgoing:
                    logger.debug(
                        "Need to strip outgoing commits, stripping...")
                    for out in outgoing:
                        try:
                            dep.strip(out.node)
                        except Exception as e:
                            logger.exception(
                                'Info: could not strip %s in the depot %s,'
                                ' but I can continue (%s)'
                                % (out.node, path, e))

        except (hglib.error.CommandError,
                hglib.error.ResponseError,
                hglib.error.ServerError,
                hglib.error.CapabilityError) as e:
            logger.exception('Error clearing the depot %s: %s' % (path, e))
        finally:
            hgrc_path = os.path.join(path, ".hg/hgrc")
            if os.path.exists(hgrc_path):
                with open(hgrc_path, 'w') as hgrc:
                    hgrc.write("")

    def set_source(self, path, source):
        """ Inherited method
        :func:`~repoman.depot_operations.DepotOperations.set_source`
        """
        try:
            with hglib.open(path) as dep:
                paths = dep.paths()
        except (hglib.util.error.ServerError,
                hglib.util.error.CommandError,
                hglib.error.ResponseError) as e:
            logger.exception('Error getting depot paths %s: %s' % (path, e))
            raise e

        if not paths or "default" not in paths or paths["default"] != source:
            hgrc_path = os.path.join(path, ".hg/hgrc")
            already_exists = os.path.exists(hgrc_path)
            with open(hgrc_path, 'r+' if already_exists else 'w') as hgrc:
                if already_exists:
                    prev_content = hgrc.read()
                    prev_has_path = re.search("default=.*($|\\n)",
                                              prev_content, re.MULTILINE)
                    if prev_has_path:
                        new_content = re.sub(
                            "default=.*($|\\n)",
                            "default=%s\n" % source, prev_content)
                    else:
                        new_content = "%s\n[paths]\ndefault=%s\n" % (
                            prev_content, source)
                else:
                    new_content = "[paths]\ndefault=%s\n" % source
                logger.debug(
                    "Setting default source in %s hgrc: %s"
                    % (path, new_content))
                hgrc.write(new_content)
