# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(['scripts\\clinttools'],
             pathex=['C:\\msys64\\home\\clint\\src\\clinttools\\src'],
             binaries=[
                 ('engine/*.exe', 'engine'),
                 ('engine/*.pdb', 'engine'),
                 ('engine/*.dll', 'engine')
             ],
             datas=[
                 ('meta.json', '.'),
                 ('COMMIT', '.')
             ],
             hiddenimports=[],
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
          a.binaries,
          Tree('files', prefix='files\\'),
          a.zipfiles,
          a.datas,
          [],
          name='clinttools',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          icon='files\\share\\pixmaps\clinttools.ico',
          entitlements_file=None )
