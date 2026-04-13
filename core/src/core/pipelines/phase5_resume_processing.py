"""Phase 5 — Resume text extraction and rule-based skill identification.

Pipeline
--------
1. extract_text(file_path)    →  raw string from PDF / DOCX / TXT
2. chunk_sections(text)       →  dict of section → text (Education, Experience, Skills, …)
3. extract_skills_onet(text)  →  skills matched against O*NET in-demand tech taxonomy
4. extract_skills_rules(text) →  skills matched against built-in taxonomy
5. extract_education(text)    →  degree, institution, year
6. extract_certifications(text) → list of cert strings
7. extract_experience_years(text) → estimated years of experience
8. process_resume(file_path)  →  ResumeExtractionResult (end-to-end)

All extraction is purely rule-based — no LLM or API key required.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class ResumeExtractionResult:
    """Output of the resume extraction pipeline."""
    skills: List[str]
    method: str
    raw_text_length: int
    education: List[str] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    experience_years: Optional[float] = None
    error: Optional[str] = None


# backward-compat alias
SkillExtractionResult = ResumeExtractionResult


# ── O*NET taxonomy loader ─────────────────────────────────────────────────────

_ONET_CSV = Path(__file__).resolve().parents[4] / "Archive" / "Technology Skills.csv"


@lru_cache(maxsize=1)
def _load_onet_skills() -> List[str]:
    """Load O*NET in-demand technology skills from the CSV (cached)."""
    if not _ONET_CSV.exists():
        return []
    skills: set[str] = set()
    with open(_ONET_CSV, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if row.get("In Demand") == "Y" or row.get("Hot Technology") == "Y":
                skills.add(row["Example"].strip())
    return list(skills)


# ── Built-in taxonomy (broad coverage) ───────────────────────────────────────

_SKILL_TAXONOMY: List[str] = [
    # Programming languages
    "Python", "Java", "JavaScript", "TypeScript", "C", "C++", "C#", "Go",
    "Rust", "Ruby", "PHP", "Swift", "Kotlin", "R", "MATLAB", "Scala", "Perl",
    "Bash", "Shell", "SQL", "HTML", "CSS", "SASS", "LESS", "Dart", "Lua",
    "Haskell", "Erlang", "Elixir", "Clojure", "F#",

    # Web frameworks & libraries
    "React", "Angular", "Vue", "Vue.js", "Next.js", "Nuxt.js", "Svelte",
    "Node.js", "Express", "Django", "Flask", "FastAPI", "Spring", "Spring Boot",
    "Laravel", "Rails", "Ruby on Rails", "ASP.NET", ".NET", "jQuery",
    "Tailwind CSS", "Bootstrap", "GraphQL", "REST", "gRPC", "WebSocket",

    # Data science & ML
    "TensorFlow", "PyTorch", "Keras", "scikit-learn", "Pandas", "NumPy",
    "SciPy", "Matplotlib", "Seaborn", "Plotly", "Hugging Face", "spaCy",
    "NLTK", "OpenCV", "LangChain", "LlamaIndex", "BERT", "GPT",
    "Machine Learning", "Deep Learning", "NLP", "Natural Language Processing",
    "Computer Vision", "Data Science", "Data Analysis", "Data Engineering",
    "Feature Engineering", "A/B Testing", "Statistics", "ETL",
    "Data Warehousing", "Neural Networks", "Transformers", "RAG",
    "Reinforcement Learning", "Time Series", "Forecasting",

    # Databases
    "MySQL", "PostgreSQL", "MongoDB", "SQLite", "Oracle", "SQL Server",
    "Redis", "Elasticsearch", "Cassandra", "DynamoDB", "Firebase", "Firestore",
    "Neo4j", "InfluxDB", "Snowflake", "BigQuery", "Redshift",
    "Pinecone", "Weaviate", "ChromaDB",

    # Cloud & infrastructure
    "AWS", "Azure", "GCP", "Google Cloud", "Docker", "Kubernetes",
    "Terraform", "Ansible", "Puppet", "Chef", "Helm", "Istio",
    "CI/CD", "Jenkins", "GitHub Actions", "CircleCI", "Travis CI", "GitLab CI",
    "Nginx", "Apache", "Linux", "Unix",

    # Tools & platforms
    "Git", "GitHub", "GitLab", "Bitbucket", "Jira", "Confluence",
    "Tableau", "Power BI", "Looker", "dbt", "Airflow", "Prefect", "Dagster",
    "Spark", "Hadoop", "Kafka", "Flink", "Celery", "RabbitMQ",
    "VS Code", "IntelliJ", "PyCharm", "Eclipse", "Xcode",
    "npm", "Yarn", "Webpack", "Vite", "Babel",
    "Postman", "Swagger", "OpenAPI",

    # Security
    "OAuth", "JWT", "SSL", "TLS", "Cybersecurity", "OWASP",
    "Penetration Testing", "Encryption",

    # Mobile
    "iOS", "Android", "React Native", "Flutter", "Xamarin",

    # Methodologies
    "Agile", "Scrum", "Kanban", "DevOps", "TDD", "BDD",
    "Microservices", "Domain-Driven Design", "SOLID",
    "Design Patterns", "System Design",

    # BI / Office
    "Excel", "Google Sheets", "PowerPoint", "Word",
]


def _build_patterns(skills: List[str]):
    """Build compiled regex patterns for a list of skills, longest first."""
    patterns = []
    for skill in skills:
        try:
            pat = re.compile(r"\b" + re.escape(skill) + r"\b", re.IGNORECASE)
            patterns.append((skill, pat))
        except re.error:
            pass
    return sorted(patterns, key=lambda x: -len(x[0]))


_BUILTIN_PATTERNS = _build_patterns(_SKILL_TAXONOMY)


# ── Text extraction ───────────────────────────────────────────────────────────

def extract_text(file_path: str) -> str:
    """Return the plain-text content of a resume file.

    Supported formats: ``.pdf``, ``.docx`` / ``.doc``, and any plain-text
    extension (``.txt``, ``.md``, etc.).
    """
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(path)
    if suffix in (".docx", ".doc"):
        return _extract_docx(path)
    return path.read_text(encoding="utf-8", errors="replace")


def _extract_pdf(path: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def _extract_docx(path: Path) -> str:
    import docx  # python-docx
    doc = docx.Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs)


# ── Section chunking ──────────────────────────────────────────────────────────

# Regexes for common resume section headers
_SECTION_HEADERS = {
    "education": re.compile(
        r"^(education|academic|qualifications?|degrees?|schooling)\b",
        re.IGNORECASE | re.MULTILINE,
    ),
    "experience": re.compile(
        r"^(experience|employment|work history|professional background|career)\b",
        re.IGNORECASE | re.MULTILINE,
    ),
    "skills": re.compile(
        r"^(skills?|technical skills?|core competenc|technologies|tools)\b",
        re.IGNORECASE | re.MULTILINE,
    ),
    "certifications": re.compile(
        r"^(certifications?|certificates?|licen[sc]es?|accreditations?|credentials?)\b",
        re.IGNORECASE | re.MULTILINE,
    ),
    "summary": re.compile(
        r"^(summary|objective|profile|about me|overview)\b",
        re.IGNORECASE | re.MULTILINE,
    ),
}

# Any section header (to detect end of section)
_ANY_HEADER = re.compile(
    r"^(education|academic|qualifications?|experience|employment|work history|"
    r"professional background|career|skills?|technical skills?|core competenc|"
    r"technologies|tools|certifications?|certificates?|licen[sc]es?|accreditations?|"
    r"credentials?|summary|objective|profile|about me|overview|projects?|publications?|"
    r"awards?|honors?|languages?|interests?|references?|volunteer)\b",
    re.IGNORECASE | re.MULTILINE,
)


def chunk_sections(text: str) -> Dict[str, str]:
    """Split resume text into named sections based on header detection."""
    lines = text.splitlines()
    sections: Dict[str, str] = {"_full": text}
    current_section = "_preamble"
    current_lines: List[str] = []
    section_content: Dict[str, List[str]] = {current_section: []}

    for line in lines:
        stripped = line.strip()
        matched_section = None
        for name, pattern in _SECTION_HEADERS.items():
            if pattern.match(stripped):
                matched_section = name
                break

        if matched_section:
            section_content[current_section] = current_lines
            current_section = matched_section
            current_lines = []
        else:
            current_lines.append(line)

    section_content[current_section] = current_lines
    for name, lines_list in section_content.items():
        sections[name] = "\n".join(lines_list)

    return sections


# ── Skill extraction ──────────────────────────────────────────────────────────

def extract_skills_rules(text: str) -> List[str]:
    """Match skills against the built-in taxonomy."""
    found: List[str] = []
    for skill, pattern in _BUILTIN_PATTERNS:
        if pattern.search(text):
            found.append(skill)
    return found


def extract_skills_onet(text: str) -> List[str]:
    """Match skills against O*NET in-demand technology list."""
    onet_skills = _load_onet_skills()
    if not onet_skills:
        return []
    patterns = _build_patterns(onet_skills)
    found: List[str] = []
    for skill, pattern in patterns:
        if pattern.search(text):
            found.append(skill)
    return found


# ── Education extraction ──────────────────────────────────────────────────────

_DEGREE_PATTERNS = [
    re.compile(r"\b(Ph\.?D\.?|Doctor(?:ate)?)\b", re.IGNORECASE),
    re.compile(r"\b(M\.?S\.?|M\.?Sc\.?|Master(?:'s)?(?:\s+of\s+\w+)?)\b", re.IGNORECASE),
    re.compile(r"\b(M\.?B\.?A\.?)\b", re.IGNORECASE),
    re.compile(r"\b(B\.?S\.?|B\.?Sc\.?|B\.?E\.?|B\.?Tech\.?|B\.?A\.?|Bachelor(?:'s)?(?:\s+of\s+\w+)?)\b", re.IGNORECASE),
    re.compile(r"\b(Associate(?:'s)?\s+(?:of|in)\s+\w+|A\.A\.?S?\.?|A\.S\.?)\b", re.IGNORECASE),
    re.compile(r"\b(High School Diploma|GED|Secondary)\b", re.IGNORECASE),
]

_YEAR_PATTERN = re.compile(r"\b(19[89]\d|20[0-3]\d)\b")


def extract_education(text: str) -> List[str]:
    """Extract degree mentions from text."""
    found = []
    for pattern in _DEGREE_PATTERNS:
        for match in pattern.finditer(text):
            # Grab surrounding context
            start = max(0, match.start() - 20)
            end = min(len(text), match.end() + 80)
            snippet = text[start:end].replace("\n", " ").strip()
            found.append(snippet)
    return _deduplicate_strings(found)


# ── Certification extraction ──────────────────────────────────────────────────

_CERT_PATTERNS = [
    re.compile(r"\b(AWS\s+Certified\s+[^\n,;]{3,50}?)(?=\s*[\n,;]|$)", re.IGNORECASE),
    re.compile(r"\b(Google\s+(?:Cloud\s+)?(?:Professional|Associate|Certified)\s+[^\n,;]{3,50}?)(?=\s*[\n,;]|$)", re.IGNORECASE),
    re.compile(r"\b(Microsoft\s+(?:Certified|Azure)\s+[^\n,;]{3,50}?)(?=\s*[\n,;]|$)", re.IGNORECASE),
    re.compile(r"\b(Certified\s+\w[\w\s]{3,40})(?=\s*[\n,;(]|$)", re.IGNORECASE),
    re.compile(r"\b(PMP|CISSP|CISA|CISM|CEH|CompTIA\s+\w+|CCNA|CCNP|CPA|CFA|CMA|SHRM-CP|PHR|SPHR)\b", re.IGNORECASE),
    re.compile(r"\b(Scrum\s+Master|CSPO|CSM|SAFe\s+\w+|PMI-ACP)\b", re.IGNORECASE),
    re.compile(r"\b(ITIL\s*\w*|Six\s+Sigma|Lean\s+Six\s+Sigma|Prince2)\b", re.IGNORECASE),
    re.compile(r"\b(TensorFlow\s+(?:Developer\s+)?Certificate)\b", re.IGNORECASE),
]


def extract_certifications(text: str) -> List[str]:
    """Extract certification mentions from text."""
    found = []
    for pattern in _CERT_PATTERNS:
        for match in pattern.finditer(text):
            cert = match.group(0).strip()
            if len(cert) > 3:
                found.append(cert)
    return _deduplicate_strings(found)


# ── Experience years estimation ───────────────────────────────────────────────

_YEAR_RANGE_PATTERN = re.compile(
    r"\b((?:19|20)\d{2})\s*[-–—to]+\s*((?:19|20)\d{2}|present|current|now)\b",
    re.IGNORECASE,
)
_YEARS_EXP_PATTERN = re.compile(
    r"\b(\d+)\+?\s*years?\s+(?:of\s+)?(?:professional\s+)?experience\b",
    re.IGNORECASE,
)


def extract_experience_years(text: str) -> Optional[float]:
    """Estimate total years of experience from date ranges or explicit mentions."""
    import datetime
    current_year = datetime.date.today().year

    # Explicit mention takes priority
    for m in _YEARS_EXP_PATTERN.finditer(text):
        return float(m.group(1))

    # Sum non-overlapping year ranges
    total = 0.0
    for m in _YEAR_RANGE_PATTERN.finditer(text):
        start_yr = int(m.group(1))
        end_str = m.group(2).lower()
        end_yr = current_year if end_str in ("present", "current", "now") else int(end_str)
        duration = max(0, end_yr - start_yr)
        total += duration

    return round(total, 1) if total > 0 else None


# ── Combined pipeline ─────────────────────────────────────────────────────────

def extract_skills(text: str) -> ResumeExtractionResult:
    """Extract skills, education, certs and experience from resume text."""
    sections = chunk_sections(text)

    # Skills: search skills section first, fall back to full text
    skills_text = sections.get("skills", "") or text
    rule_skills = extract_skills_rules(text)        # full text for broader coverage
    onet_skills = extract_skills_onet(skills_text)  # O*NET hot/in-demand tech

    all_skills = _normalise(rule_skills + onet_skills)

    # Education from education section + full text fallback
    edu_text = sections.get("education", "") or text
    education = extract_education(edu_text)

    # Certs from certifications section + full text
    cert_text = sections.get("certifications", "") + "\n" + text
    certifications = extract_certifications(cert_text)

    # Experience years from experience section
    exp_text = sections.get("experience", "") or text
    experience_years = extract_experience_years(exp_text)

    return ResumeExtractionResult(
        skills=all_skills,
        method="rules",
        raw_text_length=len(text),
        education=education,
        certifications=certifications,
        experience_years=experience_years,
    )


def process_resume(file_path: str) -> ResumeExtractionResult:
    """End-to-end: extract text from *file_path* then extract all fields."""
    try:
        text = extract_text(file_path)
    except Exception as exc:
        return ResumeExtractionResult(
            skills=[], method="error", raw_text_length=0,
            error=f"Text extraction failed: {exc}",
        )

    if not text.strip():
        return ResumeExtractionResult(
            skills=[], method="error", raw_text_length=0,
            error="No readable text found in the file.",
        )

    return extract_skills(text)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalise(skills: List[str]) -> List[str]:
    """Deduplicate (case-insensitive), prefer longer canonical names, sort."""
    seen: dict[str, str] = {}
    for s in skills:
        key = s.strip().lower()
        if key and key not in seen:
            seen[key] = s.strip()

    # Remove skills that are substrings of a longer skill in the set
    # e.g. "Kafka" when "Apache Kafka" is present
    values = list(seen.values())
    filtered = []
    for skill in values:
        skill_lower = skill.lower()
        is_substring = any(
            skill_lower != other.lower() and skill_lower in other.lower()
            for other in values
        )
        if not is_substring:
            filtered.append(skill)

    return sorted(filtered, key=str.lower)


def _deduplicate_strings(items: List[str]) -> List[str]:
    """Remove duplicates and substrings, preserving the longest match."""
    cleaned = [item.strip() for item in items if item.strip()]
    # Sort by length descending so longer strings come first
    cleaned.sort(key=len, reverse=True)
    result = []
    for item in cleaned:
        # Skip if this string is a substring of one already kept
        if not any(item.lower() in kept.lower() for kept in result):
            result.append(item)
    return result
