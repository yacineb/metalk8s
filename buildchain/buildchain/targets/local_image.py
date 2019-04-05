# coding: utf-8


"""Provides container image construction.

The images are built from a local Dockerfile.
Then, they are tagged and optionally saved on the disk (compressed).

If the image is not saved in the build tree, a dummy empty file is created to
keep track of it.

All of these actions are done by a single task.
"""


import operator
from pathlib import Path
from typing import Any, Dict, List, Optional

from buildchain import constants
from buildchain import coreutils
from buildchain import types
from buildchain.docker_command import DockerBuild

from . import image


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
        actions : List[types.Action] = []

        builder = DockerBuild(
            tag=self.tag,
            path=self.dockerfile.parent,
            dockerfile=self.dockerfile,
            buildargs=self.build_args
        )
        actions.append((builder, [], {}))

        # If a destination is defined, let's save the image there.
        if self.save_on_disk:
            filepath = self.uncompressed_filename
            actions.append(
                (self.save, [], {'save_path': filepath})
            )
            actions.append((coreutils.gzip, [filepath], {}))
        else:
            # If we don't save the image, at least we touch a file
            # (to keep track of the build).
            actions.append((coreutils.touch, [self.destination], {}))
        return actions
