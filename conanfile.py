import os
import sys
import shutil
import subprocess
import re

from conans import ConanFile, CMake, tools
from conans.errors import ConanInvalidConfiguration


class V8Conan(ConanFile):
    name = "v8"
    version = "8.8.214"
    license = "BSD"
    homepage = "https://v8.dev"
    author = "Altair Wei altair_wei@outlook.com"
    url = "https://github.com/altairwei/conan-v8.git"
    description = "V8 is Google's open source JavaScript engine."
    topics = ("javascript", "interpreter", "compiler", "virtual-machine", "javascript-engine")

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    generators = "cmake"
    short_paths = True

    exports_sources = ["msvc_crt.gn"]

    _source_subfolder = "source_subfolder"
    _build_subfolder = "build_subfolder"

    def _check_python_version(self):
        """depot_tools requires python >= 2.7.5 or >= 3.8 for python 3 support."""
        python_exe = tools.which("python")
        if not python_exe:
            msg = ("Python must be available in PATH "
                    "in order to build v8")
            raise ConanInvalidConfiguration(msg)
        # In any case, check its actual version for compatibility
        from six import StringIO  # Python 2 and 3 compatible
        version_buf = StringIO()
        cmd_v = "{} --version".format(python_exe)
        self.run(cmd_v, output=version_buf)
        p = re.compile(r'Python (\d+\.\d+\.\d+)')
        verstr = p.match(version_buf.getvalue().strip()).group(1)
        if verstr.endswith('+'):
            verstr = verstr[:-1]
        version = tools.Version(verstr)
        # >= 2.7.5 & < 3
        py2_min = "2.7.5"
        py2_max = "3.0.0"
        py3_min = "3.8.0"
        if (version >= py2_min) and (version < py2_max):
            msg = ("Found valid Python 2 required for v8:"
                    " version={}, path={}".format(version_buf.getvalue().strip(), python_exe))
            self.output.success(msg)
        elif version >= py3_min:
            msg = ("Found valid Python 3 required for v8:"
                    " version={}, path={}".format(version_buf.getvalue().strip(), python_exe))
            self.output.success(msg)
        else:
            msg = ("Found Python in path, but with invalid version {}"
                    " (v8 requires >= {} and < "
                    "{} or >= {})".format(verstr, py2_min, py2_max, py3_min))
            raise ConanInvalidConfiguration(msg)

    def system_requirements(self):
        if tools.os_info.is_linux:
            if not tools.SystemPackageTool().installed("tzdata"):
                if tools.os_info.linux_distro == "ubuntu":
                    # Install tzdata without user input
                    os.environ["DEBIAN_FRONTEND"] = "noninteractive"
                    self.run("sudo ln -fs /usr/share/zoneinfo/America/New_York /etc/localtime")
                    tools.SystemPackageTool().install("tzdata")
                    self.run("sudo dpkg-reconfigure --frontend noninteractive tzdata")
            if not tools.which("lsb-release"):
                tools.SystemPackageTool().install("lsb-release")
        if tools.os_info.is_windows:
            if str(self.settings.compiler.version) not in ["15", "16"]:
                raise ConanInvalidConfiguration("not yet supported visual studio version used for v8 build")
        self._check_python_version()

    def build_requirements(self):
        if not tools.which("ninja"):
            self.build_requires("ninja/1.10.0")
        if self.settings.os != "Windows":
            if not tools.which("bison"):
                self.build_requires("bison/3.5.3")
            if not tools.which("gperf"):
                self.build_requires("gperf/3.1")
            if not tools.which("flex"):
                self.build_requires("flex/2.6.4")

    def _set_environment_vars(self):
        """set the environment variables, such that the google tooling is found (including the bundled python2)"""
        os.environ["PATH"] = os.path.join(self.source_folder, "depot_tools") + os.pathsep + os.environ["PATH"]
        os.environ["DEPOT_TOOLS_PATH"] = os.path.join(self.source_folder, "depot_tools")
        if tools.os_info.is_windows:
            os.environ["DEPOT_TOOLS_WIN_TOOLCHAIN"] = "0"
            os.environ["GYP_MSVS_VERSION"] = "2017" if str(self.settings.compiler.version) == "15" else "2019"

    def source(self):
        self.run("git clone --depth 1 https://chromium.googlesource.com/chromium/tools/depot_tools.git")
        self._set_environment_vars()
        self.run("gclient")
        self.run("fetch v8")
        with tools.chdir("v8"):
            self.run("git checkout {}".format(self.version))

    @staticmethod
    def get_gn_profile(settings):
        """return the profile defined somewhere in v8/infra/mb/mb_config.pyl which corresponds "nearly" to the one we need.. "nearly" as in "not even remotely"..
        """
        return "{arch}.{build_type}".format(build_type=str(settings.build_type).lower(),
                                arch="x64" if str(settings.arch) == "x86_64" else "x86")

    def _install_system_requirements_linux(self):
        """some extra script must be executed on linux"""
        os.environ["PATH"] += os.pathsep + os.path.join(self.source_folder, "depot_tools")
        sh_script = self.source_folder + "/v8/build/install-build-deps.sh"
        self.run("chmod +x " + sh_script)
        cmd = sh_script + " --unsupported --no-arm --no-nacl --no-backwards-compatible --no-chromeos-fonts --no-prompt "
        cmd = cmd + ("--syms" if str(self.settings.build_type) == "Debug" else "--no-syms")
        cmd = "export DEBIAN_FRONTEND=noninteractive && " + cmd
        self.run(cmd)

    def _patch_msvc_runtime(self):
        v8_source_root = os.path.join(self.source_folder, "v8")
        msvc_config_folder = os.path.join(v8_source_root, "build", "config", "msvc")
        if os.path.exists(os.path.join(msvc_config_folder, "BUILD.gn")):
            return
        tools.mkdir(msvc_config_folder)
        shutil.copy(
            os.path.join(self.source_folder, "msvc_crt.gn"),
            os.path.join(msvc_config_folder, "BUILD.gn"))
        config_gn_file = os.path.join(v8_source_root, "build", "config", "BUILDCONFIG.gn")
        tools.replace_in_file(config_gn_file,
            "//build/config/win:default_crt",
            "//build/config/msvc:conan_crt"
        )


    def _gen_arguments(self):
        # Refer to v8/infra/mb/mb_config.pyl
        is_debug = "true" if str(self.settings.build_type) == "Debug" else "false"
        gen_arguments = [
            "is_debug = " + is_debug,
            #"enable_iterator_debugging = " + is_debug, # TODO: make it configurable

            "target_cpu = " + ('"x64"' if str(self.settings.arch) == "x86_64" else '"x86"'),
            "is_component_build = false",
            "is_chrome_branded = false",
            "treat_warnings_as_errors = false",
            "is_clang = false", # Do not use clang and libc++ shipped with v8
            "use_custom_libcxx = false",
            "use_custom_libcxx_for_host = false",
            "use_glib = false",
            "use_sysroot = false",

            # V8 specific settings
            "v8_monolithic = true",
            "v8_static_library = true",
            "v8_use_external_startup_data = false",
            #"v8_enable_backtrace = false",
        ]

        if tools.os_info.is_windows:
            gen_arguments += [
                "conan_compiler_runtime = \"%s\"" % str(self.settings.compiler.runtime)
            ]

        if tools.os_info.is_linux:
            gen_arguments += [
                "custom_toolchain=\"//build/toolchain/linux/unbundle:default\"",
                "host_toolchain=\"//build/toolchain/linux/unbundle:default\""
            ]

        return gen_arguments


    def build(self):
        v8_source_root = os.path.join(self.source_folder, "v8")
        self._set_environment_vars()

        if tools.os_info.is_linux:
            self._install_system_requirements_linux()

        with tools.chdir(v8_source_root):
            self.run("gclient sync")

            if tools.os_info.is_windows and str(self.settings.compiler) == "Visual Studio":
                self._patch_msvc_runtime()

            args = self._gen_arguments()
            args_gn_file = os.path.join(self.build_folder, "args.gn")
            with open(args_gn_file, "w") as f:
                f.write("\n".join(args))

            generator_call = "gn gen {folder}".format(folder=self.build_folder)

            self.run("python --version")
            print(generator_call)
            self.run(generator_call)
            self.run("ninja -v -C {folder} v8_monolith".format(folder=self.build_folder))


    def package(self):
        self.copy(pattern="LICENSE*", dst="licenses", src="v8")
        self.copy(pattern="*v8_monolith.a", dst="lib", keep_path=False)
        self.copy(pattern="*v8_monolith.lib", dst="lib", keep_path=False)
        self.copy(pattern="*.h", dst="include/v8", src="v8/include", keep_path=True)


    def package_info(self):
        self.cpp_info.libs = ["v8_monolith"]
        self.cpp_info.includedirs.append("include/v8")

        # Pre-configured settings come with conan-v8
        self.cpp_info.defines += [
            "V8_COMPRESS_POINTERS"
        ]
        if self.settings.compiler in ["gcc", "clang", "apple-clang"]:
            self.cpp_info.cxxflags += [
                "-std=c++14"
            ]
        if self.settings.os == "Windows":
            self.cpp_info.system_libs += [
                "winmm.lib",
                "dbghelp.lib"
            ]
            self.cpp_info.defines += [
                "_HAS_ITERATOR_DEBUGGING=0"
            ]
        else:
            self.cpp_info.cxxflags += ["-pthread"]


