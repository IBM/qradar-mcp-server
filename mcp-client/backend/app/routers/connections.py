"""Connections router - manages QRadar and LLM connections."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
import uuid

from app.models.schemas import (
    QRadarConnectionCreate, 
    QRadarConnection, 
    QRadarConnectionTest,
    LLMModelCreate,
    LLMModel
)
from app import config_store

router = APIRouter()


# ============== QRadar Connections ==============

@router.get("/qradar", response_model=list[QRadarConnection])
async def list_qradar_connections():
    """List all QRadar connections."""
    return config_store.get_qradar_connections()


@router.post("/qradar", response_model=QRadarConnection)
async def create_qradar_connection(conn: QRadarConnectionCreate):
    """Create a new QRadar connection."""
    conn_data = conn.model_dump()
    conn_data["id"] = str(uuid.uuid4())
    return config_store.save_qradar_connection(conn_data)


@router.get("/qradar/{conn_id}", response_model=QRadarConnection)
async def get_qradar_connection(conn_id: str):
    """Get a specific QRadar connection."""
    conn = config_store.get_qradar_connection(conn_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    return conn


@router.put("/qradar/{conn_id}", response_model=QRadarConnection)
async def update_qradar_connection(conn_id: str, conn: QRadarConnectionCreate):
    """Update a QRadar connection."""
    existing = config_store.get_qradar_connection(conn_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    conn_data = conn.model_dump()
    conn_data["id"] = conn_id
    return config_store.save_qradar_connection(conn_data)


@router.delete("/qradar/{conn_id}")
async def delete_qradar_connection(conn_id: str):
    """Delete a QRadar connection."""
    config_store.delete_qradar_connection(conn_id)
    return {"message": "Connection deleted"}


class QRadarTestRequest(BaseModel):
    url: str
    token: str
    verify: bool = False


@router.post("/qradar/test", response_model=QRadarConnectionTest)
async def test_qradar_direct(req: QRadarTestRequest):
    """Test QRadar connection directly with credentials."""
    try:
        url = req.url.rstrip("/")
        async with httpx.AsyncClient(verify=req.verify, timeout=10.0) as client:
            response = await client.get(
                f"{url}/api/system/about",
                headers={"SEC": req.token, "Accept": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                return QRadarConnectionTest(
                    success=True,
                    message="Connection successful",
                    version=data.get("external_version", "Unknown")
                )
            elif response.status_code == 401:
                return QRadarConnectionTest(
                    success=False,
                    message="Unauthorized - Invalid API token"
                )
            else:
                return QRadarConnectionTest(
                    success=False,
                    message=f"HTTP {response.status_code}"
                )
    except httpx.ConnectError as e:
        error_str = str(e).lower()
        if "ssl" in error_str or "certificate" in error_str:
            return QRadarConnectionTest(
                success=False,
                message="SSL Certificate Error - Turn OFF 'SSL Certificate Verification' for self-signed certificates"
            )
        return QRadarConnectionTest(
            success=False,
            message=f"Connection failed - Cannot reach server at {req.url}"
        )
    except Exception as e:
        error_str = str(e).lower()
        if "ssl" in error_str or "certificate" in error_str or "verify" in error_str:
            return QRadarConnectionTest(
                success=False,
                message="SSL Certificate Error - Turn OFF 'SSL Certificate Verification' for self-signed certificates"
            )
        return QRadarConnectionTest(
            success=False,
            message=f"Error: {str(e)}"
        )


@router.post("/qradar/{conn_id}/test", response_model=QRadarConnectionTest)
async def test_qradar_connection(conn_id: str):
    """Test a saved QRadar connection."""
    conn = config_store.get_qradar_connection(conn_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    # Reuse the direct test logic
    req = QRadarTestRequest(
        url=conn.get("url", ""),
        token=conn.get("token", ""),
        verify=conn.get("verify", False)
    )
    return await test_qradar_direct(req)


# ============== LLM Models ==============

@router.get("/models", response_model=list[LLMModel])
async def list_models():
    """List all LLM models."""
    return config_store.get_llm_models()


@router.post("/models", response_model=LLMModel)
async def create_model(model: LLMModelCreate):
    """Create a new LLM model configuration."""
    model_data = model.model_dump()
    model_data["id"] = str(uuid.uuid4())
    return config_store.save_llm_model(model_data)


@router.get("/models/{model_id}", response_model=LLMModel)
async def get_model(model_id: str):
    """Get a specific LLM model."""
    models = config_store.get_llm_models()
    model = next((m for m in models if m["id"] == model_id), None)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.put("/models/{model_id}", response_model=LLMModel)
async def update_model(model_id: str, model: LLMModelCreate):
    """Update an LLM model configuration."""
    model_data = model.model_dump()
    model_data["id"] = model_id
    return config_store.save_llm_model(model_data)


@router.delete("/models/{model_id}")
async def delete_model(model_id: str):
    """Delete an LLM model configuration."""
    config_store.delete_llm_model(model_id)
    return {"message": "Model deleted"}
