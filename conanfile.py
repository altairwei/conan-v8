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

    _source_subfolder = "source_subfolder"
    _build_subfolder = "build_subfolder"

    def _check_python_version(self):
        # Check if a valid python2 is available in PATH or it will failflex
        # Start by checking if python2 can be found
        python_exe = tools.which("python2")
        if not python_exe:
            # Fall back on regular python
            python_exe = tools.which("python")

        if not python_exe:
            msg = ("Python2 must be available in PATH "
                    "in order to build v8")
            raise ConanInvalidConfiguration(msg)
        # In any case, check its actual version for compatibility
        from six import StringIO  # Python 2 and 3 compatible
        mybuf = StringIO()
        cmd_v = "{} --version".format(python_exe)
        self.run(cmd_v, output=mybuf)
        p = re.compile(r'Python (\d+\.\d+\.\d+)')
        verstr = p.match(mybuf.getvalue().strip()).group(1)
        if verstr.endswith('+'):
            verstr = verstr[:-1]
        version = tools.Version(verstr)
        # >= 2.7.5 & < 3
        v_min = "2.7.5"
        v_max = "3.0.0"
        if (version >= v_min) and (version < v_max):
            msg = ("Found valid Python 2 required for v8:"
                    " version={}, path={}".format(mybuf.getvalue(), python_exe))
            self.output.success(msg)
        else:
            msg = ("Found Python 2 in path, but with invalid version {}"
                    " (v8 requires >= {} & < "
                    "{})".format(verstr, v_min, v_max))
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
        # python >= 2.7.5 & < 3
        try:
           self._check_python_version()
        except ConanInvalidConfiguration as e:
            if tools.os_info.is_windows:
                raise e
            self.output.info("Python 2 not detected in path. Trying to install it")
            tools.SystemPackageTool().install(["python2", "python"])
            self._check_python_version()
            raise

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
            if str(self.settings.compiler.version) not in ["15", "16"]:
                raise ValueError("not yet supported visual studio version used for v8 build")
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

    def build(self):
        v8_source_root = os.path.join(self.source_folder, "v8")
        self._set_environment_vars()

        if tools.os_info.is_linux:
            self._install_system_requirements_linux()

        # fix gn always detecting the runtime on its own:
        if str(self.settings.compiler) == "Visual Studio" and str(self.settings.compiler.runtime) in ["MD", "MDd"]:
            build_gn_file = os.path.join(v8_source_root, "build", "config", "win", "BUILD.gn")
            #print("replacing MT / MTd with MD / MDd in gn file." + build_gn_file)
            #tools.replace_in_file(file_path=build_gn_file, search="MT", replace="MD", strict=False)

        with tools.chdir(v8_source_root):
            self.run("gclient sync")
            # Refer to v8/infra/mb/mb_config.pyl
            gen_arguments = [
                "is_debug = " + ("true" if str(self.settings.build_type) == "Debug" else "false"),
                "target_cpu = " + ('"x64"' if str(self.settings.arch) == "x86_64" else '"x86"'),
                "is_component_build = false",
                "v8_monolithic = true",
                "is_chrome_branded = false",
                "v8_static_library = true",
                "treat_warnings_as_errors = false",
                "v8_use_external_startup_data = false"
            ]
            # v8_enable_backtrace=false, v8_enable_i18n_support

            if tools.os_info.is_linux:
                gen_arguments += [
                    "use_sysroot = false",
                    "use_custom_libcxx = false",
                    "use_custom_libcxx_for_host = false",
                    "use_glib = false",
                    "is_clang = " + ("true" if "clang" in str(self.settings.compiler).lower() else "false")
                ]

            args_gn_file = os.path.join(self.build_folder, "args.gn")
            with open(args_gn_file, "w") as f:
                f.write("\n".join(gen_arguments))

            generator_call = "gn gen {folder}".format(folder=self.build_folder)

            # maybe todo: absolute path..
            #if tools.os_info.is_windows:
                # this is picking up the python shipped via depot_tools, since we got it in the path.
            #    generator_call = "python " + generator_call
            self.run("python --version")
            print(generator_call)
            self.run(generator_call)
            self.run("ninja -C {folder} v8_monolith".format(folder=self.build_folder))


    def package(self):
        self.copy(pattern="LICENSE*", dst="licenses", src="v8")
        self.copy(pattern="*v8_monolith.a", dst="lib", keep_path=False)
        self.copy(pattern="*v8_monolith.lib", dst="lib", keep_path=False)
        self.copy(pattern="*.h", dst="include/v8", src="v8/include", keep_path=True)


    def package_info(self):
        # fix issue on Windows and OSx not finding the KHR files
        # self.cpp_info.includedirs.append(os.path.join("include", "MagnumExternal", "OpenGL"))
        # builtLibs = tools.collect_libs(self)
        self.cpp_info.libs = ["v8_monolith"]  # sort_libs(correct_order=allLibs, libs=builtLibs, lib_suffix=suffix, reverse_result=True)

