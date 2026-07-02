FROM ghcr.io/diamondlightsource/ubuntu-devcontainer:resolute

# language specific setup ######################################################

# Install Node.js 22. Provides node + npm on PATH, so `npm ci` yields
# ./node_modules/.bin/myst (mystmd@1.10.1, pinned via package-lock.json).
# Python and uv come from the base image.
RUN apt-get update -y \
  && apt-get install -y --no-install-recommends ca-certificates curl \
  && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
  && apt-get install -y --no-install-recommends nodejs \
  && rm -rf /var/lib/apt/lists/*
