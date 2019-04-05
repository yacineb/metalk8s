# coding: utf-8


"""Provides container image construction.

The images are built from a local Dockerfile.
Then, they are tagged and optionally saved on the disk (compressed).

If the image is not saved in the build tree, a dummy empty file is created to
keep track of it.

All of these actions are done by a single task.
"""


import operator
import re
from pathlib import Path
from typing import Any, Dict, List, Match, Optional, Union

from doit.exceptions import TaskError # type: ignore

from buildchain import config
from buildchain import constants
from buildchain import coreutils
from buildchain import types

from . import image


class DockerFileDep:
    """A Dockerfile directive line creating external file dependencies."""

    def __init__(
        self,
        line_no: int,
        line_contents: str,
        line_match: Match[str],
        dockerfile_path: Path
    ):
        self.line_no = line_no
        self.line_contents = line_contents
        self.match = line_match
        self.dockerfile_path = dockerfile_path

    def expand_dep(self) -> List[Path]:
        """Expand the Dockerfile path dependency to regular files."""
        source = self.match.group('src')
        path = self.dockerfile_path.parent/Path(source)
        # Simple file
        if path.is_file():
            return [path]
        # Directory or `.`
        if path.is_dir():
            return [
                sub_path
                for sub_path in list(coreutils.ls_files_rec(path))
            ]
        # Globs - `*` or specific e.g. `*.py`, `*.repo`
        return [
            sub_path
            for sub_path in path.parent.glob(path.name)
            if sub_path.is_file()
        ]

    def format_errors(self, error_paths: List[Path]) -> List[str]:
        """Format paths in error with relevant information."""
        error_line = "l.{}: '{}' - missing {}"
        return [
            error_line.format(self.line_no, self.line_contents, error_path)
            for error_path in error_paths
        ]

    def verify(self, file_deps: List[Path]) -> List[str]:
        """Verify Dockerfile dependencies against external dependency list."""
        missing_deps = []
        for dependency in self.expand_dep():
            if not dependency in file_deps:
                missing_deps.append(dependency)
        return self.format_errors(missing_deps)


class LocalImage(image.ContainerImage):
    """A locally built container image."""
    def __init__(
        self,
        name: str,
        version: str,
        dockerfile: Path,
        destination: Path,
        save_on_disk: bool,
        build_args: Optional[Dict[str, Any]]=None,
        **kwargs: Any
    ):
        """Initialize a local container image.

        Arguments:
            name:         image name
            version:      image version
            dockerfile:   path to the Dockerfile
            destination:  where to save the result
            save_on_disk: save the image on disk?
            build_args:   build arguments

        Keyword Arguments:
            They are passed to `FileTarget` init method.
        """
        self._dockerfile = dockerfile
        self._save = save_on_disk
        self._build_args = build_args or {}
        kwargs.setdefault('file_dep', []).append(self.dockerfile)
        super().__init__(
            name=name, version=version,
            destination=destination,
            # We never load locally built images into containerd (until now…).
            for_containerd=False,
            **kwargs
        )

    dockerfile   = property(operator.attrgetter('_dockerfile'))
    save_on_disk = property(operator.attrgetter('_save'))
    build_args   = property(operator.attrgetter('_build_args'))
    dep_re = re.compile(
        r'^\s*(COPY|ADD)( --[^ ]+)* (?P<src>[^ ]+) (?P<dst>[^ ]+)\s*$'
    )

    def load_deps_from_dockerfile(self) -> List[DockerFileDep]:
        """Compute file dependencies from Dockerfile."""
        dep_keywords = ('COPY', 'ADD')

        with self.dockerfile.open('r', encoding='utf8') as dockerfile:
            docker_lines = dockerfile.readlines()

        dep_lines = [
            (pos, line.strip(), self.dep_re.match(line.strip()))
            for (pos, line) in enumerate(docker_lines, 1)
            if line.strip().startswith(dep_keywords)
        ]
        deps = []
        for (pos, line, match) in dep_lines:
            if match is None:
                continue
            deps.append(
                DockerFileDep(
                    line_no=pos,
                    line_contents=line,
                    line_match=match,
                    dockerfile_path=self.dockerfile
                )
            )
        return deps

    def check_dockerfile_dependencies(self) -> Union[TaskError, bool]:
        """Verify task file dependencies against computed file dependencies."""
        error_tplt = (
            'Missing Dockerfile file dependencies in'
            ' build target: \n{dockerfile}:\n\t{errors}'
        )
        deps = self.load_deps_from_dockerfile()
        errors: List[str] = []
        for dep in deps:
            errors.extend(dep.verify(self.file_dep))
        if errors:
            error_message = error_tplt.format(
                dockerfile=self.dockerfile,
                errors='\n\t'.join(errors)
            )
            return TaskError(msg=error_message)
        return True

    @property
    def task(self) -> types.TaskDict:
        def show(_task: types.Task) -> str:
            return '{cmd: <{width}} {image}'.format(
                cmd='IMG BUILD', width=constants.CMD_WIDTH, image=self.tag,
            )

        task = self.basic_task
        task.update({
            'title': show,
            'doc': 'Build {} container image.'.format(self.name),
            'actions': self._build_actions(),
        })
        return task

    def _build_actions(self) -> List[types.Action]:
        """Build a container image locally."""
        actions: List[types.Action] = []

        actions.append((self.check_dockerfile_dependencies, [], {}))

        build_cmd = [
            config.DOCKER, 'build',
            '--tag', self.tag,
            '--file', self.dockerfile,
        ]
        for arg, value in self.build_args.items():
            build_cmd.extend(['--build-arg', '{}={}'.format(arg, value)])
        build_cmd.append(self.dockerfile.parent)
        actions.append(build_cmd)

        # If a destination is defined, let's save the image there.
        if self.save_on_disk:
            filepath = self.uncompressed_filename
            actions.append([
                config.DOCKER, 'save', self.tag, '-o', str(filepath)
            ])
            actions.append((coreutils.gzip, [filepath], {}))
        else:
            # If we don't save the image, at least we touch a file
            # (to keep track of the build).
            actions.append((coreutils.touch, [self.destination], {}))
        return actions
