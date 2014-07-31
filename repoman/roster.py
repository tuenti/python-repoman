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

import collections
import sqlite3
import time

from datetime import timedelta
from datetime import datetime


class RosterError(Exception):
    pass


class MaxClonesLimitReached(RosterError):
    pass


class Clone(object):
    FREE = 'FREE'
    INUSE = 'INUSE'

    def __init__(self, path, status, task, task_name, timestamp):
        self.path = path
        self.status = status
        self.task = task
        self.task_name = task_name
        self.timestamp = timestamp

    def __eq__(self, other):
        return self.__dict__['path'] == other.__dict__['path'] \
            and self.__dict__['status'] == other.__dict__['status'] \
            and self.__dict__['task'] == other.__dict__['task']

    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return str(self.__dict__)


def marshall(clone):
    """
    Adapter for serializing the object into a string for db storage.

    :param clone: Clone class to be serialized.
    """
    return (clone.path, clone.status,
            clone.task, clone.task_name, clone.timestamp)


def unmarshall(db_str):
    """
    Creates a Python Clone object from the result of a db query.

    :param db_str: String from the database.
    """

    (path,
        status,
        task,
        task_name,
        timestamp) = db_str

    return Clone(path, status, task, task_name, timestamp)


class Roster(collections.MutableMapping):
    """Manages the file used as a roster. Provides dict API to it."""

    class DBCursor(object):
        def __init__(self, connection):
            self.cursor = connection.cursor()

        def __enter__(self):
            return self.cursor

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.cursor.close()

    def __cursor(self):
        return self.DBCursor(self.connection)

    def __init__(self,
                 location,
                 max_clones=12,
                 clone_timeout=timedelta(minutes=30)):

        self.location = location
        self.connection = sqlite3.connect(
            self.location,
            detect_types=sqlite3.PARSE_DECLTYPES,
            timeout=60,
            isolation_level='EXCLUSIVE')
        self.max_clone_limit = max_clones
        self.max_clone_reverved_time = clone_timeout
        with self.__cursor() as cursor:
            cursor.execute(
                'create table if not exists clones(' +
                'path PRIMARY KEY, status, task, task_name, timestamp)', )

    def __getitem__(self, key):
        with self.__cursor() as cursor:
            cursor.execute('SELECT * FROM clones WHERE path=?', (key,))
            result = cursor.fetchone()
            if not result:
                raise KeyError(key)
            return unmarshall(result)

    def __setitem__(self, key, value):
        if key in self:
            prev = self[key]
            if prev.task != value.task and prev.status != Clone.FREE:
                raise RosterError('Element already reserved by %s' %
                                  prev.task_name)
        self._replace_item_(key, value)

    def _get_time_(self):
        return time.time()

    def _replace_item_(self, key, value):
        value.path = key
        value.timestamp = self._get_time_()
        cursor = self.connection.cursor()
        cursor.execute('REPLACE INTO clones VALUES (?, ?, ?, ?, ?)',
                       marshall(value))
        self.connection.commit()
        cursor.close()

    def __delitem__(self, key):
        cursor = self.connection.cursor()
        self.connection.execute('DELETE FROM clones WHERE path=?', (key,))
        self.connection.commit()
        cursor.close()

    def __iter__(self):
        with self.__cursor() as cursor:
            cursor.execute('SELECT path FROM clones')
            while True:
                yield cursor.next()[0]

    def __len__(self):
        with self.__cursor() as cursor:
            size = len(cursor.execute('SELECT * FROM clones').fetchall())
            return size

    def _get_old_clones_(self):
        result = []
        with self.__cursor() as cursor:
            for raw_data in cursor.execute('SELECT * FROM clones').fetchall():
                temp_clone = unmarshall(raw_data)
                timestamp = datetime.fromtimestamp(temp_clone.timestamp)
                current = datetime.fromtimestamp(self._get_time_())
                if current - timestamp > self.max_clone_reverved_time:
                    result.append(temp_clone)
        return result

    def _clean_old_clones(self):
        for clone in self._get_old_clones_():
            self.free_clone(clone, clone.task)

    def reserve_clone(self, task, task_name):
        with self.__cursor() as cursor:
            reservation_query = """
                UPDATE clones
                    SET task=?, status=?, task_name=?, timestamp=?
                    WHERE PATH IN (
                        SELECT path FROM clones WHERE status=? LIMIT 1
                    )
            """
            timestamp = self._get_time_()
            cursor.execute(
                reservation_query,
                (task, Clone.INUSE, task_name, timestamp, Clone.FREE))
            self.connection.commit()

            # Check that it could be reserved
            reserved_clone = cursor.execute(
                'SELECT * FROM clones WHERE ' +
                'task=? AND task_name=? AND timestamp=?',
                (task, task_name, timestamp)).fetchone()
            if not reserved_clone:
                raise RosterError('No available clones')
            return unmarshall(reserved_clone)

    def free_clone(self, clone, task):
        clone.task = task
        clone.status = Clone.FREE
        self[clone.path] = clone

    def add(self, path, task, task_name):
        if path in self:
            raise RosterError('Clone is already in the roster.')
        self._clean_old_clones()
        with self.__cursor() as cursor:
            result = cursor.execute(
                'SELECT count(*) FROM clones').fetchone()[0]
            if result == self.max_clone_limit:
                clones = cursor.execute('SELECT * FROM clones').fetchall()
                raise MaxClonesLimitReached(
                    'Max limit of clones reached: ' +
                    'result: %s, max: %s, select: %s' % (
                        result, self.max_clone_limit, clones))
        clone = Clone(path, Clone.INUSE, task, task_name, 0)
        self[clone.path] = clone
        return self[clone.path]

    def get_available(self):
        with self.__cursor() as cursor:
            result = [
                unmarshall(elem) for elem in cursor.execute(
                    'SELECT * FROM clones WHERE status=?', (Clone.FREE,))
            ]
            return result

    def get_not_available(self):
        with self.__cursor() as cursor:
            result = [
                unmarshall(elem) for elem in cursor.execute(
                    'SELECT * FROM clones WHERE status=?', (Clone.INUSE,))
            ]
            return result
