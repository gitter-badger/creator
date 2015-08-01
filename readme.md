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

__Install__

```
python3 setup.py build
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

Create a '.crunit' file in hello_world such as 'test.crunit'

```python
~/Desktop/hello_world $ cat test.crunit
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
    '$Sources', '$Objects', '$c:cpp $c:compileonly $(c:objout $@) $(quote $<)')

@target
def program():
  program.build('$Objects', '$Program', '$c:cpp $(c:binout $@) $(quotesplit $<)')

@task
def run():
  shell('$(quote $Program)')
```

Use creator to build and run the program
```
~/Desktop/hello_world $ creator program run
creator: exporting to: build.ninja
creator: running: ninja -f build.ninja test_program
[1/2] cl /nologo /EHsc /FoC:\Users\niklas\Desktop\rep...\Users\niklas\Desktop\repos\creator\test\src\main.cpp
main.cpp
[2/2] cl /nologo /EHsc /FeC:\Users\niklas\Desktop\rep...\niklas\Desktop\repos\creator\test\build\obj\main.obj
creator: running task 'test:run'
Hello, World!
```

__Requirements__

- Python 3
- [setuptools][]
- [ninja][]
- [colorama][] (optional)

[setuptools]: https://pypi.python.org/pypi/setuptools
[ninja]: https://github.com/martine/ninja
[colorama]: https://pypi.python.org/pypi/colorama
[Wiki]: https://github.com/creator-build/creator/wiki
