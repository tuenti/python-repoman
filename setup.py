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

from setuptools import setup, find_packages

from repoman import __version__ as version

github_url = 'https://github.com/tuenti/python-repoman'


def read_description():
    with open('README.rst') as fd:
        return fd.read()

setup(
    name='repoman-scm',
    version=version,
    description="Library and tools to manage pools of code repositories",
    long_description=read_description(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Topic :: Software Development :: Version Control',
    ],
    keywords='DVCS git mercurial',
    author='Tuenti Technologies S.L.',
    author_email='sre@tuenti.com',
    url=github_url,
    download_url='{0}/tarball/v{1}'.format(github_url, version),
    license='Apache Software License',
    packages=find_packages(exclude=['tests']),
    install_requires=[
        'ordereddict',
        'pygit2',
        'python-hglib',
    ],
    data_files=[
        ('', ['README.rst']),
    ],
)
