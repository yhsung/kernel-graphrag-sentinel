"""
LLM-Powered Report Generator
Generates human-readable impact analysis reports using LLMs.
"""

import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path

from .graph_exporter import GraphExporter

logger = logging.getLogger(__name__)

# Path to system prompt files
DOCS_DIR = Path(__file__).parent.parent.parent / "docs"
SYSTEM_PROMPT_FILE = DOCS_DIR / "llm_report_system_prompt.md"
AUTOMOTIVE_PROMPT_FILE = DOCS_DIR / "llm_automotive_safety_prompt.md"


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

        # Load system prompts (KV-cache optimized)
        self._system_prompt_base = self._load_system_prompt()
        self._automotive_extension = self._load_automotive_prompt()

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

    def _load_system_prompt(self) -> str:
        """Load base system prompt from documentation file."""
        try:
            if not SYSTEM_PROMPT_FILE.exists():
                logger.warning(f"System prompt file not found: {SYSTEM_PROMPT_FILE}, using fallback")
                return self._get_fallback_system_prompt()

            with open(SYSTEM_PROMPT_FILE, 'r') as f:
                content = f.read()

            # Extract content between ``` markers
            start = content.find("```\n")
            if start == -1:
                logger.warning("Could not find system prompt markers, using fallback")
                return self._get_fallback_system_prompt()

            start += 4  # Skip past ```\n
            end = content.rfind("\n```")
            if end == -1:
                logger.warning("Could not find closing prompt marker, using fallback")
                return self._get_fallback_system_prompt()

            system_prompt = content[start:end]
            logger.info(f"Loaded system prompt from {SYSTEM_PROMPT_FILE} ({len(system_prompt)} chars)")
            return system_prompt

        except Exception as e:
            logger.error(f"Failed to load system prompt: {e}, using fallback")
            return self._get_fallback_system_prompt()

    def _load_automotive_prompt(self) -> str:
        """Load automotive safety extension prompt."""
        try:
            if not AUTOMOTIVE_PROMPT_FILE.exists():
                logger.warning(f"Automotive prompt file not found: {AUTOMOTIVE_PROMPT_FILE}")
                return ""

            with open(AUTOMOTIVE_PROMPT_FILE, 'r') as f:
                content = f.read()

            # Extract Section 11 content
            start = content.find("## 11. AUTOMOTIVE SAFETY ANALYSIS")
            if start == -1:
                logger.warning("Could not find automotive section marker")
                return ""

            end = content.find("# End of Automotive Safety Extension")
            if end == -1:
                logger.warning("Could not find automotive section end marker")
                return ""

            automotive_section = content[start:end].strip()
            logger.info(f"Loaded automotive extension ({len(automotive_section)} chars)")
            return automotive_section

        except Exception as e:
            logger.error(f"Failed to load automotive prompt: {e}")
            return ""

    def _get_fallback_system_prompt(self) -> str:
        """Fallback system prompt if file loading fails."""
        return """You are a Linux kernel code analysis expert specializing in impact analysis and risk assessment. Your task is to generate comprehensive, professional impact analysis reports for developers planning to modify Linux kernel code.

Generate reports with these sections:
1. Header with risk level (🟢 LOW, 🟡 MEDIUM, 🔴 HIGH, ⚫ CRITICAL)
2. Executive Summary
3. Code Impact Analysis (with Mermaid diagram if provided)
4. Testing Requirements
5. Recommended New Tests
6. Risk Assessment
7. Implementation Recommendations
8. Escalation Criteria
9. Recommendations Summary
10. Conclusion

Be specific with file paths, commands, and line numbers. Use tables and checkboxes. Prioritize with CRITICAL/HIGH/MEDIUM/LOW."""

    def _is_automotive_context(self, context: str) -> bool:
        """Detect if context requires automotive safety analysis."""
        automotive_keywords = [
            "automotive", "embedded", "real-time", "safety-critical",
            "iso 26262", "iso 21434", "aspice", "asil",
            "ecu", "autosar", "misra", "functional safety",
            "wcet", "timing analysis", "hard real-time"
        ]
        context_lower = context.lower()
        is_automotive = any(keyword in context_lower for keyword in automotive_keywords)

        if is_automotive:
            logger.info("Automotive context detected, will include safety analysis section")

        return is_automotive

    def _build_system_prompt(self, context: str) -> str:
        """Build system prompt with optional automotive extension (KV-cache optimized)."""
        system_prompt = self._system_prompt_base

        # Append automotive extension if needed
        if self._is_automotive_context(context):
            if self._automotive_extension:
                system_prompt += "\n\n" + self._automotive_extension
            else:
                logger.warning("Automotive context detected but extension not loaded")

        return system_prompt

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
                lines.append("=" * 60)
                lines.append("CALL GRAPH VISUALIZATION (Mermaid Format)")
                lines.append("=" * 60)
                lines.append("")
                lines.append("IMPORTANT: Include this exact Mermaid diagram in Section 3.3 of your report.")
                lines.append("Copy the diagram exactly as shown below:")
                lines.append("")
                lines.append(mermaid_diagram)
                lines.append("")
                lines.append("=" * 60)
                lines.append("")
            except Exception as e:
                logger.warning(f"Failed to generate Mermaid diagram: {e}")

        # Add Variable and Data Flow Analysis (Module D) if available
        if self.graph_store:
            try:
                lines.append("=" * 60)
                lines.append("VARIABLE INFORMATION (Data Flow Analysis)")
                lines.append("=" * 60)
                lines.append("")
                lines.append("IMPORTANT: Include this data flow analysis in Section 3.4 of your report.")
                lines.append("")

                # Query for variables in this function
                var_query = f'''
                MATCH (v:Variable {{scope: "{function_name}"}})
                RETURN v.name as name, v.type as type,
                       v.is_parameter as is_param, v.is_pointer as is_ptr,
                       v.is_static as is_static, v.line as line
                ORDER BY v.is_parameter DESC, v.name
                '''

                variables = self.graph_store.execute_query(var_query)

                if variables:
                    # Group variables
                    params = [v for v in variables if v.get('is_param')]
                    locals_vars = [v for v in variables if not v.get('is_param')]

                    lines.append(f"Function Signature Variables ({len(variables)} total):")
                    lines.append("")

                    if params:
                        lines.append(f"Parameters ({len(params)}):")
                        for p in params:
                            ptr_str = '*' if p.get('is_ptr') else ''
                            static_str = 'static ' if p.get('is_static') else ''
                            type_str = p.get('type') or 'unknown'
                            line_str = f" (line {p.get('line')})" if p.get('line') else ''
                            lines.append(f"  - {static_str}{type_str}{ptr_str} {p['name']}{line_str}")
                        lines.append("")

                    if locals_vars:
                        lines.append(f"Local Variables ({len(locals_vars)}):")
                        for lv in locals_vars[:15]:  # Limit to first 15 locals
                            ptr_str = '*' if lv.get('is_ptr') else ''
                            static_str = 'static ' if lv.get('is_static') else ''
                            type_str = lv.get('type') or 'unknown'
                            line_str = f" (line {lv.get('line')})" if lv.get('line') else ''
                            lines.append(f"  - {static_str}{type_str}{ptr_str} {lv['name']}{line_str}")
                        if len(locals_vars) > 15:
                            lines.append(f"  ... and {len(locals_vars) - 15} more local variables")
                        lines.append("")

                    # Pointer analysis for security
                    pointers = [v for v in variables if v.get('is_ptr')]
                    if pointers:
                        lines.append(f"Pointer Variables Requiring NULL Checks ({len(pointers)}):")
                        for ptr in pointers:
                            type_str = ptr.get('type') or 'unknown'
                            param_str = " [PARAMETER]" if ptr.get('is_param') else " [LOCAL]"
                            lines.append(f"  - {type_str}* {ptr['name']}{param_str}")
                        lines.append("")

                    # Buffer/size variable correlation
                    buffer_vars = [v for v in variables if any(kw in v['name'].lower()
                                   for kw in ['buf', 'buffer', 'data', 'ptr'])]
                    size_vars = [v for v in variables if any(kw in v['name'].lower()
                                 for kw in ['size', 'len', 'length', 'count', 'num'])]

                    if buffer_vars and size_vars:
                        lines.append("Potential Buffer-Size Pairs (for overflow analysis):")
                        for buf in buffer_vars[:5]:  # Limit to 5
                            lines.append(f"  - Buffer: {buf['name']} (type: {buf.get('type', 'unknown')})")
                        if size_vars:
                            lines.append("  - Possible sizes: " + ", ".join(s['name'] for s in size_vars[:5]))
                        lines.append("")
                else:
                    lines.append("No variable data available for this function.")
                    lines.append("")

                lines.append("=" * 60)
                lines.append("")

            except Exception as e:
                logger.warning(f"Failed to fetch variable information: {e}")

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
        """Create prompt for LLM using KV-cache optimized system prompt."""
        # Build system prompt with optional automotive extension
        system_prompt = self._build_system_prompt(context)

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
        """Call Anthropic Claude API with system and user messages (with prompt caching)."""
        try:
            # Determine max_tokens based on model
            # Sonnet 4.5 supports up to 16K output tokens for comprehensive reports
            # Haiku supports 8K output tokens
            if "sonnet" in self.config.model.lower():
                max_tokens = 16384  # 16K for comprehensive reports with automotive section
            elif "haiku" in self.config.model.lower():
                max_tokens = 8192   # 8K for Haiku
            else:
                max_tokens = 4096   # Conservative default

            # Use prompt caching for system message to reduce costs
            # System message format: [{"type": "text", "text": "...", "cache_control": {"type": "ephemeral"}}]
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=max_tokens,
                temperature=self.config.temperature,
                system=[
                    {
                        "type": "text",
                        "text": system_msg,
                        "cache_control": {"type": "ephemeral"}  # Cache the system prompt
                    }
                ],
                messages=[
                    {"role": "user", "content": user_msg}
                ]
            )

            # Log cache performance metrics
            usage = response.usage
            cache_creation = getattr(usage, 'cache_creation_input_tokens', 0)
            cache_read = getattr(usage, 'cache_read_input_tokens', 0)
            input_tokens = usage.input_tokens

            if cache_creation > 0:
                logger.info(f"Cache MISS - Created cache: {cache_creation} tokens")
            if cache_read > 0:
                cache_hit_rate = (cache_read / input_tokens * 100) if input_tokens > 0 else 0
                logger.info(f"Cache HIT - Read {cache_read} tokens ({cache_hit_rate:.1f}% cache hit rate)")

            logger.debug(f"Token usage - Input: {input_tokens}, Output: {usage.output_tokens}, "
                        f"Cache creation: {cache_creation}, Cache read: {cache_read}")

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
