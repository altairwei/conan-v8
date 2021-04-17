#!/usr/bin/env bash

set -e -o pipefail
shopt -s failglob
export LC_ALL=C

# Fix deps
sudo apt remove -y php7.4-common 

# Install conan
pip3 install wheel setuptools
pip3 install conan --upgrade
pip3 install conan_package_tools bincrafters_package_tools
source ~/.profile
conan user
conan profile new default --detect

sudo apt-get install -y -qq --no-install-recommends gperf bison flex libc6-dev