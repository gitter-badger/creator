*Creator* - software build automation tool
==========================================

*Creator* is a Python based software build automation tool outputting
[ninja][] build files based on *Creator Unit Scripts*. The project is
licensed under the MIT license. Check out the [Wiki][] for more information!

Note that Creator is in a very early stage. Contributions, questions and
bug reports are absolutely welcome!

__Features__

- Creator is simple (and pure Python)
- Modular dependency management
- Built-in set of Unit Scripts for platform independent building
- Easily change build settings from the command-line or Unit Scripts
- native support for the [ninja][] build system

__Quick Reference__

- [Unit Script Functions](https://github.com/NiklasRosenstein/creator/wiki/Units#unit-script-built-ins)
- [Macro Functions](https://github.com/NiklasRosenstein/creator/wiki/Macros#functions)

__Example__

```python
load('platform', 'p')
load('compiler', 'c')

if not defined('BuildDir'):
  define('BuildDir', '$ProjectPath/build')
define('Sources', '$(wildcard $ProjectPath/*.cpp)')
define('Program', '$(p:bin $BuildDir/main)')

@target
def program():
  program.add('$Sources', '$Program', '$c:cpp $c:wall $(c:binout $@) $(quotesplit $<)')
```

__Requirements__

- Python 3
- [nr.strex][]
- [ninja][]

__List of Unit Scrips__

- [c4dunit](https://github.com/NiklasRosenstein/c4dunit) - Build
  Cinema 4D plugins on Windows and Mac OS

[ninja]: https://github.com/martine/ninja
[nr.strex]: https://github.com/NiklasRosenstein/nr.strex
[Wiki]: https://github.com/NiklasRosenstein/py-creator/wiki
