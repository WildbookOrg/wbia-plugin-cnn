#!/bin/bash

set -ex

# See https://stackoverflow.com/a/246128/176882
export CUR_LOC="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Install Python package dependencies
python -m pip install -r requirements/build.txt

$CUR_LOC/_install_libgpuarray_build_software_multi_platform.sh