*Creator* - software build automation tool
==========================================

*Creator* is a Python based software build automation tool outputting
[ninja][] build files based on *"Unit Scripts"*. The project is
licensed under the MIT license. Check out the [Wiki][] for more information!

Note that Creator is in a very early stage. Contributions, questions and
bug reports are welcome!

__Features__

- Creator is simple (and pure Python)
- Modular approach to build definitions
- Built-in set of Unit Scripts for platform independency
- Full control over the build process from the command-line
- native support for the [ninja][] build system
- Mix build definitions with custom tasks (Python functions)

__Quick Reference__

- [Unit Script Functions](https://github.com/creator-build/creator/wiki/Units#unit-script-built-ins)
- [Macro Functions](https://github.com/creator-build/creator/wiki/Macros#functions)

__Example__

```python
load('platform', 'p')
load('compiler', 'c')

if not defined('BuildDir'):
  define('BuildDir', '$ProjectPath/build')
define('Sources', '$*($ProjectPath/*.cpp)')
define('Program', '$(p:bin $BuildDir/main)')

@target
def program():
  program.add('$Sources', '$Program', '$c:cpp $c:wall $(c:binout $@) $!<')

@task
def say_hello():
  info('Hello $USERNAME')
```

__Requirements__

- Python 3
- [nr.strex][]
- [ninja][]

[ninja]: https://github.com/martine/ninja
[nr.strex]: https://github.com/NiklasRosenstein/nr.strex
[Wiki]: https://github.com/creator-build/creator/wiki
