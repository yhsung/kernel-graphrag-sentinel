"""
LLM-Powered Report Generator
Generates human-readable impact analysis reports using LLMs.
"""

import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """LLM configuration."""
    provider: str  # openai, gemini, anthropic, ollama
    model: str
    api_key: Optional[str]
    temperature: float = 0.7


class LLMReporter:
    """Generates natural language reports using LLMs."""

    def __init__(self, config: LLMConfig):
        """
        Initialize LLM reporter.

        Args:
            config: LLM configuration
        """
        self.config = config
        self.client = None

        # Initialize appropriate client
        if config.provider == "gemini":
            self._init_gemini()
        elif config.provider == "openai":
            self._init_openai()
        elif config.provider == "anthropic":
            self._init_anthropic()
        elif config.provider == "ollama":
            self._init_ollama()
        else:
            raise ValueError(f"Unsupported LLM provider: {config.provider}")

    def _init_gemini(self):
        """Initialize Google Gemini client."""
        try:
            import google.generativeai as genai

            api_key = self.config.api_key or os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("Gemini API key not found. Set GEMINI_API_KEY environment variable.")

            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(self.config.model)
            logger.info(f"Initialized Gemini client with model: {self.config.model}")
        except ImportError:
            raise ImportError("google-generativeai not installed. Run: pip install google-generativeai")

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

            self.client = {"base_url": base_url, "model": self.config.model}
            logger.info(f"Initialized Ollama client with model: {self.config.model}")
        except ImportError:
            raise ImportError("requests not installed. Run: pip install requests")

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
        """Create prompt for LLM."""
        prompt = f"""You are analyzing Linux kernel code changes. A developer is planning to modify the function `{function_name}`.

Based on the following impact analysis data, generate a comprehensive, professional report that helps the developer understand:
1. What code will be affected by this change
2. What tests need to be run
3. What new tests might be needed
4. The overall risk level and why
5. Recommendations for safely implementing this change

Impact Analysis Data:
{context}

Generate a clear, well-structured report in {format} format. Be concise but thorough. Focus on actionable insights.

Report:"""
        return prompt

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM API."""
        if self.config.provider == "gemini":
            return self._call_gemini(prompt)
        elif self.config.provider == "openai":
            return self._call_openai(prompt)
        elif self.config.provider == "anthropic":
            return self._call_anthropic(prompt)
        elif self.config.provider == "ollama":
            return self._call_ollama(prompt)
        else:
            raise ValueError(f"Unsupported provider: {self.config.provider}")

    def _call_gemini(self, prompt: str) -> str:
        """Call Google Gemini API."""
        try:
            response = self.client.generate_content(
                prompt,
                generation_config={
                    "temperature": self.config.temperature,
                    "max_output_tokens": 2048,
                }
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            raise

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API."""
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": "You are a Linux kernel code analysis expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config.temperature,
                max_tokens=2048
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise

    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic Claude API."""
        try:
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=2048,
                temperature=self.config.temperature,
                messages=[
                    {"role": "user", "content": prompt}
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


# Convenience function
def generate_llm_report(impact_result, provider: str = "gemini",
                       model: str = "gemini-2.0-flash-exp",
                       api_key: Optional[str] = None) -> str:
    """
    Convenience function to generate LLM report.

    Args:
        impact_result: ImpactResult object from ImpactAnalyzer
        provider: LLM provider (gemini, openai, anthropic, ollama)
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
    print("Available providers: gemini, openai, anthropic, ollama")

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
