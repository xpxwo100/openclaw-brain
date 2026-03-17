from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="openclaw-brain",
    version="0.1.0",
    author="OpenClaw Brain Contributors",
    author_email="openclaw-brain@example.com",
    description="🧠 类脑记忆系统 for OpenClaw - 模拟人脑的多层级记忆、注意力门控与记忆巩固机制",
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
        "openclaw>=2026.3.13",
        "lancedb>=0.5.0",
        "sentence-transformers>=2.3.0",
        "pyyaml>=6.0",
        "numpy>=1.24.0",
        "python-dateutil>=2.8.2",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "ruff>=0.1.0",
            "mkdocs>=1.5.0",
            "mkdocs-material>=9.0.0",
        ],
    },
)
