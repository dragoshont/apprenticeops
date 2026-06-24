#!/bin/sh
# Copy the read-only mounted SSH material into a root-owned ~/.ssh with the strict
# perms OpenSSH demands (the host mount is owned by the operator's uid, which ssh
# rejects when the container runs as root). Then hand off to the CMD.
set -e

if [ -d /root/.ssh-src ]; then
  mkdir -p /root/.ssh
  cp -rL /root/.ssh-src/. /root/.ssh/ 2>/dev/null || true
  chown -R root:root /root/.ssh
  chmod 700 /root/.ssh
  chmod 600 /root/.ssh/* 2>/dev/null || true
  chmod 644 /root/.ssh/*.pub 2>/dev/null || true
fi

exec "$@"
