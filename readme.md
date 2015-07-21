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
    '$Sources', '$Objects', '$c:cpp $c:wall $(c:objout $@) $"<')

@target
def program():
  program.build('$Objects', '$Program', '$c:cpp $(c:binout $@) $!<')

@task
def say_hello():
  info('Hello $USERNAME')
```

```
$ creator program say_hello
```

__Requirements__

- Python 3
- [ninja][]
- [colorama][] (optional)

[ninja]: https://github.com/martine/ninja
[colorama]: https://pypi.python.org/pypi/colorama
[Wiki]: https://github.com/creator-build/creator/wiki
