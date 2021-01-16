#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import platform
from cpt.packager import ConanMultiPackager

if __name__ == "__main__":
    builder = ConanMultiPackager(username="altair_wei", upload_dependencies="all", build_policy="missing")
    if platform.system() == "Windows":
        builder.add(settings={"arch": "x86_64", "build_type": "Release", "compiler": "Visual Studio", "compiler.version": 14, "compiler.runtime": "MT" })
        builder.add(settings={"arch": "x86_64", "build_type": "Debug"  , "compiler": "Visual Studio", "compiler.version": 14, "compiler.runtime": "MTd" })
    else:
        builder.add(settings={"arch": "x86_64", "build_type": "Release", "compiler": os.environ["COMPILER_NAME"], "compiler.version": os.environ["COMPILER_VERSION"]})
        builder.add(settings={"arch": "x86_64", "build_type": "Debug"  , "compiler": os.environ["COMPILER_NAME"], "compiler.version": os.environ["COMPILER_VERSION"]})
    builder.run()
