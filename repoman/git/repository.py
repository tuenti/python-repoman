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

import re
import os.path
import logging
import datetime
import sh
from repoman.repository import Repository as BaseRepo, \
    RepositoryError, MergeConflictError
from repoman.changeset import Changeset
from repoman.merge import MergeStrategy
from repoman.reference import Reference

logger = logging.getLogger(__name__)


class GitCmd(object):
    def __init__(self, path):
        self.path = path

    def __call__(self, *args, **kwargs):
        try:
            cmd = sh.git(_cwd=self.path, _tty_out=False, *args, **kwargs)
        except sh.ErrorReturnCode as e:
            raise RepositoryError(
                "'%s' failed in %s: %s" % (e.full_cmd, self.path, e))

        if '_iter' in kwargs and kwargs['_iter'] != None:
            return cmd

        # For convenience, remove last new line of command output
        return re.sub('(\n|\n\r)$', '', cmd.stdout.decode('utf-8'))


class GitMerge(MergeStrategy):
    def __init__(self, *args, **kwargs):
        super(GitMerge, self).__init__(*args, **kwargs)
        self._git = GitCmd(self.repository.path)

    def _validate_local_branch(self):
        if self.local_branch is None:
            self.local_branch = self.repository.get_branch()
            return

        if not isinstance(self.local_branch, Reference):
            raise RepositoryError(
                    "In merge, local branch must be a Reference object")

        self._git('checkout', self.local_branch.name)

    def perform(self):
        self._validate_local_branch()

        self._git('merge', '--no-ff', '--no-commit',
                  self.other_rev.hash,
                  _ok_code=[0, 1])

        conflicts = self._git('diff', name_only=True, diff_filter='U').split()

        if conflicts:
            raise MergeConflictError("Conflicts found: merging %s failed" %
                                     ", ".join(conflicts))

    def abort(self):
        self._git('merge', '--abort')

    def commit(self):
        if len(self._git('status', porcelain=True, _iter=True)) == 0:
            return None
        commit_message = self.repository.message_builder.merge(
            other_branch=self.other_branch_name,
            other_revision=self.other_rev.shorthash,
            local_branch=self.local_branch.name,
            local_revision=self.local_branch.get_changeset().shorthash
        )
        author = str(self.repository.signature)
        self._git("commit", m=commit_message, author=author)
        return self.repository.tip()


class GitMergeFastForward(GitMerge):
    def __init__(self, *args, **kwargs):
        super(GitMergeFastForward, self).__init__(*args, **kwargs)
        self._ff_merged = False

    def perform(self):
        self._validate_local_branch()

        try:
            self._git('merge', '--ff-only', self.other_rev.hash)
            self._ff_merged = True
        except:
            # TODO: Is this what we want? log something in any case
            super(GitMergeFastForward, self).perform()

    def abort(self):
        if self._ff_merged:
            self._git('reset', 'HEAD^', hard=True)
            return
        super(GitMergeFastForward, self).abort()

    def commit(self):
        if not self._ff_merged:
            return super(GitMergeFastForward, self).commit()
        return self.repository.tip()


class GitMergeSquash(GitMerge):
    def __init__(self, *args, **kwargs):
        super(GitMergeSquash, self).__init__(*args, **kwargs)

    def perform(self):
        self._validate_local_branch()

        self._git('merge', '--squash',
                  self.other_rev.hash,
                  _ok_code=[0, 1])

        conflicts = self._git('diff', name_only=True, diff_filter='U').split()

        if conflicts:
            raise MergeConflictError("Conflicts found: merging %s failed" %
                                     ", ".join(conflicts))


class GitMergeRebase(GitMerge):
    def __init__(self, *args, **kwargs):
        super(GitMergeSquash, self).__init__(*args, **kwargs)

    def perform(self):
        self._validate_local_branch()

        self._git('merge', '--rebase',
                  self.other_rev.hash,
                  _ok_code=[0, 1])

        conflicts = self._git('diff', name_only=True, diff_filter='U').split()

        if conflicts:
            raise MergeConflictError("Conflicts found: merging %s failed" %
                                     ", ".join(conflicts))

class Repository(BaseRepo):
    """
    Models a Git Repository
    """
    def __init__(self, *args, **kwargs):
        super(Repository, self).__init__(*args, **kwargs)
        self._git = GitCmd(self.path)

    def __getitem__(self, key):
        """
        Implements access thorugh [] operator for changesets
        key -- changeset hash or branch name
        """
        return self._new_changeset_object(key)

    def _new_changeset_object(self, refname):
        """
        Return a new Changeset object with the provided info
        """
        tags = ' '.join(self.get_changeset_tags(refname))
        info, body = self._git("log",
                               "-1",
                               "--pretty=%H,%ct,%cn%n%B",
                               refname).split("\n", 1)
        sha1, committer_time, committer_name = info.split(",", 2)

        initial_values = [
            None,  # Local changeset that does not exist in GIT
            sha1,
            tags,
            None,
            committer_name,
            body,
            datetime.datetime.utcfromtimestamp(float(committer_time)),
        ]

        c = Changeset(self, tuple(initial_values))
        return c

    def get_changeset_branches(self, changeset):
        """ Inherited method
        :func:`~repoman.repository.Repository.get_changeset_branches`
        """
        branches = self.get_branches()
        branch_contains = lambda branch: self.get_ancestor(
            changeset, branch.get_changeset()).hash == changeset.hash
        cs_branches = map(lambda b: b.name, filter(branch_contains, branches))
        return cs_branches

    def branch(self, name):
        """Inherited method :func:`~repoman.repository.Repository.branch` """
        self._git("checkout", "-B", name)
        return self._new_branch_object(name)

    def tag(self, name, revision=None, message=None):
        """Inherited method :func:`~repoman.repository.Repository.tag` """
        if not revision:
            revision = 'HEAD'
        args = ["tag", name, revision]
        if message:
            args += ["-m", message]
            args += ["-a"]
        self._git(*args)
        return self._new_tag_object(name)

    def strip(self, changeset):
        """Inherited method :func:`~repoman.repository.Repository.strip` """
        self._git('reset', '--hard', '%s^' % changeset.hash)

    def branch_exists(self, branch_name):
        """Inherited method
        :func:`~repoman.repository.Repository.branch_exists`
        """
        for branch in self.get_branches():
            if branch.name == branch_name:
                return True
        return False

    def tag_exists(self, tag_name):
        """Inherited method :func:`~repoman.repository.Repository.tag_exists`
        """
        return tag_name in self.tags()

    def tip(self):
        """Inherited method :func:`~Repository.tip` """
        return self['HEAD']

    def get_ancestor(self, cs1, cs2):
        """Inherited method :func:`~repoman.repository.Repository.get_ancestor`
        """
        if not cs1 or not cs2:
            error = "Error getting ancestor, " +\
                "either rev1 or rev2 are None: %s , %s" % (cs1, cs2)
            logger.error(error)
            raise RepositoryError(error)
        return self[self._git('merge-base', cs1.hash, cs2.hash)]

    def get_branches(self, active=False, closed=False):
        """Inherited method :func:`~repoman.repository.Repository.get_branches`
        """
        branches = list([
            branch_name.strip() for branch_name in self._git(
                "for-each-ref",
                "refs/heads",
                format="%(refname:short)",
                _iter=True)
        ])
        try:
            # Add current branch even if it doesn't have commits
            current = self.get_branch()
            if current.name not in branches:
                branches.append(current.name)
        except:
            # TODO: Better handle error cases here, related to
            # HEAD not existing
            pass
        return [self._new_branch_object(branch) for branch in branches if
                branch != 'HEAD']

    def exterminate_branch(self, branch_name, repo_origin, repo_dest):
        """Inherited method
        :func:`~repoman.repository.Repository.exterminate_branch`
        """
        if not self.terminate_branch(branch_name, repo_origin, repo_dest):
            return
        # Deleting remotely
        self.push(repo_origin, repo_dest, rev='', ref_name=branch_name)

    def terminate_branch(self, branch_name, repo_origin, repo_dest):
        """Inherited method
        :func:`~repoman.repository.Repository.terminate_branch`
        """
        if not self.branch_exists(branch_name):
            return False

        current = None
        try:
            current = self._git('rev-parse', '--abbrev-ref', 'HEAD')
        except:
            pass

        if current != None and current == branch_name:
            self._git('checkout', '--detach')

        self._git('branch', '-D', branch_name)

        return True

    def get_branch(self, branch_name=None):
        """Inherited method
        :func:`~repoman.repository.Repository.get_branch`
        """
        if not branch_name:
            branch_name = self._git("rev-parse", "--abbrev-ref", "HEAD")
        else:
            if not self.branch_exists(branch_name):
                raise RepositoryError('Branch %s does not exist in repo %s'
                                      % (branch_name, self.path))

        return self._new_branch_object(branch_name)

    def get_revset(self, cs_from=None, cs_to=None, branch=None):
        """Inherited method
        :func:`~repoman.repository.Repository.get_revset`
        """

        if branch:
            b = self.get_branch(branch)
            if cs_to is None:
                cs_to = b.get_changeset().hash
            else:
                cs_to = self.get_ancestor(self[cs_to], b.get_changeset()).hash

        if not cs_to:
            cs_to = 'HEAD'

        if not cs_from:
            cs = self._git(
                'log', '--pretty=%H', '--reverse',
                cs_to,
                _iter=True)
        else:
            try:
                # If cs_from is not an ancestor of cs_to we shouldn't output
                # anything
                self._git('merge-base', '--is-ancestor', cs_from, cs_to)
            except:
                return

            rev_range = "%s..%s" % (cs_from, cs_to)
            cs = self._git(
                'log', '--pretty=%H', '--reverse',
                rev_range,
                _iter=True)
            # When printing git log ranges, it doesn't include the root one
            yield self._new_changeset_object(cs_from)

        for c in cs:
            yield self._new_changeset_object(c.strip())

    def pull(self, remote, revision=None, branch=None):
        """Inherited method
        :func:`~repoman.repository.Repository.pull`
        """
        git_dir = os.path.join(
            self.path,
            sh.git('rev-parse', '--git-dir', _cwd=self.path).strip())
        git = GitCmd(git_dir)

        refspec = '+refs/*:refs/*'
        if branch != None:
            refspec = '+refs/heads/%s:refs/heads/%s' % (branch, branch)

        logger.debug("Executing git -c core.bare=true fetch %s %s",
                     remote, refspec)
        output = git('-c',
                     'core.bare=true',
                     'fetch',
                     remote,
                     refspec,
                     _err_to_out=True)
        logger.debug("Output:\n%s", output)
        self._clean()

    def push(self, orig, dest, rev=None, ref_name=None, force=False):
        """Inherited method
        :func:`~repoman.repository.Repository.push`
        """
        all_tags_option = "--tags"

        if rev is None and ref_name is None:
            # Push everything
            refspec = "refs/*:refs/*"
        elif rev is None:
            refspec = "%s:%s" % (ref_name, ref_name)
        elif ref_name is None:
            raise RepositoryError(
                "When pushing, revision specified but not reference name")
        else:
            if self.tag_exists(ref_name):
                # We don't know what this ref is in remote,
                # but here it is a tag
                ref_name = "refs/tags/%s" % ref_name
                all_tags_option = ""
            else:
                # In any other case, we assume it is a branch
                ref_name = "refs/heads/%s" % ref_name
            refspec = "%s:%s" % (rev, ref_name)

        if all_tags_option:
            self._git("push", dest, refspec, all_tags_option, f=force)
        else:
            self._git("push", dest, refspec, f=force)
        return self.tip()

    def _merge(self, local_branch=None, other_rev=None,
               other_branch_name=None, dry_run=False, strategy=GitMerge):
        merge = strategy(self, local_branch, other_rev, other_branch_name)
        merge.perform()
        if dry_run:
            merge.abort()
            return None
        return merge.commit()

    def merge(self, local_branch=None, other_rev=None,
              other_branch_name=None,
              dry_run=False):
        """Inherited method
        :func:`~repoman.repository.Repository.merge`
        """
        return self._merge(local_branch, other_rev, other_branch_name, dry_run,
                           strategy=GitMerge)

    def merge_fastforward(self, local_branch=None, other_rev=None,
                          other_branch_name=None,
                          dry_run=False):
        return self._merge(local_branch, other_rev, other_branch_name, dry_run,
                           strategy=GitMergeFastForward)

    def merge_squash(self, local_branch=None, other_rev=None,
                     other_branch_name=None,
                     dry_run=False):
        return self._merge(local_branch, other_rev, other_branch_name, dry_run,
                           strategy=GitMergeSquash)

    def merge_rebase(self, local_branch=None, other_rev=None,
                    other_branch_name=None,
                    dry_run=False):
        return self._merge(local_branch, other_rev, other_branch_name, dry_run,
                           strategy=GitMergeRebase)

    def add(self, files):
        if isinstance(files, str):
            files = [files]
        if len(files) > 0:
            self._git("add", *files)

    def commit(self, message, custom_parent=None,
               allow_empty=False):
        """Inherited method
        :func:`~repoman.repository.Repository.commit`
        """
        status = self._git('status', porcelain=True, _iter=True)

        if not status and not custom_parent and not allow_empty:
            logger.debug("Nothing to commit, repository clean")
            return None

        # TODO: If custom_parent is deprecated, we can remove this code
        # and use git commit directly instead of write-tree and commit-tree
        parents = []
        for head in ('HEAD', custom_parent, 'MERGE_HEAD'):
            try:
                parent = self[head].hash
                if parent not in parents:
                    parents.append(parent)
            except:
                pass

        parent_args = []
        for parent in parents:
            parent_args += ['-p', parent]

        # TODO: It currently mimics previous implementation, not sure if
        # this is what we want. It automatically adds modified files only, with
        # other statuses it may generate an empty commit even if it was not
        # allowed.
        allow_empty = True
        modified = []

        for s in status:
            status, path = s.strip().split(maxsplit=1)
            path = path.replace('"', '')
            if status == 'M':
                modified.append(path)
        self.add(modified)

        tree = self._git('write-tree').strip()

        env = os.environ.copy().update({
            'GIT_AUTHOR_NAME': self.signature.user,
            'GIT_AUTHOR_EMAIL': self.signature.email,
            'GIT_COMMITTER_NAME': self.signature.user,
            'GIT_COMMITTER_EMAIL': self.signature.email,
        })

        commit = self._git('commit-tree',
                           tree,
                           '-m',
                           message,
                           *parent_args,
                           _env=env).strip()
        self._git('reset', '--hard', commit)
        return self.tip()

    def update(self, ref):
        """Inherited method
        :func:`~repoman.repository.Repository.update`
        """
        self._clean()
        self._git("checkout", ref)
        return self.tip()

    def _clean(self):
        """
        Clean up the working copy. More information about Git clean up:
        http://stackoverflow.com/questions/22620393/git-remove-local-changes
        """
        try:
            # Clean index to avoid unmerged files
            self._git('read-tree', '--empty')
            self._git('reset', '--hard')
            self._git('clean', '-fdx')
        except Exception:
            logger.exception('The cache could not be correctly cleaned.'
                             ' Continuing')

    def _get_branch_tip(self, branch):
        """
        Returns the changeset being the branch tip

        :param branch: name of the branch
        :type string
        """
        sha1 = self._git("rev-parse", branch)
        return self[sha1]

    def get_changeset_tags(self, changeset_hash):
        """Inherited method
        :func:`~repoman.repository.Repository.get_changeset_tags`
        """
        ref_tags = [
            tag.split() for tag in
            # Error code can be 1 on empty output
            self._git("show-ref", "--tags", _ok_code=[0, 1]).split("\n")
            if tag
        ]

        ref_tags = filter(
            lambda ref_tag: ref_tag[0].startswith(changeset_hash),
            ref_tags)

        tag_reference_regexp = re.compile('^refs/tags/')
        return list(
            map(lambda ref_tag: tag_reference_regexp.sub('', ref_tag[1]),
                ref_tags)
        )

    def log_branch(self, revision_to_check_hash, branch_base_name):
        """
        returns the list of changesets included in branch_base_name from
        revision to check_hash
        (git log branch_base_name..revision_to_check_hash)
        """
        hashes = self._git(
            "log",
            "--pretty=%H",
            "%s..%s" % (branch_base_name, revision_to_check_hash)).split()

        return [self._new_changeset_object(h) for h in hashes]

    def compare_branches(self, branch_from, branch_to):
        """Inherited method
        :func:`~repoman.repository.Repository.compare_branches`
        """
        hashes = self._git("log", "--pretty=%H",
                           branch_from, "^%s" % branch_to).split()

        return [self._new_changeset_object(h) for h in hashes]

    def tags(self):
        """Inherited method
        :func:`~repoman.repository.Repository.tags`
        """
        return self._git('tag', '-l').split()

    def is_merge(self, changeset_hash):
        """Inherited method
        :func:`~repoman.repository.Repository.is_merge`
        """
        return len(self.get_parents(changeset_hash)) > 1

    def parents(self):
        """Inherited method
        :func:`~repoman.repository.Repository.parents`
        """
        return self.get_parents('HEAD')

    def get_parents(self, changeset_hash):
        """Inherited method
        :func:`~repoman.repository.Repository.get_parents`
        """
        parents = self._git("log",
                            "--pretty=%P",
                            "-1",
                            changeset_hash.strip()).split()
        return [self[cs.strip()] for cs in parents]

    def append_note(self, note, revision=None):
        """Inherited method :func:`~repoman.repository.Repository.append_note`
        """
        if not revision:
            revision = 'HEAD'
        args = ['notes', 'append', '-m', note, revision]
        self._git(*args)
        return self._git('notes', 'list', revision)

    def get_changeset_notes(self, revision=None):
        """Inherited method
        :func:`~repoman.repository.Repository.get_changeset_notes`
        """
        notes = []
        if not revision:
            revision = 'HEAD'
        raw_notes = self._git('notes', 'show', revision, _ok_code=[0, 1])
        notes = list(
            map(lambda n: n,
                filter(lambda n: len(n) > 0, raw_notes.split('\n')))
        )
        return notes

    def has_note(self, note, revision=None):
        """Inherited method :func:`~repoman.repository.Repository.has_note`
        """
        notes = self.get_changeset_notes(revision)
        return note in notes
