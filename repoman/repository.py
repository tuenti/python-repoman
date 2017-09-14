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

import copy
import logging

from repoman.commitmessage import DefaultCommitMessageBuilder
from repoman.reference import Reference
from repoman.repo_indexer import RepoIndexerError
from repoman.signature import Signature

logger = logging.getLogger(__name__)


class RepositoryError(Exception):
    """ Any error relative to repositories.
    """
    def __init__(self, exception):
        super(RepositoryError, self).__init__(exception)


class MergeConflictError(RepositoryError):
    """ There was any conflict while merging.
    """
    def __init__(self, exception):
        super(MergeConflictError, self).__init__(exception)


def repository_factory(repo_path,
                       repo_kind=None,
                       repo_indexer=None,
                       commit_message_builder=None):
    """ Factory to create Repository objects.
    It will try to choose the correct repository kind.

    :param repo_path: Path to the repository working copy.
    :type repo_path: string
    :param repo_kind: Repository class to be used.It will be determined
         automatically if None.
    :type repo_kind: string
    :param repo_indexer: Indexer to be used, if any.
         See :doc:`repoman.repo_indexers`.
    :type repo_indexer: string
    :param commit_message_builder: Constructor to generate the commit message.
        It will use
        :py:class:`repoman.commitmessage.DefaultCommitMessageBuilder` if None.
    :type commit_message_builder: repoman.commitmessage
    """
    repo_kind = repo_kind or Repository._autodiscover_repo_type(repo_path)
    try:
        mod = __import__("repoman.%s.repository" % (repo_kind),
                         fromlist=['Repository'])
        ConcreteRepository = getattr(mod, 'Repository')

        return ConcreteRepository(repo_path,
                                  repo_indexer,
                                  commit_message_builder)
    except:
        raise NotImplementedError("Repository module "
                                  "repoman.%s.repository" % (repo_kind))


class Repository(object):
    """
    Models a repo and provides changesets, operations and such.

    ABSTRACT class. Do not create instances of this class.
    Use :func:`repository_factory` to get the proper Repository implementation.
    """
    @staticmethod
    def get_repository(repo_path,
                       repo_kind=None,
                       repo_indexer=None,
                       commit_message_builder=None):
        """
        .. deprecated:: 0.5.1
           Use :func:`repository_factory` instead.
        """
        return repository_factory(repo_path,
                                  repo_kind,
                                  repo_indexer,
                                  commit_message_builder)

    def __init__(self, repo_path, repo_indexer=None, message_builder=None,
                 signature=None):
        self.path = repo_path
        self._repo_indexer = repo_indexer
        self.message_builder = message_builder or DefaultCommitMessageBuilder()
        self._signature = signature

    @property
    def signature(self):
        if not self._signature:
            self._signature = Signature()
        return self._signature

    @signature.setter
    def signature(self, signature):
        self._signature = signature

    def do_as(self, signature):
        """
        Convenience methods to do operations with an specific signature.

        To be used like:

          repository.do_as(other_signature).tag('foo')

        :param signature: Signature to use for the operation.
        :type signature: :func:`repoman.signature.Signature`
        """
        clone = copy.copy(self)
        clone.signature = signature
        return clone

    def _new_branch_object(self, branch_name):
        """
        Return a new branch reference

        :param branch_name: Name of the branch to be retrieved.
        :type branch_name: string
        :returns: Branch object
        :rtype: :func:`repoman.reference.Reference`
        """
        return Reference(branch_name, self)

    def _new_tag_object(self, tag_name):
        """
        Return a new tag reference

        :param tag_name: Tag to look for.
        :type tag_name: string
        :returns: Branch object
        :rtype: :func:`repoman.reference.Reference`
        """
        return Reference(tag_name, self)

    def _new_changeset_object(self, changeset_info):
        raise NotImplementedError("Abstract method")

    def __getitem__(self, key):
        raise NotImplementedError("Abstract method")

    def branch(self, branch_name):
        """
        Creates a branch in the repository.
        """
        raise NotImplementedError("Abstract method")

    def tag(self, tag_name, revision=None, message=None):
        """
        Creates a tag in the repository
        """
        raise NotImplementedError("Abstract method")

    def strip(self, changeset):
        """
        Strips the given changeset

        :param changesets: list of changeset objects
        :type changesets: list of Changeset
        """
        raise NotImplementedError("Abstract method")

    def get_changeset_branches(self, changeset):
        """
        Gets the branches associated to the given changeset

        :param changeset: Changeset to look for
        :type Changeset: string
        """
        raise NotImplementedError("Abstract method")

    def branch_exists(self, branch_name):
        """
        Return if the given branch exists in the repository

        :param branch_name: name of the branch
        :type branch_name: string
        """
        raise NotImplementedError("Abstract method")

    def tag_exists(self, tag_name):
        """
        Return if the given tag exists in the repository

        :param tag_name: name of the tag
        :type tag_name: string
        """
        raise NotImplementedError("Abstract method")

    def tip(self):
        raise NotImplementedError("Abstract method")

    def get_ancestor(self, cs1, cs2):
        """
        Returns a changeset being the first ancestor of both changesets
        provided

        :param cs1: First changeset
        :type cs1: string
        :param cs2: Second changeset
        :type cs2: string
        :returns: ancestor changeset
        :rtype: string
        """
        raise NotImplementedError("Abstract method")

    def terminate_branch(self, branch_name, repo_origin, repo_dest):
        """
        Remove the branch locally and remotely

        :param branch_name: name of the branch
        :type branch_name: string
        :param repo_origin: repository source
        :type repo_origin: string
        :param repo_dest: repository destination
        :type repo_dest: string
        """
        raise NotImplementedError("Abstract method")

    def get_branch(self, branch_name=None):
        """
        Get Branch object.
        If no branch_provided, current branch is returned
        Does not need to swith to the branch

        :param branch_name: name of the branch
        :type branch_name: string
        :returns: Branch object
        :rtype: :func:`repoman.reference.Reference`
        """
        raise NotImplementedError("Abstract method")

    def get_revset(self, cs_from=None, cs_to=None,
                   branch=None, keyword=None, date=None):
        """
        Returns an iterator for the changesets in the repository that
        correspond to the given parameters

        :param cs_from: starting changeset. If this is the only parameter,
                        a list with just this changeset will be returned
        :type cs_from: string
        :param cs_to: ending changeset. If specified, all changesets between
                      cs_from and cs_to will be returned, both included
        :type cs_to: string
        :param branch: branch that returned changesets should belong to.
                       Filter out changesets not belonging to that branch
        :type branch:
        :returns:
        :rtype:
        """
        raise NotImplementedError("Abstract method")

    def compare_branches(self, revision_to_check, branch_base):
        """
        This function returns the changesets that would be included
        in branch_base_name if you merge revision_to_check_hash into
        branch_base_name.
        The first param must be a changeset hash and the second a branch name.

        :param revision_to_check_hash:
        :type revision_to_check_hash: string
        :param branch_base_name:
        :type branch_base_name: string
        """
        raise NotImplementedError("Abstract method")

    def get_branches(self, active=False, closed=False):
        """
        Returns the list of branches.
        Firstly, it tries to do so using the included repo indexer,
        if not possible, it tries to retrieve them from repository itself.
        If either active or closed are true, it directly search in the
        repository.

        :param active: indicates to get active branches
        :type active: bool
        :param closed: indicates to get closed branches
        :type closed: bool
        """
        raise NotImplementedError("Abstract method")

    def _changeset_indexer2repo(self, changeset):
        raise NotImplementedError("Abstract method")

    def get_branch_tip(self, branch_name):
        """
        Returns the changeset being the branch tip checking the indexers first
        and then the repository itself

        :param branch_name: name of the branch
        :type branch_name: string
        """
        if self._repo_indexer:
            try:
                log = self._repo_indexer.get_branch_log(branch_name, limit=1)
                tip = log[0]
                return self._changeset_indexer2repo(tip)
            except RepoIndexerError:
                logger.info("Could not retrieve branch log from RepoIndexer,\
                                  polling repository...")

        return self._get_branch_tip(branch_name)

    def _get_branch_tip(self, branch_name):
        raise NotImplementedError("Abstract method")

    def _get_tag_changeset(self, tag_name):
        raise NotImplementedError("Abstract method")

    def is_merge(self, changeset_hash):
        """
        Returns if the changeset is a merge.

        :param changeset_hash: hash identifying the changeset
        :type changeset_hash: string
        """
        raise NotImplementedError("Abstract method")

    def pull(self, remote=None, revision=None, branch=None):
        """
        Gets changesets from remote repo into local repo
        If neither branch nor revision are specified, everything will be
        pulled.

        :param remote: URL of the remote repo, where to pull from
        :type remote: string
        :param revision: revision to pull
        :type revision: string
        :param branch: branch to pull
        :type branch: string
        :raises: :func:`~RepositoryError`
        """
        raise NotImplementedError("Abstract method")

    def push(self, orig, dest, rev=None, ref_name=None):
        """
        Pushes changesets to remote repo from local repo. It will also pull,
            merge and commit if two remote heads are found

        :param orig: URL of repo to pull from if two heads found
        :type orig: string
        :param dest: URL of the remote repo, where to push to
        :type dest: string
        :param rev: changeset object to push
        :type rev: changeset object
        :param ref_name: reference name to push
        :type ref_name: string
        :raises: :func:`~RepositoryError`
        """
        raise NotImplementedError("Abstract method")

    def commit(self, message, custom_parent=None, allow_empty=False):
        """
        Commits changes in current working copy. This will implement a
        'hg commit' behaviour, adding all modified files if necessary and
        ignoring removed files.

        :param message: commit message
        :type message: string
        :param custom_parent: by default the commit parent is the repo head
                             with this parameter you can specify a custom one
                             like when there was a fastforward merge and you
                             want to perform a commit anyway
        :type custom_parent: pygit2.Oid
        :param allow_empty: allows empty commits
        :type allow_empty: bool
        """
        raise NotImplementedError("Abstract method")

    def parents(self):
        """
        Returns a list of the parents of current working copy revision
        """
        raise NotImplementedError("Abstract method")

    def get_parents(self, changeset_hash):
        """
        Returns the list of parents of the given changeset

        :param changeset_hash: hash identifying the changeset
        :type changeset_hash: string
        """
        raise NotImplementedError("Abstract method")

    def get_changeset_tags(self, changeset_hash):
        """
        Gets the tags of the given changeset

        :param changeset_hash:
        :type changeset_hash: string
        :returns: the tags of the given changeset
        :rtype: list of strings
        """
        cs = self[changeset_hash]
        return cs.tags.split()

    def update(self, branch):
        """
        Updates working copy to the specified branch.

        :param branch: ref to update working copy to, a branch name or a
            revision hash
        :type branch: string
        """
        raise NotImplementedError("Abstract method")

    def add(self, files):
        """
        Adds a file or a list of files to the repo to be tracked

        :param files: file or files to add
        :type files: string or list of strings
        :raises: :py:exc:`RepositoryError`
        """
        raise NotImplementedError("Abstract method")

    def merge(self, local_branch=None, other_rev=None,
              other_branch_name=None, dry_run=False):
        """
        Merges two revision and commits the result

        :param local_branch: branch object to merge to - optional, if None,
            it takes current branch
        :type Reference: repoman.git.gitchangeset
        :param other_rev: changeset object to merge with - mandatory
        :type Changeset: repoman.git.gitchangeset
        :param other_branch_name: name of the branch the other_rev changeset
                                  belongs to
        :type other_branch_name: string
        :param dry_run: option to simulate the merge, it assuer the repository
                        is restored to the previous state
        :type dry_run: bool
        """
        raise NotImplementedError("Abstract method")

    def rawcommand(self, command):
        raise NotImplementedError("Abstract method")

    def __cmp__(self, other):
        return cmp(self.path, other.path)

    def tags(self):
        """
        Just returns the tags
        """
        raise NotImplementedError("Abstract method")

    def exterminate_branch(self, branch_name, repo_origin, repo_dest):
        """
        Exterminating the branch, apart from terminate it, this also
        removes it from remote

        :param branch_name: name of the branch
        :type branch_name: string
        :param repo_origin: repository source
        :type repo_origin: string
        :param repo_dest: repository destination
        :type repo_dest: string
        :param message: Message used in commit message (ignored)
        :type message: string
        """
        raise NotImplementedError("Abstract method")

    ###########################
    # Higher level operations #
    ###########################

    def full_merge_and_push(self, base_branch, changeset_to_merge_hash,
                            branch_to_merge_name, origin,
                            destination, ref_name=None):
        """
        Perform a full merge and push.

        :param base_branch: branch where the changeset will be merged into
        :type base_branch: string
        :param changeset_to_merge_hash: changeset to merge into base_branch
        :type changeset_to_merge_hash: string
        :param branch_to_merge_name: name of the branch to merge
        :type branch_to_merge_name: string
        :param origin: repository origin
        :type origin: string
        :param destination: repository destination
        :type destination: string
        :param ref_name: reference name to push
        :type ref_name: string
        """
        self.pull(origin, base_branch)
        self.pull(origin, changeset_to_merge_hash)

        changeset_to_merge = self[changeset_to_merge_hash]
        merge_changeset = self.merge(local_branch=self.get_branch(base_branch),
                                     other_rev=changeset_to_merge,
                                     other_branch_name=branch_to_merge_name)
        if merge_changeset:
            merge_changeset = self.push(origin, destination, merge_changeset,
                                        ref_name)
        return merge_changeset

    @staticmethod
    def _autodiscover_repo_type(repo_path):
        raise NotImplementedError
