*Creator* - Meta build system for ninja
=======================================

*Creator* is a simple, pure Python meta build system for [ninja][] with focus on an organised and comprehensible way of specifying the build rules. Unlike GNU Make, Creator is fully modular with namespaces and global and local variables. Build definitions are Python scripts we call *Units*.

Check out the [Wiki][] for more information!

__Features__

- Creator is simple (and pure Python)
- Exports [ninja][] build rules 
- Easily extensible, even from a Unit Python script
- Modular approach to build definitions
- Built-in set of Unit Scripts for platform independency
- Full control over the build process from the command-line
- Mix build definitions with custom tasks (Python functions)

__Example__

```python
load('platform', 'p')
load('compiler', 'c')

if not defined('BuildDir'):
  define('BuildDir', '$ProjectPath/build')
define('Sources', '$(wildcard $ProjectPath/src/*.cpp)')
define('Objects', '$(p:obj $(move $Sources, $ProjectPath/src, $BuildDir/obj))')
define('Program', '$(p:bin $BuildDir/main)')

@target
def objects():
  objects.build_each(
    '$Sources', '$Objects', '$c:cpp $(c:objout $@) $"<')

@target
def program():
  program.build('$Objects', '$Program', '$c:cpp $(c:binout $@) $!<')

@task
def run():
  import subprocess
  subprocess.call([eval('$Program')])
```

```
~/Desktop/hello_world $ creator program run
creator: exporting to: build.ninja
creator: running: ninja -f build.ninja test_program
[1/2] cl /nologo /FoC:\Users\niklas\Desktop\hel...\niklas\Desktop\hello_world\src\main.cpp
main.cpp
C:\Program Files (x86)\Microsoft Visual Studio 11.0\VC\INCLUDE\xlocale(336) : warning C4530: C++ exception handler used, but unwind semantics are not enabled. Specify /EHsc
[2/2] cl /nologo /FeC:\Users\niklas\Desktop\hel...\niklas\Desktop\hello_world\build\obj\main.obj
creator: running task 'test:run'
Hello, World!
```

__Requirements__

- Python 3
- [ninja][]
- [colorama][] (optional)

[ninja]: https://github.com/martine/ninja
[colorama]: https://pypi.python.org/pypi/colorama
[Wiki]: https://github.com/creator-build/creator/wiki
