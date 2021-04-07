from setuptools import setup, find_packages
from glob import glob


def find_scripts(pkgs):
    ret = []
    for pkgname in pkgs:
        ret.extend(glob(pkgname + '/scripts/*.py'))
    return ret


pkgs = find_packages()
scripts = find_scripts(pkgs)

NAME = "serverlib"
setup(
    name=NAME,
    packages=find_packages(),
    include_package_data=True,
    version='21.04.05.0',
    license='GNU GPLv3',
    platforms='any',
    description='Package to develop write asynchronoys servers and clients using 0MQ',
    author='Julio Trevisan',
    author_email='juliotrevisan@gmail.com',
    url=f'https://github.com/trevisanj/{NAME}',
    keywords= ['wisdom'],
    install_requires=["a107"],
    python_requires = '>=3',
    scripts=scripts
)
