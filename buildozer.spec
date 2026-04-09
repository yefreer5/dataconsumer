[app]
title = Data Consumer
package.name = dataconsumer
package.domain = org.dataconsumer
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
source.exclude_dirs = .git,.github,bin,.buildozer
version = 2.1.0
requirements = python3,kivy
p4a.bootstrap = sdl2
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,ACCESS_NETWORK_STATE
android.api = 34
android.minapi = 21
android.archs = arm64-v8a
android.allow_backup = True
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 0
