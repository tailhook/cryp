from distutils.core import setup

setup(name='Cryp',
      version='0.2',
      description='Simple password management application',
      author='Paul Colomiets',
      author_email='pc@gafol.net',
      url='svn://svn.gafol.net/cryp/',
      packages=['cryp'],
      scripts=['scripts/cryp', 'scripts/cryp-cli', 'scripts/cryp-backup']
    )
