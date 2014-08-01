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

import getpass
import socket


class Signature(dict):
    @property
    def user(self):
        if 'user' in self:
            return self['user']
        return getpass.getuser()

    @property
    def email(self):
        if 'email' in self:
            return self['email']
        return "%s@%s" % (self.user, socket.gethostname())

    @property
    def author(self):
        if 'author' in self:
            return self['author']
        return self.user

    @property
    def author_email(self):
        if 'author_email' in self:
            return self['author_email']
        return self.email

    def __str__(self):
        return "%s <%s>" % (self.user, self.email)
