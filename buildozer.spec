[app]
title = 批量图片生成器
package.name = batchimagegen
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,ttf,csv
version = 0.2
requirements = python3,kivy==2.1.0, Pillow, androidstorage4kivy
orientation = portrait
osx.python_version = 3
osx.kivy_version = 2.1.0
fullscreen = 0

[buildozer]
log_level = 2
warn_on_root = 1