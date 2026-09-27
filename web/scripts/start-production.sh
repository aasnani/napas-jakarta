#!/bin/sh

set -eu

# A self-hosted Next/Eve deployment needs both processes in the same service.
# The supervisor makes either child failing a service failure, so Railway does
# not keep routing traffic to a Next process whose Eve dependency is gone.
exec node ./scripts/production-supervisor.mjs
