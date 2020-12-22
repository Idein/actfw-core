from setuptools import setup, find_packages
import os

exec(open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'actfw_core', '_version.py')).read())

with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

name = 'actfw-core'
author = 'Idein Inc.'

setup(
    name=name,
    version=__version__,
    description='Core components of actfw, independent of specific devices',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/Idein/actfw-core',
    author=author,
    author_email='n.ohkawa@idein.jp, sho.nakatani@idein.jp',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3 :: Only',
    ],
    keywords='actcast',
    packages=find_packages(),
    install_requires=['Pillow'],
)
