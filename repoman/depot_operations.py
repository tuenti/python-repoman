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

from repoman.depot import Depot


class DepotOperations(object):
    KIND = None

    @classmethod
    def get_depot_operations(cls, repo_kind):
        try:
            # __import__ in python < 2.7 works not very well
            # TODO: migrate to python 3.0 and change this
            mod = __import__("repoman.%s.depot_operations" % (repo_kind),
                             fromlist=['DepotOperations'])
            ConcreteDepotOperations = getattr(mod, 'DepotOperations')
            return ConcreteDepotOperations()
        except:
            raise NotImplementedError

    def check_changeset_availability(self, path, changesets):
        """ Check for changesets are already in the specified depot path.
        Always request all changesets from all sources. This means
        that the changesets will always be missing.

        :param path: Path to the depot.
        :param changesets: List of strings specifying the changesets.
        :returns: List of changesets missing
        """
        raise NotImplementedError

    def grab_changesets(self, path, url, changesets):
        """
        Copies changesets from the remote url to the specified path.

        :param path: target depot for the changesets.
        :param url: depot to copy the changesets from.
        :param changesets: List of changesets ids.
        :returns: True.
        """
        raise NotImplementedError

    def init_depot(self, path, parent=None, source=None):
        """
        Initializes a new depot

        :param path: path to the main depot

        :returns: Depot class corresponding to the path. False otherwise.
        """
        raise NotImplementedError

    def is_a_depot(self, path):
        """
        Check if the given path corresponds to a depot.

        :param path: path to the supposed depot

        :returns: True if a depot. False otherwise.
        """
        raise NotImplementedError

    def get_depot_from_path(self, path, parent=None):
        """
        Factory method that creates Depots from a given path

        :param path: Path of the depot

        :returns: Depot class corresponding to the path.
        """
        self._locks_cleanup(path)
        return Depot(path, parent, self)

    def _locks_cleanup(self, path):
        """
        Make sure that a clone has no unreleased locks because of some failed
        process.

        Implementation is not mandatory, but recommended in SCMs with locking
        mechanisms.

        :param path: Path of the depot
        """
        pass

    def clear_depot(self, path, parent=None):
        """
        Clear a depot just in case a previous usage let it dirty
        This should also reset configuration

        :param path: Path of the depot
        :param parent:
        """
        raise NotImplementedError

    def set_source(self, path, source):
        """
        Set the default remote source.

        :param path: Path of the depot
        :param source: Remote URI of the source repo
        """
        raise NotImplementedError
