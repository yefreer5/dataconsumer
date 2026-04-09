[app]
title = Data Consumer
package.name = dataconsumer
package.domain = org.dataconsumer
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0.0
requirements = python3,kivy
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,ACCESS_NETWORK_STATE
android.api = 33
android.minapi = 21
android.archs = arm64-v8a
android.allow_backup = True
p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 0
