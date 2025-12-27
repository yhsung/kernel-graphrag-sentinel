"""
Configuration Management
Handles configuration from YAML files and environment variables.
"""

import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import logging

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    # Look for .env in project root
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path, override=True)  # Override existing env vars
except ImportError:
    pass  # python-dotenv not installed, use existing environment

logger = logging.getLogger(__name__)


@dataclass
class KernelConfig:
    """Kernel source configuration."""
    root: str
    subsystem: str


@dataclass
class Neo4jConfig:
    """Neo4j database configuration."""
    url: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: str = "password123"


@dataclass
class PreprocessingConfig:
    """Code preprocessing configuration."""
    enable_cpp: bool = False
    kernel_config: Optional[str] = None


@dataclass
class AnalysisConfig:
    """Impact analysis configuration."""
    max_call_depth: int = 3
    include_indirect_calls: bool = True
    max_results: int = 100


@dataclass
class LLMConfig:
    """LLM provider configuration."""
    provider: str = "openai"  # openai, gemini, ollama
    model: str = "gpt-4"
    api_key: Optional[str] = None
    temperature: float = 0.7


@dataclass
class Config:
    """Main configuration object."""
    kernel: KernelConfig
    neo4j: Neo4jConfig = field(default_factory=Neo4jConfig)
    preprocessing: PreprocessingConfig = field(default_factory=PreprocessingConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)

    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'Config':
        """
        Load configuration from YAML file.

        Args:
            yaml_path: Path to YAML configuration file

        Returns:
            Config object
        """
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """
        Load configuration from dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            Config object
        """
        # Kernel configuration (required)
        kernel_data = data.get('kernel', {})
        kernel = KernelConfig(
            root=kernel_data.get('root', os.getenv('KERNEL_ROOT', '/workspaces/ubuntu/linux-6.13')),
            subsystem=kernel_data.get('subsystem', 'fs/ext4')
        )

        # Neo4j configuration
        neo4j_data = data.get('neo4j', {})
        neo4j = Neo4jConfig(
            url=neo4j_data.get('url', os.getenv('NEO4J_URL', 'bolt://localhost:7687')),
            user=neo4j_data.get('user', os.getenv('NEO4J_USER', 'neo4j')),
            password=neo4j_data.get('password', os.getenv('NEO4J_PASSWORD', 'password123'))
        )

        # Preprocessing configuration
        preprocessing_data = data.get('preprocessing', {})
        preprocessing = PreprocessingConfig(
            enable_cpp=preprocessing_data.get('enable_cpp', False),
            kernel_config=preprocessing_data.get('kernel_config')
        )

        # Analysis configuration
        analysis_data = data.get('analysis', {})
        analysis = AnalysisConfig(
            max_call_depth=analysis_data.get('max_call_depth', 3),
            include_indirect_calls=analysis_data.get('include_indirect_calls', True),
            max_results=analysis_data.get('max_results', 100)
        )

        # LLM configuration
        llm_data = data.get('llm', {})
        provider = llm_data.get('provider', os.getenv('LLM_PROVIDER', 'openai'))

        # Get API key based on provider
        if provider == 'gemini':
            default_key = os.getenv('GEMINI_API_KEY')
            default_model = llm_data.get('model', os.getenv('GEMINI_MODEL', 'gemini-2.0-flash-exp'))
        elif provider == 'anthropic':
            default_key = os.getenv('ANTHROPIC_API_KEY')
            default_model = llm_data.get('model', os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022'))
        else:  # openai or default
            default_key = os.getenv('OPENAI_API_KEY')
            default_model = llm_data.get('model', os.getenv('OPENAI_MODEL', 'gpt-4'))

        llm = LLMConfig(
            provider=provider,
            model=default_model,
            api_key=llm_data.get('api_key', default_key),
            temperature=llm_data.get('temperature', 0.7)
        )

        return cls(
            kernel=kernel,
            neo4j=neo4j,
            preprocessing=preprocessing,
            analysis=analysis,
            llm=llm
        )

    @classmethod
    def from_defaults(cls, kernel_root: Optional[str] = None,
                       subsystem: Optional[str] = None) -> 'Config':
        """
        Create configuration with default values.

        Args:
            kernel_root: Override kernel root path
            subsystem: Override subsystem path

        Returns:
            Config object with defaults
        """
        kernel = KernelConfig(
            root=kernel_root or os.getenv('KERNEL_ROOT', '/workspaces/ubuntu/linux-6.13'),
            subsystem=subsystem or 'fs/ext4'
        )

        # Load LLM config from environment
        provider = os.getenv('LLM_PROVIDER', 'openai')
        if provider == 'gemini':
            llm_config = LLMConfig(
                provider='gemini',
                model=os.getenv('GEMINI_MODEL', 'gemini-2.0-flash-exp'),
                api_key=os.getenv('GEMINI_API_KEY'),
                temperature=0.7
            )
        elif provider == 'anthropic':
            llm_config = LLMConfig(
                provider='anthropic',
                model=os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022'),
                api_key=os.getenv('ANTHROPIC_API_KEY'),
                temperature=0.7
            )
        elif provider == 'ollama':
            llm_config = LLMConfig(
                provider='ollama',
                model=os.getenv('OLLAMA_MODEL', 'llama3'),
                api_key=None,  # Ollama doesn't need API key
                temperature=0.7
            )
        else:  # openai or unknown
            llm_config = LLMConfig(
                provider='openai',
                model=os.getenv('OPENAI_MODEL', 'gpt-4'),
                api_key=os.getenv('OPENAI_API_KEY'),
                temperature=0.7
            )

        return cls(
            kernel=kernel,
            neo4j=Neo4jConfig(),
            preprocessing=PreprocessingConfig(),
            analysis=AnalysisConfig(),
            llm=llm_config
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Configuration as dictionary
        """
        return {
            'kernel': {
                'root': self.kernel.root,
                'subsystem': self.kernel.subsystem,
            },
            'neo4j': {
                'url': self.neo4j.url,
                'user': self.neo4j.user,
                'password': '***' if self.neo4j.password else None,
            },
            'preprocessing': {
                'enable_cpp': self.preprocessing.enable_cpp,
                'kernel_config': self.preprocessing.kernel_config,
            },
            'analysis': {
                'max_call_depth': self.analysis.max_call_depth,
                'include_indirect_calls': self.analysis.include_indirect_calls,
                'max_results': self.analysis.max_results,
            },
            'llm': {
                'provider': self.llm.provider,
                'model': self.llm.model,
                'api_key': '***' if self.llm.api_key else None,
                'temperature': self.llm.temperature,
            }
        }

    def save_yaml(self, yaml_path: str):
        """
        Save configuration to YAML file.

        Args:
            yaml_path: Path to save YAML file
        """
        with open(yaml_path, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False)

        logger.info(f"Configuration saved to {yaml_path}")


def load_config(config_path: Optional[str] = None,
                 kernel_root: Optional[str] = None,
                 subsystem: Optional[str] = None) -> Config:
    """
    Load configuration from file or create with defaults.

    Args:
        config_path: Path to YAML configuration file (optional)
        kernel_root: Override kernel root path
        subsystem: Override subsystem path

    Returns:
        Config object
    """
    if config_path and Path(config_path).exists():
        logger.info(f"Loading configuration from {config_path}")
        config = Config.from_yaml(config_path)

        # Override with command-line arguments if provided
        if kernel_root:
            config.kernel.root = kernel_root
        if subsystem:
            config.kernel.subsystem = subsystem

        return config
    else:
        logger.info("Using default configuration")
        return Config.from_defaults(kernel_root, subsystem)


if __name__ == "__main__":
    import json

    # Test configuration
    config = Config.from_defaults()
    print("Default Configuration:")
    print(json.dumps(config.to_dict(), indent=2))

    # Save example configuration
    example_path = "examples/analyze_ext4.yaml"
    os.makedirs(os.path.dirname(example_path), exist_ok=True)

    example_config = Config.from_defaults(subsystem='fs/ext4')
    example_config.preprocessing.enable_cpp = False
    example_config.analysis.max_call_depth = 3
    example_config.save_yaml(example_path)

    print(f"\nExample configuration saved to {example_path}")
