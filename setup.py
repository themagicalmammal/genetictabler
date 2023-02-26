import codecs
import os

from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))

with codecs.open(os.path.join(here, "README.md"), encoding="utf-8") as fh:
    LONG_DESCRIPTION = "\n" + fh.read()

VERSION = "2.0.3"
DESCRIPTION = "A time table scheduler using Genetic algorithm(s)."

# Setting up
setup(
    name="genetictabler",
    version=VERSION,
    # Authors: Ashish Shah (avinavashish008@gmail.com)
    # PyPI does not have an easy way to specify multiple authors.
    author="Dipan Nanda",
    author_email="d19cyber@gmail.com",
    description=DESCRIPTION,
    long_description_content_type="text/markdown",
    long_description=LONG_DESCRIPTION,
    packages=find_packages(),
    include_package_data=True,
    license="GPLv3",
    install_requires=[],
    project_urls={
        "Source code": "https://github.com/themagicalmammal/genetictabler",
        "Documentation":
        "https://github.com/themagicalmammal/genetictabler/blob/main/README.md",
        "Bug tracker":
        "https://github.com/themagicalmammal/genetictabler/issues",
    },
    keywords=[
        "python",
        "geneticalgorithm",
        "genetics",
        "genes",
        "chromosomes",
        "timetable",
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Operating System :: Unix",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Topic :: Utilities",
    ],
)
