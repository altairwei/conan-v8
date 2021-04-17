import os
import platform
from cpt.packager import ConanMultiPackager

if __name__ == "__main__":
    builder = ConanMultiPackager(
        username="altair_wei",
        upload_dependencies="all",
        build_policy="missing")
    if platform.system() == "Windows":
        for build_type in ["Release", "Debug"]:
            builder.add(settings={
                "arch": "x86_64",
                "build_type": build_type,
                "compiler": "Visual Studio",
                "compiler.version": 15,
                "compiler.runtime": "MT"
            })
    else:
        for build_type in ["Release", "Debug"]:
            builder.add(settings={
                "arch": "x86_64",
                "build_type": build_type,
                "compiler": os.environ["COMPILER_NAME"],
                "compiler.version": os.environ["COMPILER_VERSION"],
                "compiler.libcxx": os.environ["LIBCXX"]
            })
    builder.run()
