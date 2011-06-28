from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext

setup(name='Cryp',
      version='0.2',
      description='Simple password management application',
      author='Paul Colomiets',
      author_email='pc@gafol.net',
      url='svn://svn.gafol.net/cryp/',
      packages=['cryp'],
      scripts=['scripts/cryp', 'scripts/cryp-cli', 'scripts/cryp-backup'],
      cmdclass={'build_ext': build_ext},
      ext_modules=[
        Extension("cryp._cipher", ["cryp/_cipher.pyx"], libraries=['crypto']),
        ],
    )
