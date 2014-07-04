#!/usr/bin/env python
"""
Copyright 2014 Tuenti Technologies S.L.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import sys

from repoman.repository import repository_factory, RepositoryError

repo_kind   = sys.argv[0]
repo_path   = sys.argv[1]
repo_branch = sys.argv[2]

try:
    repo = repository_factory(repo_path, repo_kind)
    # ...
    repo.update(repo_branch)
    print repo.branch()
    # argv[2]
    print repo.parents()
    #[( < repoman.hg.repository.Repository at 0x48e3050 >,
    # '24356',
    # '0ce743b0620667737ea3aa1fa4e23c058c54f1a9',
    # '',
    # 'my-branch',
    # 'John Smith',
    # 'Fixing some bugs',
    # datetime.datetime(2014, 7, 18, 16, 34, 55),
    # '1405694095.0-7200')]
    print [str(changeset) for changeset in repo.get_revset()]
    #['bbcab718e05c', '0ce743b06206', '4c5df773e745', '6718ecce7892',
    # '6e7ec03d4f4a', 'a6e2d1910944', '6b4bcb0371c7', '37516d5ea67d',
    # '5507d2d336a4', 'ee6b1e8ccacd', 'f7bed42c52d7', 'a41be3ff8e68',
    # 'dbbacd1a0fef', '519a27d48baf', 'cb2c09b55aa3']
    print list(repo.tags())
    # ['v0.1', 'v0.2', 'v0.3', 'v0.4', 'v0.4.1', 'v0.5.0', ...
    repo.tag('example')
    print list(repo.tags())
    # ['example', 'v0.1', 'v0.2', 'v0.3', 'v0.4', 'v0.4.1', 'v0.5.0', ...
    repo.push()
    # ...
except RepositoryError as e:
    print "There was an error in an operation in repo: %s" % e


