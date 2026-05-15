"""Root conftest.py -- set up import paths for Ansible collection testing.

Creates a temporary namespace package structure so that
``import ansible_collections.stevefulme1.unraid.plugins...`` resolves to the
plugins/ directory inside this repository without installing the collection.

When CI checks out into ``ansible_collections/stevefulme1/unraid``, the
namespace structure already exists — in that case we add the ancestor
directory to sys.path instead of creating a symlink.
"""
from __future__ import absolute_import, division, print_function

__metaclass__ = type

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

# Detect CI layout: repo is already at .../ansible_collections/stevefulme1/unraid
if _REPO_ROOT.endswith(os.path.join("ansible_collections", "stevefulme1", "unraid")):
    _COLLECTIONS_BASE = os.path.dirname(
        os.path.dirname(os.path.dirname(_REPO_ROOT))
    )
else:
    _COLLECTIONS_BASE = os.path.join(_REPO_ROOT, ".test_collections")
    _NAMESPACE_DIR = os.path.join(
        _COLLECTIONS_BASE, "ansible_collections", "stevefulme1"
    )
    _COLLECTION_LINK = os.path.join(_NAMESPACE_DIR, "unraid")

    if not os.path.isdir(_NAMESPACE_DIR):
        os.makedirs(_NAMESPACE_DIR, exist_ok=True)

    for _d in [
        os.path.join(_COLLECTIONS_BASE, "ansible_collections"),
        _NAMESPACE_DIR,
    ]:
        _init = os.path.join(_d, "__init__.py")
        if not os.path.exists(_init):
            with open(_init, "w") as _f:
                pass

    if not os.path.exists(_COLLECTION_LINK):
        os.symlink(_REPO_ROOT, _COLLECTION_LINK)

if _COLLECTIONS_BASE not in sys.path:
    sys.path.insert(0, _COLLECTIONS_BASE)
