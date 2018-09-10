from distutils.core import setup

setup(
    name="hubbub_a_loosh",
    version=0.1,
    packages=['hub'],
    license='Creative Commons Attribution-Noncommercial-Share Alike license',
    long_description=open('README.md').read(),
    install_requires=open('requirements.txt').read().split('\n'),
)
