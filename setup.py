from setuptools import setup
import packagepoa


with open("README.md") as fp:
    README = fp.read()


setup(
    name="packagepoa",
    version=packagepoa.__version__,
    description="Generate, transform and assemble files for a PoA article.",
    long_description=README,
    long_description_content_type="text/markdown",
    packages=["packagepoa"],
    license="MIT",
    install_requires=["configparser"],
    url="https://github.com/elifesciences/package-poa",
    maintainer="eLife Sciences Publications Ltd.",
    maintainer_email="tech-team@elifesciences.org",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
)
