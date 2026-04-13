from typing import Dict, Iterable, List, Tuple


def collect_activity_preferences(responses: Dict[str, float]) -> Dict[str, float]:
    return {k: float(v) for k, v in responses.items()}


def build_activity_vector(responses: Dict[str, float], activity_order: Iterable[str]) -> List[float]:
    return [float(responses.get(name, 0.0)) for name in activity_order]


def compute_activity_similarity(user_vector: List[float], job_activity_matrix: Dict[str, List[float]]) -> List[Tuple[str, float]]:
    results: List[Tuple[str, float]] = []
    for job, vector in job_activity_matrix.items():
        # Simple inverse-L1 similarity for MVP scaffold
        dist = sum(abs(a - b) for a, b in zip(user_vector, vector))
        results.append((job, 1.0 / (1.0 + dist)))
    return sorted(results, key=lambda item: item[1], reverse=True)


def identify_preferred_careers(similarities: List[Tuple[str, float]], threshold: float = 0.5) -> List[str]:
    return [job for job, score in similarities if score >= threshold]
