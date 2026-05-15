"""Root conftest.py -- set up import paths for Ansible collection testing.

Creates a temporary namespace package structure so that
``import ansible_collections.stevefulme1.unraid.plugins...`` resolves to the
plugins/ directory inside this repository without installing the collection.
"""
from __future__ import absolute_import, division, print_function

__metaclass__ = type

import os
import sys

# Build the path: <repo>/.test_collections/ansible_collections/stevefulme1/unraid
_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
_COLLECTIONS_BASE = os.path.join(_REPO_ROOT, ".test_collections")
_NAMESPACE_DIR = os.path.join(
    _COLLECTIONS_BASE, "ansible_collections", "stevefulme1"
)
_COLLECTION_LINK = os.path.join(_NAMESPACE_DIR, "unraid")

# Create the namespace directories and symlink once per session
if not os.path.isdir(_NAMESPACE_DIR):
    os.makedirs(_NAMESPACE_DIR, exist_ok=True)

# __init__.py files for namespace packages
for _d in [
    os.path.join(_COLLECTIONS_BASE, "ansible_collections"),
    _NAMESPACE_DIR,
]:
    _init = os.path.join(_d, "__init__.py")
    if not os.path.exists(_init):
        with open(_init, "w") as _f:
            pass

# Symlink the repo root as the collection directory
if not os.path.exists(_COLLECTION_LINK):
    os.symlink(_REPO_ROOT, _COLLECTION_LINK)

# Prepend to sys.path so Python finds ansible_collections.stevefulme1.unraid
if _COLLECTIONS_BASE not in sys.path:
    sys.path.insert(0, _COLLECTIONS_BASE)
