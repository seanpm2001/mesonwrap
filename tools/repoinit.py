#!/usr/bin/env python3

# Copyright 2015 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This script is used to initialise a Github repo to be
used as a basis for a Wrap db entry. Also calculates a basic
upstream.wrap."""

import argparse
import datetime
import git
import hashlib
import os
import shutil
import sys
import urllib.request

import environment

upstream_templ = '''[wrap-file]
directory = %s

source_url = %s
source_filename = %s
source_hash = %s
'''

readme = '''This repository contains a Meson build definition for project {reponame}.

For more information please see http://mesonbuild.com.
'''


mit_license = '''Copyright (c) {year} The Meson development team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''


class GitFile:

    def __init__(self, filename, file, index):
        self.filename = filename
        self.file = file
        self.index = index

    def __enter__(self):
        return self.file.__enter__()

    def __exit__(self, type, value, traceback):
        self.file.__exit__(type, value, traceback)
        self.index.add([self.filename])


class RepoBuilder:

    def __init__(self, name, path=None, homepage=None, organization=None):
        self.name = name
        try:
            self.repo = git.Repo(path)
            self.origin = self.repo.remote('origin')
        except git.InvalidGitRepositoryError:
            if homepage is None:
                raise ValueError('homepage is required')
            gh = environment.Github()
            mesonbuild = gh.get_organization(organization)
            description = 'Meson build definitions for %s' % name
            ghrepo = mesonbuild.create_repo(name, description=description, homepage=homepage)
            self.repo = git.Repo.init(path)
            with self.open('readme.txt', 'w') as ofile:
                ofile.write(readme.format(reponame=name))
            with self.open('LICENSE.build', 'w') as ofile:
                ofile.write(mit_license.format(year=datetime.datetime.now().year))
            self.commit = self.repo.index.commit('Create repository for project %s' % name)
            self.origin = self.repo.create_remote('origin', ghrepo.ssh_url)
            self.origin.push(self.repo.head.ref.name)

    def open(self, path, mode='r'):
        abspath = os.path.join(self.repo.working_dir, path)
        f = open(abspath, mode)
        if f.writable():
            return GitFile(path, f, self.repo.index)
        return f

    @staticmethod
    def _get_hash(url):
        with urllib.request.urlopen(zipurl) as r:
            data = r.read()
        h = hashlib.sha256()
        h.update(data)
        return h.hexdigest()

    def init_version(self, version):
        branch = self.repo.create_head(version)
        self.origin.push(branch)

    def create_version(self, version, zipurl, filename, directory, ziphash=None, base=None):
        # TODO use provide interface for this function
        if ziphash is None:
            ziphash = self._get_hash(zipurl)
        self.repo.head.reference = self.repo.create_head(version, commit=base)
        assert not self.repo.head.is_detached
        self.repo.head.reset(index=True, working_tree=True)
        with self.open('upstream.wrap', 'w') as ofile:
            ofile.write(upstream_templ % (directory, zipurl, filename, ziphash))
        self.repo.index.add(['upstream.wrap'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('name')
    parser.add_argument('--directory')
    parser.add_argument('--version')
    parser.add_argument('--homepage')
    parser.add_argument('--test', action='store_true')
    args = parser.parse_args()
    organization = 'mesonbuild-test' if args.test else 'mesonbuild'
    builder = RepoBuilder(name=args.name,
                          path=args.directory,
                          homepage=args.homepage,
                          organization=organization)
    if args.version:
        builder.init_version(args.version)
