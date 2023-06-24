# -*- mode: python ; coding: utf-8 -*-
import os
import platform
ARCH = platform.machine()


block_cipher = None

BINARIES = [
 ('engine/clinttools-engine', 'engine'),
 ('engine/*.dylib', '.'),
 ('engine/rubberband', 'engine'),
 ('engine/clinttools-soundstretch', 'engine'),
 ('engine/sbsms', 'engine'),
]

a = Analysis(['scripts/clinttools'],
             pathex=[
                 os.path.dirname(SPECPATH),
             ],
             binaries=BINARIES,
             datas=[
                 ('meta.json', '.'),
                 ('COMMIT', '.'),
                 ('files/', 'files'),
             ],
             hiddenimports=[
                 'sglib',
                 'sgui',
                 'logging',
                 'numpy',
                 'PyQt6',
                 'jinja2',
                 'mido',
                 'mutagen',
                 'psutil',
                 'pymarshal',
                 'wavefile',
                 'yaml',
             ],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='clinttools',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None )

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='clinttools')
app = BUNDLE(coll,
             name='Clint Tools DAW.app',
             icon='macos/clinttools.icns',
             bundle_identifier='io.github.clinttoolsaudio')
