"""
LLM-Powered Report Generator
Generates human-readable impact analysis reports using LLMs.
"""

import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

from .graph_exporter import GraphExporter

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """LLM configuration."""
    provider: str  # openai, gemini, anthropic, ollama, lmstudio
    model: str
    api_key: Optional[str]
    temperature: float = 0.7


class LLMReporter:
    """Generates natural language reports using LLMs."""

    def __init__(self, config: LLMConfig, graph_store=None):
        """
        Initialize LLM reporter.

        Args:
            config: LLM configuration
            graph_store: Optional Neo4j graph store for diagram generation
        """
        self.config = config
        self.client = None
        self.graph_store = graph_store
        self.graph_exporter = GraphExporter(graph_store) if graph_store else None

        # Initialize appropriate client
        if config.provider == "gemini":
            self._init_gemini()
        elif config.provider == "openai":
            self._init_openai()
        elif config.provider == "anthropic":
            self._init_anthropic()
        elif config.provider == "ollama":
            self._init_ollama()
        elif config.provider == "lmstudio":
            self._init_lmstudio()
        else:
            raise ValueError(f"Unsupported LLM provider: {config.provider}")

    def _init_gemini(self):
        """Initialize Google Gemini client."""
        try:
            from google import genai

            api_key = self.config.api_key or os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("Gemini API key not found. Set GEMINI_API_KEY environment variable.")

            self.client = genai.Client(api_key=api_key)
            logger.info(f"Initialized Gemini client with model: {self.config.model}")
        except ImportError:
            raise ImportError("google-genai not installed. Run: pip install google-genai")

    def _init_openai(self):
        """Initialize OpenAI client."""
        try:
            from openai import OpenAI

            api_key = self.config.api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")

            self.client = OpenAI(api_key=api_key)
            logger.info(f"Initialized OpenAI client with model: {self.config.model}")
        except ImportError:
            raise ImportError("openai not installed. Run: pip install openai")

    def _init_anthropic(self):
        """Initialize Anthropic Claude client."""
        try:
            from anthropic import Anthropic

            api_key = self.config.api_key or os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable.")

            self.client = Anthropic(api_key=api_key)
            logger.info(f"Initialized Anthropic client with model: {self.config.model}")
        except ImportError:
            raise ImportError("anthropic not installed. Run: pip install anthropic")

    def _init_ollama(self):
        """Initialize Ollama client (local LLM)."""
        try:
            import requests

            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            # Test connection
            response = requests.get(f"{base_url}/api/tags")
            if response.status_code != 200:
                raise ConnectionError(f"Cannot connect to Ollama at {base_url}")

            self.client = {"base_url": base_url, "model": self.config.model, "provider": "ollama"}
            logger.info(f"Initialized Ollama client with model: {self.config.model}")
        except ImportError:
            raise ImportError("requests not installed. Run: pip install requests")

    def _init_lmstudio(self):
        """Initialize LM Studio client (local LLM with OpenAI-compatible API)."""
        try:
            from openai import OpenAI

            base_url = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")

            # Create OpenAI client pointing to LM Studio
            self.client = OpenAI(
                base_url=base_url,
                api_key="lm-studio"  # LM Studio doesn't require a real API key
            )

            # Store additional metadata
            self.client._lmstudio_metadata = {
                "base_url": base_url,
                "model": self.config.model,
                "provider": "lmstudio"
            }

            logger.info(f"Initialized LM Studio client at {base_url} with model: {self.config.model}")
        except ImportError:
            raise ImportError("openai not installed. Run: pip install openai")

    def generate_impact_report(self, impact_data: Dict[str, Any],
                               function_name: str,
                               format: str = "markdown") -> str:
        """
        Generate human-readable impact analysis report using LLM.

        Args:
            impact_data: Impact analysis data from ImpactAnalyzer
            function_name: Name of the function being analyzed
            format: Output format (markdown, text, html)

        Returns:
            LLM-generated report string
        """
        # Build context from impact data
        context = self._build_context(impact_data, function_name)

        # Create prompt
        prompt = self._create_prompt(context, function_name, format)

        # Generate report
        try:
            report = self._call_llm(prompt)
            logger.info(f"Generated LLM report for {function_name} using {self.config.provider}")
            return report
        except Exception as e:
            logger.error(f"LLM report generation failed: {e}")
            return f"Error generating LLM report: {str(e)}"

    def _build_context(self, impact_data: Dict[str, Any], function_name: str) -> str:
        """Build context string from impact data."""
        lines = []

        lines.append(f"Function: {function_name}")
        lines.append(f"File: {impact_data.get('file_path', 'unknown')}")
        lines.append("")

        # Add Mermaid call graph visualization if graph exporter is available
        if self.graph_exporter:
            try:
                mermaid_diagram = self.graph_exporter.generate_mermaid_for_impact(impact_data)
                lines.append("Call Graph Visualization:")
                lines.append(mermaid_diagram)
                lines.append("")
                lines.append("(Note: Include this Mermaid diagram in your report)")
                lines.append("")
            except Exception as e:
                logger.warning(f"Failed to generate Mermaid diagram: {e}")

        # Statistics
        stats = impact_data.get('stats', {})
        lines.append("Statistics:")
        lines.append(f"  - Direct callers: {stats.get('direct_callers', 0)}")
        lines.append(f"  - Indirect callers: {stats.get('indirect_callers', 0)}")
        lines.append(f"  - Direct callees: {stats.get('direct_callees', 0)}")
        lines.append(f"  - Indirect callees: {stats.get('indirect_callees', 0)}")
        lines.append(f"  - Direct tests: {stats.get('direct_tests', 0)}")
        lines.append(f"  - Indirect tests: {stats.get('indirect_tests', 0)}")
        lines.append("")

        # Direct callers sample
        direct_callers = impact_data.get('direct_callers', [])
        if direct_callers:
            lines.append(f"Sample Direct Callers (showing {min(10, len(direct_callers))} of {len(direct_callers)}):")
            for caller in direct_callers[:10]:
                lines.append(f"  - {caller.get('name', 'unknown')} ({caller.get('file', 'unknown')})")
            lines.append("")

        # Test coverage
        direct_tests = impact_data.get('direct_tests', [])
        if direct_tests:
            lines.append("Direct Test Coverage:")
            for test in direct_tests:
                lines.append(f"  - {test.get('name', 'unknown')}")
            lines.append("")
        else:
            lines.append("⚠️ No direct test coverage found")
            lines.append("")

        # Risk assessment
        risk_level = impact_data.get('risk_level', 'UNKNOWN')
        lines.append(f"Current Risk Level: {risk_level}")

        return "\n".join(lines)

    def _create_prompt(self, context: str, function_name: str, format: str) -> str:
        """Create prompt for LLM using structured system prompt."""
        # Professional system prompt based on high-quality Anthropic reports
        system_prompt = """You are a Linux kernel code analysis expert specializing in impact analysis and risk assessment. Your task is to generate comprehensive, professional impact analysis reports for developers planning to modify Linux kernel code.

# Report Structure

Generate reports following this exact structure:

## 1. HEADER SECTION
- Report title: "Impact Analysis Report: `<function_name>()` Function Modification"
- File path and function name
- Report date
- Risk level with color-coded emoji:
  - 🟢 LOW: Isolated changes, good test coverage, minimal dependencies
  - 🟡 MEDIUM: Moderate impact, some test coverage, standard dependencies
  - 🔴 HIGH: Public interfaces, no tests, or high call frequency
  - ⚫ CRITICAL: Core infrastructure, ABI/API changes, system-wide impact

## 2. EXECUTIVE SUMMARY (2-3 sentences)
Concise overview covering:
- Function's role and importance
- Test coverage status
- Key risk factors
- Nature of the interface (internal/public)

## 3. CODE IMPACT ANALYSIS

### 3.1 Affected Components Table
| Component | Impact | Details |
|-----------|--------|---------|
| **Direct Callers** | [LOW/MEDIUM/HIGH] | Number and description |
| **Indirect Callers** | [LOW/MEDIUM/HIGH] | Depth and breadth of impact |
| **Public Interface** | [NONE/LOW/CRITICAL] | User-facing implications |
| **Dependent Code** | [LOW/MEDIUM/HIGH] | External dependencies |

### 3.2 Scope of Change
- Entry points count
- Call sites frequency
- Abstraction layers
- Visibility (internal/external/public)

Include the call graph visualization if provided in the context.

## 4. TESTING REQUIREMENTS

### 4.1 Existing Test Coverage
Use checkmarks and warning symbols:
- ✅ Direct unit tests found
- ✅ Integration tests identified
- ❌ No direct tests
- ⚠️ Partial coverage

### 4.2 Mandatory Tests to Run
Provide specific, executable commands organized by category:

#### Functional Tests
```bash
# Concrete commands to verify functionality
```

#### Regression Tests
- Specific test paths or commands
- Subsystem-specific tests

## 5. RECOMMENDED NEW TESTS

### 5.1 Unit Tests (Priority Level)
Provide specific test case names and purposes:
```c
// Concrete test cases needed
```

## 6. RISK ASSESSMENT

### Risk Level: [Emoji] [LEVEL]

**Justification Table:**
| Risk Factor | Severity | Reason |
|------------|----------|--------|
| **[Factor]** | [LEVEL] | Specific reason |

### Potential Failure Modes
Enumerate 3-5 specific failure scenarios with consequences.

## 7. IMPLEMENTATION RECOMMENDATIONS

### Phase-by-Phase Checklist
Organize as actionable phases with checkboxes (Phase 1-4: Preparation, Development, Testing, Validation).

## 8. ESCALATION CRITERIA
**Stop and escalate if:** List specific conditions.

## 9. RECOMMENDATIONS SUMMARY
Table with Priority, Action, Owner columns.

## 10. CONCLUSION
2-3 sentences with clear recommendation.

# Writing Guidelines
- Be specific with file paths, commands, line numbers
- Be actionable with executable commands
- Use tables, checkboxes, clear formatting
- Prioritize with CRITICAL/HIGH/MEDIUM/LOW
- Focus on "why" not just "what"
- Professional, direct, risk-aware tone"""

        # User message with impact analysis data
        user_message = f"""Analyze this Linux kernel function modification:

Function: {function_name}

Impact Analysis Data:
{context}

Generate a comprehensive impact analysis report in {format} format following the structured template."""

        # Return both parts (system + user) as a single prompt for compatibility
        # Some providers will use this in messages array, others as single prompt
        return f"{system_prompt}\n\n---\n\n{user_message}"

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM API."""
        # Extract system prompt and user message from combined prompt
        # Format: "system_prompt\n\n---\n\nuser_message"
        parts = prompt.split("\n\n---\n\n", 1)
        if len(parts) == 2:
            system_msg, user_msg = parts
        else:
            # Fallback: treat entire prompt as user message
            system_msg = "You are a Linux kernel code analysis expert."
            user_msg = prompt

        if self.config.provider == "gemini":
            return self._call_gemini(user_msg)  # Gemini doesn't use system messages
        elif self.config.provider == "openai":
            return self._call_openai_with_system(system_msg, user_msg)
        elif self.config.provider == "anthropic":
            return self._call_anthropic_with_system(system_msg, user_msg)
        elif self.config.provider == "ollama":
            return self._call_ollama(user_msg)  # Ollama uses simple prompt
        elif self.config.provider == "lmstudio":
            return self._call_lmstudio_with_system(system_msg, user_msg)
        else:
            raise ValueError(f"Unsupported provider: {self.config.provider}")

    def _call_gemini(self, prompt: str) -> str:
        """Call Google Gemini API."""
        try:
            from google import genai

            # Gemini 2.0/3.0 Flash supports up to 8192 output tokens
            response = self.client.models.generate_content(
                model=self.config.model,
                contents=prompt,
                config=genai.GenerateContentConfig(
                    temperature=self.config.temperature,
                    max_output_tokens=8192,
                )
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            raise

    def _call_openai_with_system(self, system_msg: str, user_msg: str) -> str:
        """Call OpenAI API with system and user messages."""
        try:
            # Build request parameters
            # Reasoning models (gpt-5, o1) need more tokens as they use tokens for thinking
            max_tokens = 16384 if "gpt-5" in self.config.model or "o1" in self.config.model else 2048

            params = {
                "model": self.config.model,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg}
                ],
                "max_completion_tokens": max_tokens
            }

            # Some models (e.g., gpt-5-nano) only support default temperature=1
            # Only include temperature if it's not the default
            if self.config.temperature != 1.0:
                params["temperature"] = self.config.temperature

            response = self.client.chat.completions.create(**params)
            content = response.choices[0].message.content
            if not content:
                logger.warning(f"OpenAI returned empty content. Response: {response}")
                return "Error: LLM returned empty response"
            return content
        except Exception as e:
            # If temperature is not supported, retry without it
            if "temperature" in str(e) and "not support" in str(e).lower():
                logger.warning(f"Model {self.config.model} doesn't support custom temperature, retrying with default")
                # Use same token limit as above
                max_tokens = 16384 if "gpt-5" in self.config.model or "o1" in self.config.model else 2048
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_msg}
                    ],
                    max_completion_tokens=max_tokens
                )
                content = response.choices[0].message.content
                if not content:
                    logger.warning(f"OpenAI returned empty content on retry. Response: {response}")
                    return "Error: LLM returned empty response"
                return content

            logger.error(f"OpenAI API call failed: {e}")
            raise

    def _call_anthropic_with_system(self, system_msg: str, user_msg: str) -> str:
        """Call Anthropic Claude API with system and user messages."""
        try:
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=4096,  # Increased for detailed reports
                temperature=self.config.temperature,
                system=system_msg,  # Anthropic uses 'system' parameter
                messages=[
                    {"role": "user", "content": user_msg}
                ]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
            raise

    def _call_ollama(self, prompt: str) -> str:
        """Call Ollama (local LLM) API."""
        try:
            import requests

            base_url = self.client["base_url"]
            model = self.client["model"]

            response = requests.post(
                f"{base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.config.temperature
                    }
                }
            )
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            logger.error(f"Ollama API call failed: {e}")
            raise

    def _call_lmstudio_with_system(self, system_msg: str, user_msg: str) -> str:
        """Call LM Studio (local LLM with OpenAI-compatible API)."""
        try:
            # LM Studio uses OpenAI-compatible API
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg}
                ],
                temperature=self.config.temperature,
                max_tokens=4096  # Increased for detailed reports
            )
            content = response.choices[0].message.content
            if not content:
                logger.warning(f"LM Studio returned empty content. Response: {response}")
                return "Error: LM Studio returned empty response"
            return content
        except Exception as e:
            logger.error(f"LM Studio API call failed: {e}")
            raise


# Convenience function
def generate_llm_report(impact_result, provider: str = "gemini",
                       model: str = "gemini-2.0-flash-exp",
                       api_key: Optional[str] = None) -> str:
    """
    Convenience function to generate LLM report.

    Args:
        impact_result: ImpactResult object from ImpactAnalyzer
        provider: LLM provider (gemini, openai, anthropic, ollama, lmstudio)
        model: Model name
        api_key: API key (optional, uses env var if not provided)

    Returns:
        Generated report string
    """
    config = LLMConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        temperature=0.7
    )

    reporter = LLMReporter(config)

    # Convert ImpactResult to dict format
    impact_data = {
        "file_path": impact_result.target_file,
        "stats": impact_result.stats,
        "direct_callers": impact_result.direct_callers,
        "indirect_callers": impact_result.indirect_callers,
        "direct_callees": impact_result.direct_callees,
        "indirect_callees": impact_result.indirect_callees,
        "direct_tests": impact_result.direct_tests,
        "indirect_tests": impact_result.indirect_tests,
        "risk_level": impact_result.stats.get('risk_level', 'UNKNOWN')
    }

    return reporter.generate_impact_report(
        impact_data,
        impact_result.target_function
    )


if __name__ == "__main__":
    # Test LLM reporter
    print("LLM Reporter Module")
    print("Available providers: gemini, openai, anthropic, ollama, lmstudio")

    # Example usage
    test_config = LLMConfig(
        provider="gemini",
        model="gemini-2.0-flash-exp",
        api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.7
    )

    try:
        reporter = LLMReporter(test_config)
        print(f"✅ Successfully initialized {test_config.provider} reporter")
    except Exception as e:
        print(f"❌ Failed to initialize reporter: {e}")
