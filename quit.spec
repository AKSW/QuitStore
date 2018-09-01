# -*- mode: python -*-

block_cipher = None

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules('rdflib.plugins')
hiddenimports.append('quit.tools.processor')

a = Analysis(['quit/run.py'],
             pathex=['.'],
             binaries=[],
             datas=[('quit/web/templates/*', 'quit/web/templates/'), ('quit/web/static/css/*', 'quit/web/static/css'), ('quit/web/static/fonts/*', 'quit/web/static/fonts'), ('quit/web/static/js/*', 'quit/web/static/js')],
             hiddenimports=hiddenimports,
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='run',
          debug=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=True )