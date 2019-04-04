# coding: utf-8

"""Provides Python commands for Docker Python client.

Supply callable objects with prepared configuration for use
with `doit`'s Python actions.
"""

import copy
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import docker                            # type: ignore
from docker.types import Mount           # type: ignore
import doit                              # type: ignore
from doit.exceptions import TaskError    # type: ignore

from buildchain import constants


DOCKER_CLIENT : docker.DockerClient = docker.from_env()


# The call method is not counter as a public method
# pylint: disable=too-few-public-methods
class BuildCommand:
    """Docker build callable"""

    def __init__(
        self,
        tag: str,
        path: Path,
        dockerfile: Path,
        args: Dict[str, Any]
    ):
        self.tag = tag
        self.path = str(path)
        self.dockerfile = str(dockerfile)
        self.args = args

    def __call__(self) -> Union[TaskError, bool]:
        try:
            DOCKER_CLIENT.images.build(
                tag=self.tag,
                path=self.path,
                dockerfile=self.dockerfile,
                buildargs=self.args
            )
        except (docker.errors.BuildError, docker.errors.APIError) as err:
            return TaskError(err)
        return True


# The call method is not counter as a public method
# pylint: disable=too-few-public-methods
class TagCommand:
    """Docker tag callable"""

    def __init__(self, repository: str, fullname: str, version: str):
        self.repository = repository
        self.fullname = fullname
        self.version = version

    def __call__(self) -> Union[TaskError, bool]:
        try:
            to_tag = DOCKER_CLIENT.images.get(self.fullname)
            to_tag.tag(self.repository, tag=self.version)
        except (docker.errors.BuildError, docker.errors.APIError) as err:
            return doit.exceptions.TaskError(err)
        return True


# The call method is not counter as a public method
# pylint: disable=too-few-public-methods
class PullCommand:
    """Docker pull callable"""

    def __init__(self, repository: str, digest: str):
        self.repository = repository
        self.digest = digest

    def __call__(self) -> Union[TaskError, bool]:
        try:
            DOCKER_CLIENT.images.pull(self.repository, tag=self.digest)
        except (docker.errors.BuildError, docker.errors.APIError) as err:
            return doit.exceptions.TaskError(err)
        return True


# The call method is not counter as a public method
# pylint: disable=too-few-public-methods
class SaveCommand:
    """Docker save callable"""

    def __init__(self, tag: str, save_path: Path):
        self.tag = tag
        self.save_path = str(save_path)

    def __call__(self) -> Union[TaskError, bool]:
        try:
            to_save = DOCKER_CLIENT.images.get(self.tag)
            image_stream = to_save.save()
            with open(self.save_path, 'wb') as image_file:
                for chunk in image_stream:
                    image_file.write(chunk)
        except (docker.errors.APIError, IOError) as err:
            return TaskError(err)
        return True


class RunCommand:
    """Docker run callable"""

    RPMLINTRC_MOUNT : Mount = Mount(
        target='/rpmbuild/rpmlintrc',
        source=str(constants.ROOT/'packages'/'rpmlintrc'),
        type='bind',
        read_only=True
    )
    ENTRYPOINT_MOUNT : Mount = Mount(
        target='/entrypoint.sh',
        source=str(constants.ROOT/'packages'/'entrypoint.sh'),
        type='bind',
        read_only=True
    )
    _BASE_CONFIG = {
        'hostname': 'build',
        'mounts': [ENTRYPOINT_MOUNT],
        'environment': {
            'TARGET_UID': os.geteuid(),
            'TARGET_GID': os.getegid()
        },
        'tmpfs': {'/tmp': ''},
        'remove': True
    }

    def __init__(
        self,
        command:     List[str],
        builder:     Any,
        environment: Optional[Dict[str, Any]]=None,
        mounts:      Optional[List[Mount]]=None,
        tmpfs:       Optional[Dict[str, str]]=None,
        run_config:  Optional[Dict[str, Any]]=None,
        read_only:   bool=False
    ):
        self.command = command
        self.builder = builder
        self.environment = environment or {}
        self.mounts = mounts or []
        self.tmpfs = tmpfs or {}
        self.run_config = run_config or self.base_config()
        self.read_only = read_only

    @classmethod
    def bind_mount(
        cls, source: Path, target: str, **kwargs: Any
    ) -> Mount:
        """Helper for read/write mounts."""
        return Mount(
            source=str(source),
            target=target,
            type='bind',
            **kwargs
        )

    @classmethod
    def bind_ro_mount(cls, source: Path, target: str) -> Mount:
        """Helper for read-only mounts."""
        return cls.bind_mount(source=source, target=target, read_only=True)

    @classmethod
    def base_config(cls) -> Dict[str, Any]:
        """Docker run command base configuration."""
        return copy.deepcopy(cls._BASE_CONFIG)

    def expand_config(self) -> Dict[str, Any]:
        """Expand the run configuration with given data."""
        run_config = copy.deepcopy(self.run_config)
        config_list_keys = ['mounts']
        for key in config_list_keys:
            base_value = run_config.get(key, [])
            expanded_value = base_value + getattr(self, key)
            run_config[key] = expanded_value

        config_dict_keys = ['environment', 'tmpfs']
        for key in config_dict_keys:
            base_value = run_config.get(key, {})
            additional = getattr(self, key)
            run_config[key] = dict(**base_value, **additional)

        simple_keys = ['read_only']
        for key in simple_keys:
            run_config[key] = getattr(self, key)

        return run_config

    def __call__(self) -> Union[TaskError, bool]:
        run_config = self.expand_config()
        try:
            DOCKER_CLIENT.containers.run(
                image=self.builder.tag,
                command=self.command,
                **run_config
            )
        except (
            docker.errors.ContainerError,
            docker.errors.ImageNotFound,
            docker.errors.APIError
        ) as err:
            return TaskError(err)

        return True
