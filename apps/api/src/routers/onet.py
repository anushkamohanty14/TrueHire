from fastapi import APIRouter

from core.src.core.pipelines.phase1_onet_data import build_job_ability_matrix, clean_onet_data, load_onet_data

router = APIRouter(prefix="/onet", tags=["onet"])


@router.get("/jobs")
def list_jobs(limit: int = 20) -> dict[str, list[str]]:
    rows = clean_onet_data(load_onet_data())
    titles = list(build_job_ability_matrix(rows).keys())
    return {"jobs": titles[:limit]}
