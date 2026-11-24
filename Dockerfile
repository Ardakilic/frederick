# Build image for frederick - see Makefile. Every command runs in here; nothing
# is installed on the host. Base image and wheels are pinned together: a
# floating toolchain re-triangulates every STL (same shape, different bytes).
FROM python:3.14-slim

COPY requirements.txt requirements-dev.txt /tmp/
RUN pip install --no-cache-dir --root-user-action=ignore \
    -r /tmp/requirements.txt -r /tmp/requirements-dev.txt

# The Makefile runs as the caller's uid:gid, which has no passwd entry and so
# no writable home; /tmp works for any user. No .pyc files in the mounted repo.
ENV HOME=/tmp \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
