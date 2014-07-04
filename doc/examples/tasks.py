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

from repoman import depot_manager

repo_kind = sys.argv[0]
repo_url = sys.argv[1]

manager = depot_manager.DepotManager(repo_kind=repo_kind)

# Process 1, 2 & 3 are sequentially chained

# Process 1
depot = manager.give_me_depot('task_id', 'Owner task name') 
try:
        depot.request_refresh({ repo_url: ['master'] })
        print list(depot.repository.tags())
        depot.repository.tag('example')
        print list(depot.repository.tags())
except:
        manager.free_depot(depot, 'task_id')
             
# Process 2
depot = manager.give_me_depot_from_path(depot.path) 
try:
        print list(depot.repository.tags()) # Example tag is there
finally:
        manager.free_depot(depot, 'task_id')

# Process 3
depot = manager.give_me_depot('task_id2', 'Other owner task name') 

try:
        depot.request_refresh({ repo_url: ['master'] })
        print list(depot.repository.tags()) # Example tag is NOT there
finally:
        manager.free_depot(depot, 'task_id2')
