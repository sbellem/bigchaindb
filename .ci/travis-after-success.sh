#!/bin/bash

set -e -x

if [[ -z ${TOXENV} ]]; then
    codecov --gcov-root ${TRAVIS_BUILD_DIR}/bigchaindb
fi
