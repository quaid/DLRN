# -*- coding: utf-8 -*-

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import mock
import sh

from dlrn.tests import base

from dlrn import db
from dlrn import repositories
from dlrn import utils


class TestsWithData(base.TestCase):
    def setUp(self):
        super(TestsWithData, self).setUp()
        self.session = db.getSession(new=True)
        utils.loadYAML(self.session, './dlrn/tests/samples/commits_1.yaml')


def _aux(*x):
    return 'origin (fetch) url'


@mock.patch.object(sh.Command, '__call__', autospec=True)
class TestRefreshRepo(base.TestCase):

    def test_clone_if_not_cloned(self, sh_mock):
        repositories.refreshrepo('url', 'path', branch='branch')
        expected = [mock.call(sh.git.clone, 'url', 'path'),
                    mock.call(sh.git.fetch, 'origin'),
                    mock.call(sh.git.checkout, '-f', 'branch'),
                    mock.call(sh.git.reset, '--hard', 'origin/branch'),
                    mock.call(sh.git.log, '--pretty=format:%H %ct', '-1')]
        self.assertEqual(sh_mock.call_args_list, expected)

    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('shutil.rmtree', return_value=True)
    def test_dont_clone_if_cloned(self, path_mock, shutil_mock, sh_mock):
        repositories.refreshrepo('url', 'path', branch='branch')
        expected = [mock.call(sh.git, 'remote', '-v'),
                    mock.call(sh.git.clone, 'url', 'path'),
                    mock.call(sh.git.fetch, 'origin'),
                    mock.call(sh.git.checkout, '-f', 'branch'),
                    mock.call(sh.git.reset, '--hard', 'origin/branch'),
                    mock.call(sh.git.log, '--pretty=format:%H %ct', '-1')]
        self.assertEqual(sh_mock.call_args_list, expected)

    @mock.patch('os.path.exists', return_value=True)
    def test_dont_fetch_if_local_repo_exists(self, path_mock, sh_mock):
        repositories.refreshrepo('url', 'path', branch='branch', local=True)
        expected = [mock.call(sh.git.log, '--pretty=format:%H %ct', '-1')]
        self.assertEqual(sh_mock.call_args_list, expected)

    def test_clone_fetch_if_local_repo_missing(self, sh_mock):
        repositories.refreshrepo('url', 'path', branch='branch', local=True)
        expected = [mock.call(sh.git.clone, 'url', 'path'),
                    mock.call(sh.git.fetch, 'origin'),
                    mock.call(sh.git.checkout, '-f', 'branch'),
                    mock.call(sh.git.reset, '--hard', 'origin/branch'),
                    mock.call(sh.git.log, '--pretty=format:%H %ct', '-1')]
        self.assertEqual(sh_mock.call_args_list, expected)