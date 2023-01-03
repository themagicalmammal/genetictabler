import codecs
import os

from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))

with codecs.open(os.path.join(here, "README.md"), encoding="utf-8") as fh:
    LONG_DESCRIPTION = "\n" + fh.read()

VERSION = "1.0.7"
DESCRIPTION = "A time table scheduler using Genetic algorithm(s)."

# Setting up
setup(
    name="genetictabler",
    version=VERSION,
    author="Dipan Nanda, Ashish Shah",
    author_email="d19cyber@gmail.com, avinavashish008@gmail.com",
    description=DESCRIPTION,
    long_description_content_type="text/markdown",
    long_description=LONG_DESCRIPTION,
    url="https://github.com/themagicalmammal/genetictabler",
    packages=find_packages(),
    include_package_data=True,
    license="GPLv3",
    install_requires=[],
    project_urls={
        "Website": "https://github.com/themagicalmammal/genetictabler",
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
        "Intended Audience :: System Administrators",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Operating System :: Unix",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Topic :: Utilities",
    ],
)
