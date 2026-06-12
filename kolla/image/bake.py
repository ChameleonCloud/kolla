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

import json
import os
import re

from kolla.image.tasks import get_build_args
from kolla.image.utils import Status


def target_name(image):
    # buildx restricts target names to [a-zA-Z0-9_-]
    return re.sub(r'[^a-zA-Z0-9_-]', '_', image.name)


def build_bake_definition(conf, images, working_dir):
    matched = {image.name: image for image in images
               if image.status == Status.MATCHED}
    build_args = get_build_args(conf)
    targets = {}
    for name in sorted(matched):
        image = matched[name]
        target = {
            'context': os.path.relpath(image.path, working_dir),
            'dockerfile': 'Dockerfile',
            'tags': [image.canonical_name],
        }
        if image.parent is not None and image.parent.name in matched:
            # The rendered FROM line is the parent's canonical name, so
            # buildx substitutes the locally built parent target for it.
            target['contexts'] = {
                image.parent.canonical_name:
                    'target:' + target_name(image.parent),
            }
        elif image.parent is None and conf.pull:
            # Pull the latest image for the base distro only
            target['pull'] = True
        if build_args:
            target['args'] = build_args
        if conf.network_mode:
            target['network'] = conf.network_mode
        if not conf.cache:
            target['no-cache'] = True
        targets[target_name(image)] = target
    return {
        'group': {'default': {'targets': sorted(targets)}},
        'target': targets,
    }


def render_hcl(definition):
    # All scalar/list values are emitted with json.dumps, which is valid
    # HCL for strings, bools and string lists. Maps need "k" = "v" form.
    lines = []
    for group_name, group in definition['group'].items():
        lines.append('group %s {' % json.dumps(group_name))
        lines.append('  targets = %s' % json.dumps(group['targets']))
        lines.append('}')
        lines.append('')
    for name, target in definition['target'].items():
        lines.append('target %s {' % json.dumps(name))
        for key, value in target.items():
            if isinstance(value, dict):
                lines.append('  %s = {' % key)
                for k in sorted(value):
                    lines.append('    %s = %s' % (json.dumps(k),
                                                  json.dumps(value[k])))
                lines.append('  }')
            else:
                lines.append('  %s = %s' % (key, json.dumps(value)))
        lines.append('}')
        lines.append('')
    return '\n'.join(lines)


def write_bake_file(conf, images, working_dir):
    definition = build_bake_definition(conf, images, working_dir)
    path = os.path.join(working_dir, conf.bake_file)
    with open(path, 'w') as f:
        f.write(render_hcl(definition))
    return path