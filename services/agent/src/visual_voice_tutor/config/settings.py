from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the Visual Voice Tutor backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="development", alias="APP_ENV")
    app_name: str = Field(default="visual-voice-tutor", alias="APP_NAME")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    cors_allowed_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        alias="CORS_ALLOWED_ORIGINS",
    )
    api_auth_enabled: bool = Field(default=False, alias="API_AUTH_ENABLED")
    api_auth_token: str = Field(default="", alias="API_AUTH_TOKEN")

    ws_path: str = Field(default="/ws", alias="WS_PATH")

    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")

    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_service_role_key: str = Field(default="", alias="SUPABASE_SERVICE_ROLE_KEY")

    azure_openai_endpoint: str = Field(default="", alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str = Field(default="", alias="AZURE_OPENAI_API_KEY")
    azure_openai_deployment: str = Field(default="", alias="AZURE_OPENAI_DEPLOYMENT")

    azure_speech_key: str = Field(default="", alias="AZURE_SPEECH_KEY")
    azure_speech_region: str = Field(default="", alias="AZURE_SPEECH_REGION")
    azure_tts_voice: str = Field(default="ru-RU-DariyaNeural", alias="AZURE_TTS_VOICE")
    azure_tts_output_format: str = Field(
        default="audio-24khz-48kbitrate-mono-mp3",
        alias="AZURE_TTS_OUTPUT_FORMAT",
    )
    azure_tts_chunk_size_bytes: int = Field(default=16384, alias="AZURE_TTS_CHUNK_SIZE_BYTES")
    azure_tts_request_timeout_sec: int = Field(default=25, alias="AZURE_TTS_REQUEST_TIMEOUT_SEC")
    azure_asr_language: str = Field(default="ru-RU", alias="AZURE_ASR_LANGUAGE")
    azure_asr_timeout_sec: int = Field(default=12, alias="AZURE_ASR_TIMEOUT_SEC")

    langfuse_public_key: str = Field(default="", alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(default="", alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field(default="", alias="LANGFUSE_HOST")

    otel_service_name: str = Field(
        default="visual-voice-tutor-backend",
        alias="OTEL_SERVICE_NAME",
    )
    otel_exporter_otlp_endpoint: str = Field(default="", alias="OTEL_EXPORTER_OTLP_ENDPOINT")
    otel_exporter_otlp_headers: str = Field(default="", alias="OTEL_EXPORTER_OTLP_HEADERS")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
