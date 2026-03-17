from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="openclaw-brain",
    version="0.2.0",
    author="OpenClaw Brain Contributors",
    author_email="openclaw-brain@example.com",
    description="Refactored multi-layer memory system for OpenClaw",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/openclaw/openclaw-brain",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.9",
    install_requires=[
        "lancedb>=0.5.0",
        "sentence-transformers>=2.3.0",
        "pyyaml>=6.0",
        "numpy>=1.24.0",
        "python-dateutil>=2.8.2",
    ],
    extras_require={
        "openclaw": [
            "openclaw>=2026.3.13",
        ],
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "ruff>=0.1.0",
            "mkdocs>=1.5.0",
            "mkdocs-material>=9.0.0",
        ]
    },
}
