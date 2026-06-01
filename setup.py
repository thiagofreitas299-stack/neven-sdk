"""
NEVEN TECH — Setup Script (backward compatibility)
Use pyproject.toml for modern installations.
"""

from setuptools import setup, find_packages

setup(
    name="neven",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.100.0",
        "uvicorn[standard]>=0.23.0",
        "pydantic>=2.0.0",
        "requests>=2.28.0",
        "numpy>=1.24.0",
        "websockets>=11.0",
    ],
    entry_points={
        "console_scripts": [
            "neven=neven.cli.main:main",
        ],
    },
    python_requires=">=3.9",
    author="NEVEN Technologies",
    author_email="engineering@neventech.com",
    description="The Physical World Runtime — Connect AI agents to physical infrastructure",
    url="https://neventech.com",
)
