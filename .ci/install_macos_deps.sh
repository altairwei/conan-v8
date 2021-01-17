#!/usr/bin/env bash

set -e -o pipefail
shopt -s failglob
export LC_ALL=C

# Install conan
pip3 install wheel setuptools
pip3 install conan --upgrade
pip3 install conan_package_tools bincrafters_package_tools
conan user