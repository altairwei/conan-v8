import os
import platform
from cpt.packager import ConanMultiPackager


if __name__ == "__main__":
    builder = ConanMultiPackager(build_policy="outdated", upload_only_recipe = True)
    if platform.system() == "Windows":
        for build_type in ["Release", "Debug"]:
            for crt in ["MT", "MD"]:
                builder.add(settings={
                    "arch": "x86_64",
                    "build_type": build_type,
                    "compiler": os.environ["COMPILER_NAME"],
                    "compiler.version": os.environ["COMPILER_VERSION"],
                    "compiler.runtime": crt + "d" if build_type == "Debug" else crt
                })
    elif platform.system() == "Darwin":
        for build_type in ["Release", "Debug"]:
            builder.add(settings={
                "arch": "x86_64",
                "build_type": build_type,
                "compiler": "apple-clang",
                "compiler.version": os.environ["CLANG_VERSION"],
                "compiler.libcxx": "libc++"
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
