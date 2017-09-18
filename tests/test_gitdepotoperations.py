        sh.git('clone',
        # It is there
            [],
        # It is not there
        self.assertEquals(
            ['deadbeef'],
            dcvs.check_changeset_availability(
                os.path.join(self.environment_path, 'repo1'),
                ['deadbeef']))

        # Multiple changesets
        self.assertEquals(
            ['deadbeef'],
            dcvs.check_changeset_availability(
                os.path.join(self.environment_path, 'repo1'),
                ['deadbeef', '52109e71fd7f16cb366acfcbb140d6d7f2fc50c9']))

        # All changesets
        self.assertEquals(
            [],
            dcvs.check_changeset_availability(
                os.path.join(self.environment_path, 'repo1'),
                [
                    'master',
                    'e3b1fc907ea8b3482e29eb91520c0e2eee2b4cdb',
                    '52109e71fd7f16cb366acfcbb140d6d7f2fc50c9',
                ]))

    def test_check_changeset_availability_on_workspace(self):
        dcvs = DepotOperations()
        # Remote repository
        self.add_content_to_repo(
            os.path.join(FIXTURE_PATH, 'fixture-2.git.bundle'),
            'remote')

        # Master cache
        master = dcvs.init_depot(
            os.path.join(self.environment_path, 'master'),
            parent=None,
            source=os.path.join(self.environment_path, 'remote'))

        # Workspace depot
        workspace1 = dcvs.init_depot(
            os.path.join(self.environment_path, 'workspace1'),
            parent=master,
            source=os.path.join(self.environment_path, 'master'))

        # There are commands that can accept files and changesets,
        # check that we are not mixing files with changesets when checking
        # available changesets in working copies
        open(os.path.join(workspace1.path, 'deadbeef'), 'w').close()
        self.assertEquals(
            ['deadbeef'],
            dcvs.check_changeset_availability(workspace1.path, ['deadbeef']))

    def test_master_grab_changesets(self):
        self.assertFalse(

    def _test_request_refresh(self, f):
        dcvs = DepotOperations()

        # Remote repository
        self.add_content_to_repo(
            os.path.join(FIXTURE_PATH, 'fixture-2.git.bundle'),
            'remote')

        # Master cache
        master = dcvs.init_depot(
            os.path.join(self.environment_path, 'master'),
            parent=None,
            source=os.path.join(self.environment_path, 'remote'))

        # Workspace depot
        workspace1 = dcvs.init_depot(
            os.path.join(self.environment_path, 'workspace1'),
            parent=master,
            source=os.path.join(self.environment_path, 'master'))

        self.assertTrue(workspace1.request_refresh({
            os.path.join(self.environment_path, 'remote'): ['my-branch1']}))

        f(workspace1)

        # Other remote repository with additional references
        self.add_content_to_repo(
            os.path.join(FIXTURE_PATH, 'fixture-4.git.bundle'),
            'other')

        with self.assertRaises(sh.ErrorReturnCode):
            sh.git('rev-parse', 'newbranch', _cwd=workspace1.path)

        self.assertTrue(workspace1.request_refresh({
            os.path.join(self.environment_path, 'other'): ['newbranch']}))

        self.assertEquals(
            sh.git('rev-parse', 'newbranch', _cwd=workspace1.path).strip(),
            "a277468c9cc0088ba69e0a4b085822d067e360ff")

    def test_request_refresh_git_workspace_clean(self):
        self._test_request_refresh(lambda w: None)

    def test_request_refresh_git_dirty_workspace(self):
        def taint(workspace):
            f = open(os.path.join(workspace.path, 'test1.txt'), 'w')
            f.write('taint!')
            f.close()
        self._test_request_refresh(taint)

    def test_request_refresh_git_untracked_file(self):
        def untracked(workspace):
            f = open(os.path.join(workspace.path, 'untracked.txt'), 'w')
            f.write('untracked!')
            f.close()
        self._test_request_refresh(untracked)

    def test_request_refresh_git_detached_workspace(self):
        def detach(workspace):
            sh.git('checkout', detach=True, _cwd=workspace.path)
        self._test_request_refresh(detach)

    def test_request_refresh_git_all_dirty_workspace(self):
        def taint_all(workspace):
            f = open(os.path.join(workspace.path, 'test1.txt'), 'w')
            f.write('taint!')
            f.close()
            f = open(os.path.join(workspace.path, 'untracked.txt'), 'w')
            f.write('untracked!')
            f.close()
            sh.git('checkout', detach=True, _cwd=workspace.path)
        self._test_request_refresh(taint_all)

    def test_request_refresh_not_existing_reference(self):
        dcvs = DepotOperations()

        # Remote repository
        self.add_content_to_repo(
            os.path.join(FIXTURE_PATH, 'fixture-2.git.bundle'),
            'remote')

        # Master cache
        master = dcvs.init_depot(
            os.path.join(self.environment_path, 'master'),
            parent=None,
            source=os.path.join(self.environment_path, 'remote'))

        # Workspace depot
        workspace1 = dcvs.init_depot(
            os.path.join(self.environment_path, 'workspace1'),
            parent=master,
            source=os.path.join(self.environment_path, 'master'))

        with self.assertRaises(sh.ErrorReturnCode):
            sh.git('rev-parse', 'notexists', _cwd=workspace1.path)

        self.assertFalse(workspace1.request_refresh({
            os.path.join(self.environment_path, 'remote'): ['notexists']}))