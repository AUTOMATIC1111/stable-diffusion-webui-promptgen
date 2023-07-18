from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from scripts.promptgen import api_generate, return_available_models

from enum import Enum

class SamplingMode(str, Enum):
    TopK = "Top K"
    TopP = "Top P"


class PromptRequest(BaseModel):
    model_name: str = Field("AUTOMATIC/promptgen-lexart", description="Model name.")
    batch_count: int = Field(1, ge=1, le=100, description="Batch count.")
    batch_size: int = Field(20, ge=1, le=100, description="Batch size.")
    text: str = Field("", description="Input text.")
    min_length: int = Field(20, ge=1, le=400, description="Minimum length.")
    max_length: int = Field(150, ge=1, le=400, description="Maximum length.")
    num_beams: int = Field(1, ge=1, le=8, description="Number of beams.")
    temperature: float = Field(1, ge=0, le=4, description="Temperature.")
    repetition_penalty: float = Field(1, ge=1, le=4, description="Repetition penalty.")
    length_preference: float = Field(1, ge=-10, le=10, description="Length preference.")
    sampling_mode: SamplingMode = Field(SamplingMode.TopK, description="Sampling mode, Either 'Top K' or 'Top P'")
    top_k: int = Field(12, ge=1, le=50, description="Top K.")
    top_p: float = Field(0.15, ge=0, le=1, description="Top P.")

def promptgen_api(_, app: FastAPI):
    @app.get("/promptgen/list_models")
    async def list_models():
        try:
            return {"available_models":  return_available_models()}  
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/promptgen/generate")
    async def generate_prompts(prompt_request: PromptRequest):
        try:
            prompts = api_generate(
                model_name=prompt_request.model_name,
                batch_count=prompt_request.batch_count,
                batch_size=prompt_request.batch_size,
                text=prompt_request.text,
                min_length=prompt_request.min_length,
                max_length=prompt_request.max_length,
                num_beams=prompt_request.num_beams,
                temperature=prompt_request.temperature,
                repetition_penalty=prompt_request.repetition_penalty,
                length_penalty=prompt_request.length_preference,
                sampling_mode=prompt_request.sampling_mode,
                top_k=prompt_request.top_k,
                top_p=prompt_request.top_p,
            )
            return {"prompts": prompts}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        

try:
    import modules.script_callbacks as script_callbacks

    script_callbacks.on_app_started(promptgen_api)
except:
    pass
