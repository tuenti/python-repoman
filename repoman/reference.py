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


class Reference(object):
    """
    This class represents a SCM reference.
    A reference is just a pointer to a specific changeset.
    """
    name = None
    repository = None

    def __init__(self, name, repository):
        """
        Creates a reference with the given name and pointing to the given
        changeset

        :param name: Name of the reference
        :type string
        :param repository: Repository that belongs to
        :type Repository: repoman.repository
        """
        self.name = name
        self.repository = repository

    def get_changeset(self):
        return self.repository[self.name]

    def __str__(self):
        return self.name
