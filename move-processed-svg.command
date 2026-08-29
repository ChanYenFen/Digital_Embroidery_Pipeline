#!/bin/bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$DIR/tools/move-processed-svg.sh"
echo
read -n 1 -s -r -p "Press any key to close..."
echo
