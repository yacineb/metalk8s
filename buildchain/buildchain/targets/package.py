# coding: utf-8


"""Provides local packages construction.

This modules provides several services:
- create the directory for the packages
- generate the .meta from the .spec
- download the source files
- build a SRPM from the source files

Note that for now, it only works for CentOS 7 x86_64.

            self.make_package_directory(),
            self.generate_meta(),
            self.get_source_files(),
            self.build_srpm(),

Overview;

┌─────┐     ┌───────────────┐     ┌────────────────┐     ┌────────────┐
│mkdir│────>│ generate .meta│────>│ download source│────>│ build SRPM │
└─────┘     └───────────────┘     └────────────────┘     └────────────┘
"""


import os
import operator
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Sequence

from buildchain import constants
from buildchain import types
from buildchain import utils
from buildchain.docker_command import DockerRun

from . import base
from . import directory
from . import image


SOURCE_URL_PATTERN = re.compile(r'^Source\d+:\s+(?P<url>.+)$')


class Package(base.Target, base.CompositeTarget):
    """A RPM software package for CentOS 7."""

    MKDIR_TASK_NAME = 'pkg_mkdir'
    SUFFIX = 'el7'

    def __init__(
        self,
        basename: str,
        name: str,
        version: str,
        build_id: int,
        sources: Sequence[Path],
        builder: image.ContainerImage,
        **kwargs: Any
    ):
        """Initialize the package.

        Arguments:
            basename: basename for the sub-tasks
            name:     package name
            version:  package version
            build_id: package build ID
            sources:  package source files
            builder:  docker image used to build the package

        Keyword Arguments:
            They are passed to `Target` init method.
        """
        self._name = name
        self._version = version
        self._build_id = build_id
        self._sources = [
            self.rootdir/'SOURCES'/filename for filename in sources
        ]
        self._builder = builder
        super().__init__(
            basename='{base}:{name}'.format(base=basename, name=self.name),
            **kwargs
        )

    name     = property(operator.attrgetter('_name'))
    version  = property(operator.attrgetter('_version'))
    build_id = property(operator.attrgetter('_build_id'))
    sources  = property(operator.attrgetter('_sources'))
    builder  = property(operator.attrgetter('_builder'))

    @property
    def rootdir(self) -> Path:
        """Package root directory."""
        return constants.PKG_ROOT/self._name

    @property
    def srcdir(self) -> Path:
        """Package source directory."""
        return self.rootdir/'SOURCES'

    @property
    def spec(self) -> Path:
        """.spec file path."""
        return constants.ROOT/'packages'/'{}.spec'.format(self.name)

    @property
    def meta(self) -> Path:
        """.meta file path."""
        return self.rootdir/'{}.meta'.format(self.name)

    @property
    def srpm(self) -> Path:
        """SRPM path."""
        fmt = '{pkg.name}-{pkg.version}-{pkg.build_id}.{pkg.SUFFIX}.src.rpm'
        return constants.PKG_ROOT/fmt.format(pkg=self)

    @property
    def execution_plan(self) -> List[types.TaskDict]:
        return [
            self.make_package_directory(),
            self.generate_meta(),
            self.get_source_files(),
            self.build_srpm(),
        ]

    def make_package_directory(self) -> types.TaskDict:
        """Create the package's directory."""
        task = self.basic_task
        mkdir = directory.Mkdir(directory=self.rootdir).task
        task.update({
            'name': self.MKDIR_TASK_NAME,
            'doc': 'Create directory for {}.'.format(self.name),
            'title': mkdir['title'],
            'actions': mkdir['actions'],
            'uptodate': mkdir['uptodate'],
            'targets': mkdir['targets'],
        })
        return task

    def generate_meta(self) -> types.TaskDict:
        """Generate the .meta file for the package."""
        task = self.basic_task
        task.update({
            'name': 'pkg_rpmspec',
            'actions': [self._rpmspec],
            'doc': 'Generate {}.meta'.format(self.name),
            'title': lambda task: utils.title_with_target1('RPMSPEC', task),
            'targets': [self.meta],
        })
        task['file_dep'].extend([self.spec, self.builder.destination])
        task['task_dep'].append('{}:{}'.format(self.basename,
                                               self.MKDIR_TASK_NAME))
        return task

    def get_source_files(self) -> types.TaskDict:
        """Download the source files to build the package."""
        targets = [self.srcdir]
        targets.extend(self.sources)
        actions = directory.Mkdir(directory=self.srcdir).task['actions']
        actions.append(self._download_sources)
        task = self.basic_task
        task.update({
            'name': 'pkg_get_source',
            'actions': actions,
            'doc': 'Download source files for {}.'.format(self.name),
            'title': lambda task: utils.title_with_target1('GET_SRC', task),
            'targets': targets,
        })
        task['file_dep'].append(self.meta)
        task['task_dep'].append('{}:{}'.format(self.basename,
                                               self.MKDIR_TASK_NAME))
        return task

    def build_srpm(self) -> types.TaskDict:
        """Build the SRPM for the package."""
        env = {
            'SPEC': self.spec.name,
            'SRPM': self.srpm.name,
            'SOURCES': ' '.join(map(operator.attrgetter('name'), self.sources)),
        }

        buildsrpm = DockerRun(
            command=['/entrypoint.sh', 'buildsrpm'],
            builder=self.builder,
            environment=env,
            tmpfs={'/home/build': '', '/var/tmp': ''},
            mounts=self._get_buildsrpm_mounts(self.srpm.parent),
            read_only=True
        )

        task = self.basic_task
        task.update({
            'name': 'pkg_srpm',
            'actions': [(buildsrpm, [], {})],
            'doc': 'Build {}'.format(self.srpm.name),
            'title': lambda task: utils.title_with_target1('BUILD SRPM', task),
            'targets': [self.srpm],
            # Prevent Docker from polluting our output.
            'verbosity': 0,
        })
        task['file_dep'].extend([self.spec, self.builder.destination])
        task['file_dep'].extend(self.sources)
        task['task_dep'].append('{}:{}'.format(self.basename,
                                               self.MKDIR_TASK_NAME))
        return task

    def _rpmspec(self) -> None:
        """Run the `rpmspec` command inside a container and save the output."""
        container_spec = '/rpmbuild/SPECS/{}'.format(self.spec.name)
        mount_string = 'type=bind,source={src},destination={dst},ro'.format(
            src=self.spec, dst=container_spec
        )
        rpmspec_cmd = [
            config.DOCKER, 'run',
            '--hostname', 'build',
            '--mount', mount_string,
            '--read-only',
            '--rm',
            self.builder.tag,
            'su', '-l', 'build', '-c',
            'rpmspec -P {}'.format(shlex.quote(container_spec)),
        ]
        stdout = subprocess.check_output(rpmspec_cmd)
        with open(self.meta, 'w', encoding='utf-8') as fp:
            fp.write(stdout.decode('utf-8'))

    def _buildsrpm_cmd(self) -> List[str]:
        """Return the command to run `buildsrpm` inside a container."""
        extra_env = {
            'SPEC': self.spec.name,
            'SRPM': self.srpm.name,
            'SOURCES': ' '.join(map(operator.attrgetter('name'), self.sources)),
        }
        cmd = list(constants.BUILDER_BASIC_CMD)
        for var, value in extra_env.items():
            cmd.extend(['--env', '{}={}'.format(var, value)])
        for mount_string in self._get_buildsrpm_mounts(self.srpm.parent):
            cmd.extend(['--mount', mount_string])
        cmd.extend([
            '--read-only',
            self.builder.tag,
            '/entrypoint.sh', 'buildsrpm'
        ])
        return cmd

    def _download_sources(self) -> None:
        """Return a list of actions to download the source files."""
        for srcfile, url in self._get_source_files_urls().items():
            with urllib.request.urlopen(url) as conn:
                with open(srcfile, 'wb') as fp:
                    fp.write(conn.read())

    def _get_source_files_urls(self) -> Dict[Path, str]:
        """Extract source file URLs from .meta file."""
        urls = {}
        sourcefiles = {src.name for src in self.sources}
        with open(self.meta, 'r', encoding='utf-8') as fp:
            for line in fp:
                match = SOURCE_URL_PATTERN.match(line)
                if not match:
                    continue
                url = match.group('url')
                filename = _file_from_url(url)
                if filename in sourcefiles:
                    sourcefiles.remove(filename)
                    urls[self.srcdir/filename] = url
        if sourcefiles:
            raise Exception('URL not found for source files: {}'.format(
                ', '.join(sourcefiles)
            ))
        return urls

    def _get_buildsrpm_mounts(self, srpm_dir: Path) -> List[types.Mount]:
        """Return the list of container mounts required by `buildsrpm`."""
        mounts = [
            # .spec file
            DockerRun.bind_ro_mount(
                source=self.spec,
                target='/rpmbuild/SPECS/{}'.format(self.spec.name),
            ),
            # SRPM directory.
            DockerRun.bind_mount(
                source=srpm_dir,
                target='/rpmbuild/SRPMS',
            ),
            # rpmlint configuration file
            DockerRun.RPMLINTRC_MOUNT
        ]

        # Source files.
        for source in self.sources:
            mounts.append(
                DockerRun.bind_ro_mount(
                    source=source,
                    target='/rpmbuild/SOURCES/{}'.format(source.name)
                )
            )
        return mounts


def _file_from_url(url: str) -> str:
    """Get filename from a URL."""
    path = urllib.parse.urlparse(url).path
    return urllib.parse.unquote(os.path.basename(path))
