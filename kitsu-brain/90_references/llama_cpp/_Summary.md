# Llama.cpp Reference Summary

## What this system does
Llama.cpp is a high-performance C++ library for running Large Language Models (LLMs) locally on CPU/GPU. It provides:
- GGUF model format support
- Efficient inference optimization
- Cross-platform compatibility
- Model quantization and conversion tools

## What parts are relevant to Kitsu
- **Model Loading**: Kitsu uses llama.cpp for local LLM inference
- **Performance Optimization**: Quantization techniques for running on low-end hardware
- **GGUF Format**: Standard model format for Kitsu's LLM layer
- **Memory Management**: Dynamic loading/unloading strategies

## What can be ignored
- Build system internals (CMake, Makefiles)
- Development tooling and CI/CD
- Model training scripts (Kitsu uses inference only)
- Hardware-specific optimizations not relevant to target platforms
- Contributing guidelines and development workflows

## Key Integration Points
- Model loading through GGUF interface
- Memory management for tier-based capability system
- Performance optimization for ultra-low and balanced modes
