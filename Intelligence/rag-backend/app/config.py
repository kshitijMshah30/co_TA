from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str
    supabase_service_key: str

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384
    embedding_device: str = "cpu"

    default_lab_id: str = "lab_5"
    retrieval_top_k: int = 5
    min_similarity: float = 0.4

    llm_backend: str = "mock"
    llm_api_base: str = "http://localhost:8000/v1"
    llm_api_key: str = ""
    llm_model: str = "placeholder-model"
    llm_timeout_seconds: int = 30

    api_request_timeout_seconds: int = 30


settings = Settings()
