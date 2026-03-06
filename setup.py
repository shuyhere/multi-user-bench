from setuptools import find_packages, setup

setup(
    name="muses_bench",
    version="0.1.0",
    description="Muses-Bench: A Benchmark for Multi-User LLM Agents",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "openai",
        "numpy",
        "termcolor",
        "litellm>=1.41.0",
    ],
)
