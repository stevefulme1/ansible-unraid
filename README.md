# Ansible Collection — stevefulme1.unraid

Ansible collection for managing [Unraid](https://unraid.net/) NAS servers via the built-in GraphQL API.

**Requires Unraid 7.2 or later.**

## Modules

| Module | Description |
|--------|-------------|
| `facts` | Gather system, array, disk, Docker, VM, share, and UPS facts |
| `array` | Start or stop the disk array |
| `parity` | Start, pause, resume, or cancel parity checks |
| `disk` | Spin disks up or down |
| `share` | Manage user shares |
| `docker_container` | Manage Docker container lifecycle |
| `docker_container_update` | Bulk update all containers to latest images |
| `docker_network` | Manage Docker networks |
| `vm` | Manage VM lifecycle (start/stop/pause/resume) |
| `vm_info` | Query detailed VM information |
| `user` | Create user accounts |
| `api_key` | Manage API keys |
| `api_key_role` | Add or remove roles on API keys |
| `notification` | Create, archive, or delete notifications |
| `notification_info` | Query notifications with filters |
| `ups` | Configure UPS settings |
| `flash_backup` | Trigger USB flash backup |
| `settings` | Update system settings |
| `system` | Reboot or shutdown the server |
| `service_info` | List running services |
| `network_info` | Query network access URLs |
| `plugin_info` | List installed plugins |
| `log_info` | List or read log files |
| `update_info` | Check for OS updates |

## Plugins

| Plugin | Type | Description |
|--------|------|-------------|
| `unraid_inventory` | inventory | Dynamic inventory from VMs and Docker containers |
| `unraid_events` | EDA source | Real-time event streaming via GraphQL WebSocket |

## Installation

```bash
ansible-galaxy collection install stevefulme1.unraid
```

## Authentication

Create an API key in your Unraid WebGUI under **Settings > Management Access > API Keys** with the `ADMIN` role.

```yaml
- name: Gather Unraid facts
  stevefulme1.unraid.facts:
    api_url: https://tower.local
    api_key: "{{ unraid_api_key }}"
```

Or use environment variables:

```bash
export UNRAID_API_URL=https://tower.local
export UNRAID_API_KEY=your-api-key-here
```

## Requirements

- Unraid 7.2+
- ansible-core >= 2.16
- Python >= 3.12

## License

GPL-3.0-or-later
