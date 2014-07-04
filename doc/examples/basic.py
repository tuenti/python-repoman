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

from repoman import depot_manager

repo_kind = sys.argv[0]
repo_url = sys.argv[1]

manager = depot_manager.DepotManager(repo_kind=repo_kind)
 
depot = manager.give_me_depot('task_id', 'Owner task name')

try:
    depot.request_refresh({ repo_url: ['master'] })

    # ...
    print list(depot.repository.tags())
    # ['v0.1', 'v0.2', 'v0.3', 'v0.4', 'v0.4.1', 'v0.5.0', ...
    depot.repository.tag('example')
    print list(depot.repository.tags())
    # ['example', 'v0.1', 'v0.2', 'v0.3', 'v0.4', 'v0.4.1', 'v0.5.0', ...
    # ...
finally:
    manager.free_depot(depot, 'task_id')
