==========================================
stevefulme1.unraid Release Notes
==========================================

.. contents:: Topics

v1.0.0
======

Release Summary
---------------

Initial release of the Unraid Ansible Collection.

Major Changes
-------------

- Added GraphQL API client for Unraid 7.2+.
- Added ``facts`` module for gathering system, array, Docker, VM, and share facts.
- Added ``array`` module for starting and stopping the disk array.
- Added ``parity`` module for parity check operations.
- Added ``disk`` module for spinning disks up and down.
- Added ``share`` module for user share management.
- Added ``docker_container`` module for container lifecycle management.
- Added ``docker_container_update`` module for bulk container updates.
- Added ``docker_network`` module for Docker network management.
- Added ``vm`` module for VM lifecycle management.
- Added ``user`` module for user account creation.
- Added ``api_key`` module for API key management.
- Added ``notification`` module for notification management.
- Added ``ups`` module for UPS configuration.
- Added ``flash_backup`` module for flash drive backups.
- Added ``settings`` module for system settings.
- Added ``system`` module for reboot and shutdown.
- Added ``unraid_inventory`` inventory plugin.
- Added ``unraid_events`` EDA event source plugin.
