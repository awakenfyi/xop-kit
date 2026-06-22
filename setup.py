from setuptools import setup, find_packages

setup(
    name="xop-kit",
    version="0.2.0",
    description="xOP Kit — reference implementation of the xOP Standard",
    author="Lyra Labs",
    author_email="sage@artist.fyi",
    url="https://github.com/awakenfyi/xop-kit",
    packages=find_packages(),
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
