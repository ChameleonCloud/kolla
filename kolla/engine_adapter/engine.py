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

from enum import Enum
from kolla.image.utils import LOG

try:
    import docker
except (ImportError):
    LOG.debug("Docker python library was not found")

try:
    import python_on_whales as buildx
except (ImportError):
    LOG.debug("python_on_whales python library was not found")

try:
    import podman
except (ImportError, ModuleNotFoundError):
    LOG.debug("Podman python library was not found")
    pass


class Engine(Enum):

    DOCKER = "docker"
    BUILDX = "buildx"
    PODMAN = "podman"


class UnsupportedEngineError(ValueError):

    def __init__(self, engine_name):
        super().__init__()
        self.engine_name = engine_name

    def __str__(self):
        return f'Unsupported engine name given: "{self.engine_name}"'


def getEngineException(conf):
    if conf.engine == Engine.DOCKER.value:
        return (docker.errors.DockerException)
    elif conf.engine == Engine.BUILDX.value:
        return (buildx.exceptions.DockerException)
    elif conf.engine == Engine.PODMAN.value:
        return (podman.errors.exceptions.APIError,
                podman.errors.exceptions.PodmanError)
    else:
        raise UnsupportedEngineError(conf.engine)


class python_on_whales_adapter(buildx.DockerClient):

    def build_to_buildx(self, 
                        path,
                        tag,
                        nocache,
                        rm,
                        network_mode,
                        pull,
                        forcerm,
                        platform,
                        buildargs,
                        **kwargs):
        
        buildx_kwargs = {}

        if buildargs:
            buildx_kwargs["build_args"]=buildargs

        if kwargs:
            buildx_kwargs.update(kwargs)

        result = self.buildx.build(
            stream_logs=True,
            load=True,
            context_path = path,
            tags = [tag],
            cache = not nocache,
            network=network_mode,
            pull=pull,
            **buildx_kwargs
        )

        # for some reason kolla wants item [1]?
        return [None, result]

    def __init__(self):
        super().__init__()
        self.images=self.image
        self.images.build=self.build_to_buildx


def getEngineClient(conf):
    if conf.engine == Engine.DOCKER.value:
        kwargs_env = docker.utils.kwargs_from_env()
        return docker.DockerClient(version='auto', **kwargs_env)
    elif conf.engine == Engine.BUILDX.value:
        return python_on_whales_adapter()
    elif conf.engine == Engine.PODMAN.value:
        client = podman.PodmanClient(base_url=conf.podman_base_url)
        try:
            client.version()
        except podman.errors.exceptions.APIError as e:
            e.explanation += (". Check if podman service is active and "
                              "the address to podman.sock is set correctly "
                              "through --podman_base_url")
            raise e
        return client
    else:
        raise UnsupportedEngineError(conf.engine)
