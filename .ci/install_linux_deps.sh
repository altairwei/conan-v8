#!/usr/bin/env bash

set -e -o pipefail
shopt -s failglob
export LC_ALL=C

# Setup python ppa
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update

# Install conan
pip3 install wheel setuptools
pip3 install conan --upgrade
pip3 install conan_package_tools bincrafters_package_tools
source ~/.profile
conan user
conan profile new default --detect

if [[ "${COMPILER_NAME}" == "gcc" ]]; then
    #conan profile update settings.compiler.libcxx=libstdc++11 default
    echo "Skip update libcxx"
elif [[ "${COMPILER_NAME}" == "clang" ]]; then
    conan profile update settings.compiler.libcxx=libc++ default
fi

sudo apt-get install -y -qq --no-install-recommends gperf bison flex libc6-dev