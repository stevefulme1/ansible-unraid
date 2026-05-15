# Contributing

Contributions are welcome! Please open an issue or pull request on GitHub.

## Development Setup

1. Clone the repo into the Ansible collections path:
   ```bash
   mkdir -p ~/.ansible/collections/ansible_collections/stevefulme1
   git clone https://github.com/stevefulme1/ansible-unraid.git \
       ~/.ansible/collections/ansible_collections/stevefulme1/unraid
   ```

2. Install development dependencies:
   ```bash
   pip install ansible-core ansible-lint pytest pytest-mock nox bandit
   ```

3. Run tests:
   ```bash
   # Unit tests
   python -m pytest tests/unit/ -v

   # Sanity tests
   ansible-test sanity --python 3.12

   # Linting
   ansible-lint
   ```

## Module Guidelines

- All modules must support `check_mode`.
- Use `unraid_argument_spec()` from `module_utils.unraid_api` for auth params.
- Follow the query → compare → mutate pattern for idempotency.
- Include full DOCUMENTATION, EXAMPLES, and RETURN blocks.
