"""
ARCHITECTURE OWNERSHIP:
=====================

What owns this?
- model_dict.json (available models)
- ollama.yaml (Ollama configuration)

What can import this?
- infra/llm/ (LLM integration)
- domain/ai/ (AI providers)
- runtime/ (model selection)

What imports it?
- infra/llm/llm_fallback_generator.py
- domain/ai/llm/provider.py
- runtime/launchers/bootstrap.py

Is it active or deprecated?
- ACTIVE: All model systems
- DEPRECATED: None

Is it runtime-critical?
- CRITICAL: model_dict.json
- SEMI-CRITICAL: ollama.yaml
- Failure here = no model configuration
"""
