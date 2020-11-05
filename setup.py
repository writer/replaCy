import os
from typing import List

from setuptools import setup, find_packages
from setuptools.command.install import install

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

with open(os.path.join(here, "VERSION"), encoding="utf-8") as f:
    __version__ = f.read().strip()
    with open(os.path.join(here, "replacy", "version.py"), "w+", encoding="utf-8") as v:
        v.write("# CHANGES HERE HAVE NO EFFECT: ../VERSION is the source of truth\n")
        v.write(f'__version__ = "{__version__}"')
"""
requirementPath = os.path.abspath("./requirements.txt")
install_requires: List[str] = []
if os.path.isfile(requirementPath):
    with open(requirementPath) as f:
        install_requires = f.read().splitlines()
"""
setup(
    name="replacy",
    description="ReplaCy = spaCy Matcher + pyInflect. Create rules, correct sentences.",
    packages=find_packages(),
    package_data={"replacy": ["resources/*"]},
    include_package_data=True,
    author="Qordoba",
    author_email="Sam Havens <sam.havens@qordoba.com>, Melisa Stal <melisa@qordoba.com>",
    url="https://github.com/Qordobacode/replaCy",
    version=__version__,
    license="MIT",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=["pyfunctional>=1.2.0", "jsonschema>=2.6.0", "lemminflect==0.2.1"],
    python_requires=">=3.5",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Text Processing :: Linguistic",
        "Typing :: Typed",
    ],
)
