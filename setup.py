from setuptools import setup, find_packages

setup(
    name="xop-kit",
    version="0.2.0",
    description="xOP Kit — reference implementation of the xOP Standard",
    author="Morgan Sage Norman",
    author_email="hello@awaken.fyi",
    url="https://github.com/awakenfyi/xop-kit",
    # C2 fix: cli.py and orchestrator.py are top-level modules that find_packages()
    # misses. py_modules includes them so non-editable installs work. tests is
    # excluded so it doesn't ship as an installed top-level package.
    packages=find_packages(exclude=["tests", "tests.*"]),
    py_modules=["cli", "orchestrator"],
    include_package_data=True,
    package_data={
        "": ["*.md", "*.json", "*.jsonl"],
    },
    entry_points={
        "console_scripts": [
            "xop=cli:main",
        ],
    },
    license="MIT",
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Topic :: Software Development :: Quality Assurance",
        "Programming Language :: Python :: 3",
    ],
)
