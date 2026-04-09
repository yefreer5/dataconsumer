[app]
title = Data Consumer
package.name = dataconsumer
package.domain = org.dataconsumer
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
source.exclude_dirs = .git,.github,bin,.buildozer
version = 1.2.0
requirements = python3,kivy
p4a.bootstrap = sdl2
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,ACCESS_NETWORK_STATE
android.api = 35
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
android.allow_backup = True
android.accept_sdk_license = True
p4a.branch = develop

[buildozer]
log_level = 2
warn_on_root = 0
