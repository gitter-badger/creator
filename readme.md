*Creator* - Meta build system for ninja
=======================================

[![Join the chat at https://gitter.im/creator-build/creator](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/creator-build/creator?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

*Creator* is a simple, pure Python meta build system for [ninja][] with focus
on an organised and comprehensible way of specifying the build rules. Unlike
GNU Make, Creator is fully modular with namespaces and global and local
variables. Build definitions are Python scripts we call *Units*.

Check out the [Wiki][] for more information!

> __Important__: Creator is in a very early stage and everything can be
> subject to change! If you want to use Creator, make sure to always use
> the latest version from the *master* branch.

__Features__

- Creator is simple (and pure Python)
- Exports [ninja][] build rules 
- Easily extensible, even from a Unit Python script
- Modular approach to build definitions
- Built-in set of Unit Scripts for platform independency
- Full control over the build process from the command-line
- Mix build definitions with custom tasks (Python functions)

__Install__

To always use the latest version, clone the repository and install
via pip remotely:

```
git clone https://github.com/creator-build/creator.git && cd creator
sudo pip3 install -e .
```

Or to install it correctly do either of the two commands

```
sudo pip3 install .
sudo python3 setup.py install
```

__Example__

In an empty hello_world directory create 'src/main.cpp'

```cpp
~/Desktop/hello_world $ cat src/main.cpp
#include <stdio.h>

int main(void) {
    printf("Hello, World!\n");
    return 0;
}
```

Create a '.crunit' file in hello_world such as 'hello_world.crunit'

```python
~/Desktop/hello_world $ cat hello_world.crunit
load('platform', 'p')
load('compiler', 'c')

if not defined('BuildDir'):
  define('BuildDir', '$ProjectPath/build')
define('Sources', '$(wildcard $ProjectPath/src/*.cpp)')
define('Objects', '$(p:obj $(move $Sources, $ProjectPath/src, $BuildDir/obj))')
define('Program', '$(p:bin $BuildDir/main)')

@target()
def objects():
  objects.build_each(
    '$Sources', '$Objects', '$c:cpp $c:compileonly $(c:objout $@) $(quote $<)')

@target(objects)
def program():
  program.build('$Objects', '$Program', '$c:cpp $(c:binout $@) $(quotesplit $<)')

@task(program)
def run():
  shell('$(quote $Program)')
```

Use creator to build and run the program

```
niklas ~/Desktop/hello_world_cpp $ creator program run
creator: exporting to: build.ninja
creator: running: ninja -f build.ninja
[2/2] clang++ -o /Users/niklas/Desktop/hello_wor.../niklas/Desktop/hello_world_cpp/build/obj/main.o
creator: running task 'hello_world:run'
Hello, World!
```

See also: [*creator-build/hello_world.cpp*](https://github.com/creator-build/hello_world.cpp)

__Requirements__

- Python 3
- [setuptools][]
- [glob2][]
- [colorama][] (optional)
- [ninja][]

[setuptools]: https://pypi.python.org/pypi/setuptools
[glob2]: https://pypi.python.org/pypi/glob2
[colorama]: https://pypi.python.org/pypi/colorama
[ninja]: https://github.com/martine/ninja
[Wiki]: https://github.com/creator-build/creator/wiki
