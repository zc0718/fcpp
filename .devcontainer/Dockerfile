FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ cmake ninja-build clang clang-format clang-tidy \
    python3 python3-pip python3-venv nodejs npm \
    doxygen graphviz lcov jq \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --break-system-packages conan \
    && conan profile detect --force
