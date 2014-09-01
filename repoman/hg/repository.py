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

import datetime
import logging
import os
import re
import time

from repoman.changeset import Changeset
from repoman.hg import hglibext as hglib
from repoman.reference import Reference
from repoman.repo_indexer import RepoIndexerError
from repoman.repository import Repository as BaseRepo, \
    RepositoryError, MergeConflictError

logger = logging.getLogger(__name__)


class Repository(BaseRepo):
    """
    Models a Mercurial repository
    """
    NEW_REMOTE_HEAD_LITERAL = "creates new remote head"
    MERGING_WITH_ANCESTOR_LITERAL = "working directory ancestor has no effect"

    class with_repo(object):
        """
        .. py:decorator:: with_repo

           Decorator for methods in this class that use a repository.

           It adds a parameter after "self" with the repository, so, a method
           defined like this:

           .. code-block:: python

               @with_repo()
               def method(self, repo, a, b):
                   ...

           Will have to be called as:

           .. code-block:: python

               hg_repository.method(a, b)


           And will receive self as usual, and a repository instantiated
           with the path of the hg_repository object.
        """
        DEFAULT_EXCEPTIONS = (
            hglib.error.CommandError,
            hglib.error.ServerError,
            hglib.error.ResponseError
        )

        def __init__(self, error_message=None, exceptions=DEFAULT_EXCEPTIONS):
            self.error_message = error_message
            self.exceptions = exceptions

        def __call__(self, f):
            def wrapped(they, *args, **kwargs):
                try:
                    with hglib.open(they.path) as repo:
                        return f(they, repo, *args, **kwargs)
                except self.exceptions as e:
                    if self.error_message:
                        arguments = ", ".join(str(arg) for arg in args)
                        arguments += ", " + str(kwargs)
                        logger.exception("%s (%s)" % (
                            self.error_message, arguments))
                        raise RepositoryError(self.error_message + str(e))
                    else:
                        logger.exception(e)
                        raise RepositoryError(e)
            return wrapped

    def __getitem__(self, key):
        """
        Implements access thorugh [] operator for changesets

        :param key: item to get, could be branch name, tag name or revision
                    hash
        :type string
        """
        # Checking if key is a branch
        if self.branch_exists(key):
            key = self._get_branch_tip(key).hash
        # Checking if key is a tag
        elif self.tag_exists(key):
            key = self._get_tag_changeset(key).hash

        return self.get_revset(cs_from=key).next()

    def _new_changeset_object(self, changeset_info):
        """
        Return a new Changeset with the provided info

        :param changeset_info: data needed to build a Changeset object, it
               is a tuple that hglib returns
        :type tuple
        """
        return Changeset(self, changeset_info)

    def get_changeset_branches(self, changeset):
        """ Inherited method
        :func:`~repoman.repository.Repository.get_changeset_branches`
        """
        return changeset.branches

    @with_repo()
    def branch(self, repo, branch_name):
        """ Inherited method
        :func:`~repoman.repository.Repository.branch`
        """
        repo.branch(branch_name, force=True)
        return self._new_branch_object(branch_name)

    @with_repo(error_message="Error tagging revision")
    def tag(self, repo, name, revision=None, message=None):
        """ Inherited method
        :func:`~repoman.repository.Repository.tag`
        """
        repo.update()
        repo.tag(name, rev=revision, message=message, force=True,
                 user=self.signature.user)

    @with_repo()
    def strip(self, repo, changeset):
        """ Inherited method
        :func:`~repoman.repository.Repository.strip`
        """
        repo.strip(changeset.hash)

    @with_repo(error_message="Error getting branch")
    def branch_exists(self, repo, branch_name):
        """ Inherited method
        :func:`~repoman.repository.Repository.branch_exists`
        """
        if branch_name == repo.branch():
            return True
        return branch_name in [b[0] for b in repo.branches(closed=True)]

    @with_repo(error_message="Error getting tag")
    def tag_exists(self, repo, tag_name):
        """ Inherited method
        :func:`~repoman.repository.Repository.tag_exists`
        """
        repo = hglib.open(self.path)
        return tag_name in [t[0] for t in repo.tags()]

    @with_repo(error_message="Error getting branch")
    def get_branch(self, repo, branch_name=None):
        """ Inherited method
        :func:`~repoman.repository.Repository.get_branch`
        """
        if not branch_name:
            repo = hglib.open(self.path)
            branch_name = repo.branch()
        else:
            if not self.branch_exists(branch_name):
                raise RepositoryError("Branch %s does not exist in repo %s"
                                      % (branch_name, self.path))
        return self._new_branch_object(branch_name)

    def exterminate_branch(self, branch_name, repo_origin, repo_dest):
        """ Inherited method
        :func:`~repoman.repository.Repository.exterminate_branch`
        """
        self.terminate_branch(branch_name, repo_origin, repo_dest)

    def terminate_branch(self, branch_name, repo_origin, repo_dest):
        """ Inherited method
        :func:`~repoman.repository.Repository.terminate_branch`
        """
        repo = None
        try:
            with hglib.open(self.path) as repo:
                try:
                    repo.pull(repo_origin, branch=branch_name)
                except hglib.error.CommandError:
                    # Ignore this error, the branch could be only local thus
                    # the pull can safely fail
                    pass
                repo.update(branch_name, clean=True)
                repo.commit(
                    message=str(self.message_builder.close_branch(
                        branch=branch_name
                    )),
                    user=self.signature.user,
                    closebranch=True)

                parents = repo.parents()
                self.push(repo_origin, repo_dest,
                          self._new_changeset_object(parents[0]))
        except hglib.error.CommandError as e:
            if 'can only close branch heads' in e.err:
                logger.exception(
                    "Cannot close %s branch, it's already closed" %
                    branch_name)
                return
            logger.exception("Error closing the release branch %s: %s" % (
                branch_name, e))
            raise RepositoryError(e)

    def get_revset(self, cs_from=None, cs_to=None,
                   branch=None, keyword=None, date=None):
        """ Inherited method
        :func:`~repoman.repository.Repository.get_revset`
        """
        repo = None
        if cs_from:
            if cs_to:
                revset = "%s::%s" % (cs_from, cs_to)
            else:
                revset = cs_from
        else:
            revset = None

        with hglib.open(self.path) as repo:
            try:
                # If a revset is given, not heavy, not needed to split
                # the log in chunks
                if revset:
                    # Adding cs_from because it's not added due to the :: usage
                    result = [
                        self._new_changeset_object(
                            repo.log(revrange=cs_from)[0])
                    ]
                    for revision in repo.log(revrange=revset, branch=branch):
                        changeset = self._new_changeset_object(revision)
                        if changeset not in result:
                            result.append(changeset)
                    for changeset in result:
                        yield changeset
                else:
                    chunk_size = 15
                    first = repo.log(limit=1, branch=branch)[0]
                    previous_hash = None
                    first_hash = first.node
                    revrange = None

                    while previous_hash != first_hash:
                        changesets = repo.log(limit=chunk_size, branch=branch,
                                              revrange=revrange)
                        previous_hash = first_hash
                        if len(changesets) > chunk_size:
                            first = changesets.pop(-1)
                            first_hash = first.node
                            revrange = "%s:%s" % (first_hash, chunk_size)
                        while changesets:
                            cs = self._new_changeset_object(changesets.pop(0))
                            yield cs

            except hglib.error.CommandError as e:
                logger.exception(e)
                raise RepositoryError(e)

    @with_repo(error_message="Error pulling")
    def pull(self, repo, remote=None, revision=None, branch=None):
        """ Inherited method
        :func:`~repoman.repository.Repository.pull`
        """
        if revision:
            repo.pull(source=remote, rev=revision)
        elif branch:
            repo.pull(source=remote, branch=branch)
        else:
            repo.pull(source=remote)

    @with_repo()
    def push(self, repo, orig, dest, rev=None, ref_name=None):
        """ Inherited method
        :func:`~repoman.repository.Repository.push`
        """
        def update_repo(repo, orig):
            command_config = ["--config", "extensions.rebase="]
            command = ["pull", "--rebase", orig, "--tool=false"]
            repo.rawcommand(command_config + command)
            return self._new_changeset_object(repo.tip()).hash

        # Push method should always be ready for the case where there is a new
        # remote head
        push_succeded = False
        last_exception = None
        MAX_RETRIES = 15
        if not rev:
            rev_hash = "tip"
        else:
            rev_hash = rev.hash
        logger.info("Pushing %s from %s to %s" % (rev_hash, self.path, dest))

        retries = 0
        while not push_succeded and retries < MAX_RETRIES:
            try:
                retries += 1
                push_result = repo.push(
                    dest=dest, rev=rev_hash, newbranch=True)
                if not push_result:
                    logger.info(
                        "hglib.push returned False in %s, retrying..." %
                        self.path)
                    last_exception = "hglib.push returned False..."
                    time.sleep(1)
                    rev_hash = update_repo(repo, orig)
                else:
                    push_succeded = True
            except hglib.error.CommandError as e:
                last_exception = e
                logger.exception("Push didn't work, why?")
                logger.debug(e.__str__())
                if self.NEW_REMOTE_HEAD_LITERAL not in str(e):
                    logger.error("Error pushing: %s" % e)
                    raise RepositoryError("Error pushing: %s" % e)
                logger.debug("Error pushing, maybe two heads...")
                try:
                    rev_hash = update_repo(repo, orig)
                except hglib.error.CommandError as ex:
                    # Conflicts??
                    logger.exception("Error merging!")
                    raise RepositoryError(
                        "Error merging: %s (%s)" % (e, ex))
        if not push_succeded:
            raise RepositoryError(
                "Five attempts for pushing failed: %s" %
                last_exception)
        else:
            return self[rev_hash]

    @with_repo()
    def update(self, repo, branch):
        """ Inherited method
        :func:`~repoman.repository.Repository.update`
        """
        repo.update(branch, clean=True)
        parents = repo.parents()
        return self._new_changeset_object(parents[0])

    def merge(self, local_branch=None, other_rev=None,
              other_branch_name=None, dry_run=False):
        """ Inherited method
        :func:`~repoman.repository.Repository.merge`
        """
        log_message = 'Initiating merge. Local branch: %s. ' + \
                      'Other branch: %s@%s.'
        logger.debug(log_message %
                     (local_branch, other_branch_name, other_rev))
        if not other_rev:
            raise RepositoryError("No revision to merge with specified")
        if local_branch and not type(local_branch) == Reference:
            raise RepositoryError(
                "local_branch (%s) parameter must be a Reference " +
                "instead of %s" % (local_branch, type(local_branch)))

        commit = None
        repo = None
        try:
            repo = hglib.open(self.path)
            if local_branch:
                repo.update(rev=local_branch.name, clean=True)
            else:
                local_branch = self._new_branch_object(repo.branch())
            try:
                repo.merge(rev=other_rev.hash, tool='false')
            except hglib.error.CommandError as e:
                if dry_run:
                    # Restoring state
                    repo.update(rev=local_branch.name, clean=True)
                # Error can mean either no need to commit, or conflicts
                basic_error_msg = \
                    'Found an error during merge. local: %s, remote: %s@%s' % \
                    (local_branch.name, other_branch_name, other_rev.hash)
                if "merging" in str(e) and "failed" in str(e):
                    logger.exception("Merging failed with conflicts:")
                    raise MergeConflictError(e[2])
                elif self.MERGING_WITH_ANCESTOR_LITERAL in e.err:
                    # Ugly way to detect this error, but the e.ret is not
                    # correct
                    logger.info("Nothing to merge, already merged: %s" % e.err)
                    return None
                elif e.ret == -1:
                    logger.exception(basic_error_msg)
                    if 'response expected' in e.err:
                        raise RepositoryError(e.out)
                    else:
                        # Unknown error
                        logger.exception(e)
                        raise RepositoryError(e)
                else:
                    # Merge failed because it was not needed
                    return None

            if not dry_run:
                commit_message = self.message_builder.merge(
                    other_branch=other_branch_name or "",
                    other_revision=other_rev.shorthash,
                    local_branch=local_branch.name,
                    local_revision=local_branch.get_changeset().shorthash
                )
                commit = repo.commit(message=str(commit_message),
                                     user=self.signature.user)
                return self._new_changeset_object(repo.tip())
            else:
                # Restoring state
                repo.update(rev=local_branch.name, clean=True)
                return None

        except hglib.error.CommandError as e:
            logger.exception(
                "Error merging branch %s into %s" % (
                    other_rev.hash, local_branch.name))
            # Undoing the merge to get rid of partial merges
            repo.update(clean=True)
            raise RepositoryError(e)
        finally:
            if repo:
                repo.close()
        return commit

    def add(self, files):
        """ Inherited method
        :func:`~repoman.repository.Repository.add`
        """
        if not isinstance(files, list):
            files = [files]
        with hglib.open(self.path) as repo:
            for file in files:
                if not repo.add(os.path.join(self.path, file)):
                    raise RepositoryError("Could not add file '%s'" % file)

    @with_repo()
    def commit(self, repo, message, custom_parent=None,
               allow_empty=False):
        """ Inherited method
        :func:`~repoman.repository.Repository.commit`

        Advise: allow_empty not commit on non-changed working copy,
        but it won't raise an error.
        """
        def branch_exists():
            return any(repo.branch() == b[0] for b in repo.branches())
        def has_modifications():
            return repo.status(added=True,
                               modified=True,
                               removed=True,
                               deleted=False,
            )
        if not allow_empty and not has_modifications() and branch_exists():
            logger.info("Nothing to commit, repository clean")
            return None
        repo.commit(
            message=str(self.message_builder.commit(message)),
            user=self.signature.user
        )
        return self._new_changeset_object(repo.tip())

    @with_repo()
    def parents(self, repo):
        """ Inherited method
        :func:`~repoman.repository.Repository.parents`
        """
        repo = hglib.open(self.path)
        try:
            return [self._new_changeset_object(cs) for cs in repo.parents()]
        except TypeError:
            raise RepositoryError("Working copy for repo %s has no parents "
                                  "(is it bare?)" % self.path)

    @with_repo()
    def tip(self, repo):
        """ Inherited method
        :func:`~repoman.repository.Repository.tip`
        """
        repo = hglib.open(self.path)
        return self._new_changeset_object(repo.tip())

    @with_repo(error_message="Error getting ancestor")
    def get_ancestor(self, repo, cs1, cs2):
        """ Inherited method
        :func:`~repoman.repository.Repository.get_ancestor`
        """
        if not cs1 or not cs2:
            error = "Error getting ancestor, either \
            rev1 or rev2 are None: %s , %s" % (cs1, cs2)
            logger.error(error)
            raise RepositoryError(error)
        rev1 = cs1.hash
        rev2 = cs2.hash
        logger.debug("Getting ancestor for: %s, %s" % (rev1, rev2))
        ancestor_rev = repo.log(
            revrange="ancestor('%s', '%s')" % (rev1, rev2))[0]
        return self._new_changeset_object(ancestor_rev)

    def _get_branch_tip(self, branch_name):
        """
        Returns the changeset being the branch tip

        :param branch_name: name of the branch
        :type string
        """
        with hglib.open(self.path) as repo:
            try:
                tip = repo.log(revrange="'%s'" % branch_name)[0]
                return self._new_changeset_object(tip)
            except hglib.error.CommandError as e:
                # Checking if it's a branch recently created, if so, returning
                # current changeset (due to hglib.log does not work with not
                # commited branches)
                if repo.branch() == branch_name:
                    return self._new_changeset_object(repo.parents()[0])
                logger.exception(
                    "Error getting branch '%s' tip: %s" % (branch_name, e))
                raise RepositoryError(e)

    def _get_tag_changeset(self, tag_name):
        """
        Gets the changeset that correspond to the given tag

        :param tag_name: name of the tag
        :type string
        """
        with hglib.open(self.path) as repo:
            try:
                repo = hglib.open(self.path)
                rev = [t[2] for t in repo.tags() if t[0] == tag_name][0]
                return self._new_changeset_object(self[rev])
            except (IndexError, hglib.error.CommandError) as e:
                logger.exception("Eror getting tag '%s': %s" % (tag_name, e))
                raise RepositoryError(e)

    @with_repo()
    def is_merge(self, repo, changeset_hash):
        """ Inherited method
        :func:`~repoman.repository.Repository.is_merge`
        """
        return bool(repo.log(revrange=changeset_hash, onlymerges=True))

    @with_repo()
    def get_parents(self, repo, changeset_hash):
        """ Inherited method
        :func:`~repoman.repository.Repository.get_parents`
        """
        log = repo.log(revrange="parents('%s')" % changeset_hash)
        return [self._new_changeset_object(cs) for cs in log]

    def get_branches(self, active=False, closed=False):
        """ Inherited method
        :func:`~repoman.repository.Repository.get_branches`
        """
        if self._repo_indexer and not active and not closed:
            try:
                branches = self._repo_indexer.get_branches()
                if branches:
                    for branch in branches:
                        yield self._new_branch_object(branch)
            except RepoIndexerError:
                logger.exception(
                    "Could not retrieve branches from RepoIndexer, " +
                    "polling repository...")
        if self.path:
            logger.warning(
                "Could not retrieve branches from RepoIndexer, " +
                "polling repository...")
            for branch in self._get_sorted_branches(active, closed):
                yield branch

    def _get_sorted_branches(self, active=False, closed=False):
        """
        Get the underlaying repository branches, sorted by name

        :param active: indicates active branches
        :type active: bool
        :param closed: indicates closed branches
        :type closed: bool
        """
        # TODO implement sorted branches with repo indexers
        try:
            with hglib.open(self.path) as repo:
                branches = repo.branches(active, closed)
                branches.sort(key=lambda branch: branch[0], reverse=True)
                for branch in branches:
                    yield self._new_branch_object(branch[0])
        except (hglib.error.CommandError, hglib.error.ServerError) as e:
            logger.exception(e)
            raise RepositoryError(e)

    @with_repo()
    def compare_branches(self, repo, revision_to_check_hash, branch_base):
        """ Inherited method
        :func:`~repoman.repository.Repository.compare_branches`
        """
        log = repo.log(revrange="ancestors('%s') and not ancestors('%s')" % (
            revision_to_check_hash, branch_base))
        return [self._new_changeset_object(cs) for cs in log]

    @with_repo(error_message="Error executing raw command")
    def rawcommand(self, repo, command):
        """
        .. deprecated:: 0.5.1 Not allowed in interface

        :param command: command to execute
        :type string
        """
        return repo.rawcommand(command)

    def get_changeset_tags(self, changeset_hash):
        """Inherited method
        :func:`~repoman.repository.Repository.get_changeset_tags`
        """
        cs = self[changeset_hash]
        return cs.tags.split()

    @with_repo(error_message="Error getting tags")
    def tags(self, repo):
        """ Inherited method
        :func:`~repoman.repository.Repository.tags`
        """
        return repo.tags()

    def _changeset_indexer2repo(self, indexer_changeset):
        """
        Converts an indexer changeset to an Changeset
        """
        fixed_date = re.match("(.*)[\+|\-]",
                              indexer_changeset.date).groups(0)[0]
        # The date format provided by fecru is: 2013-05-09T15:11:44+02:00
        cs_datetime = datetime.datetime.strptime(
            fixed_date, "%Y-%m-%dT%H:%M:%S")
        changeset_values = (
            None,
            indexer_changeset.csid,
            indexer_changeset.tags,
            indexer_changeset.branch,
            indexer_changeset.author,
            indexer_changeset.comment,
            cs_datetime,
            None,
            indexer_changeset.parent,
            indexer_changeset.children
        )
        return self._new_changeset_object(changeset_values)
