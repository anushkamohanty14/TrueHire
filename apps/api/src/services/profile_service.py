from typing import Any, Dict, List, Optional

from core.src.core.pipelines.phase1_onet_data import build_job_ability_matrix, clean_onet_data, load_onet_data
from core.src.core.pipelines.phase2_user_input import create_user_profile, suggest_jobs_from_interest_tags
from core.src.core.storage.user_store import JsonUserStore


class ProfileService:
    def __init__(self, store: Optional[JsonUserStore] = None) -> None:
        self.store = store or JsonUserStore()

    def create_profile(self, user_id: str, manual_skills: List[str], interest_tags: List[str]) -> Dict[str, Any]:
        profile = create_user_profile(user_id=user_id, manual_skills=manual_skills, interest_tags=interest_tags)

        # Phase 1 -> Phase 2 integration: enrich profile with O*NET job suggestions.
        onet_rows = clean_onet_data(load_onet_data())
        job_titles = list(build_job_ability_matrix(onet_rows).keys())
        profile["phase1_job_suggestions"] = suggest_jobs_from_interest_tags(profile["interest_tags"], job_titles)

        return self.store.upsert_profile(profile)

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.store.get_profile(user_id)
