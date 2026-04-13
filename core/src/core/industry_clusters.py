"""Industry classification for O*NET job titles.

Classifies job titles into industry buckets using priority-ordered substring
matching (first match wins). A fallback map handles remaining edge cases.

Public API
----------
classify_title(title: str) -> str
    Returns an industry_id string, e.g. "technology".

classify_titles(titles) -> dict[str, str]
    Returns {title -> industry_id} for a collection of titles.

INDUSTRY_META : dict[str, dict]
    Static metadata — {industry_id: {name, icon, description}}.

ALL_INDUSTRIES : list[str]
    Ordered list of all industry_ids.
"""
from __future__ import annotations

from typing import Dict, Iterable

# ── Industry metadata ─────────────────────────────────────────────────────────

INDUSTRY_META: Dict[str, Dict] = {
    "technology":    {"name": "Technology",             "icon": "computer"},
    "healthcare":    {"name": "Healthcare & Medicine",  "icon": "health_and_safety"},
    "finance":       {"name": "Finance & Accounting",   "icon": "account_balance"},
    "engineering":   {"name": "Engineering",            "icon": "engineering"},
    "education":     {"name": "Education",              "icon": "school"},
    "science":       {"name": "Science & Research",     "icon": "science"},
    "legal":         {"name": "Legal",                  "icon": "gavel"},
    "arts":          {"name": "Arts & Media",           "icon": "palette"},
    "management":    {"name": "Management & Business",  "icon": "business_center"},
    "social":        {"name": "Social Services",        "icon": "people"},
    "trades":        {"name": "Trades & Manufacturing", "icon": "construction"},
    "government":    {"name": "Government & Safety",    "icon": "shield"},
    "transport":     {"name": "Transportation",         "icon": "local_shipping"},
    "hospitality":   {"name": "Hospitality & Food",     "icon": "restaurant"},
    "agriculture":   {"name": "Agriculture & Environment", "icon": "eco"},
}

ALL_INDUSTRIES = list(INDUSTRY_META.keys())

# ── Priority-ordered substring rules ─────────────────────────────────────────
# Rules are checked in order; first match wins (case-insensitive substring).
# Put more specific rules before broad ones.

_RULES = [
    # ── Technology ──────────────────────────────────────────────────────────
    ("technology", [
        "software", "computer ", "computer,",
        "data scientist", "data analyst", "data warehousing",
        "database", "network architect", "network support", "network administrator",
        "cybersecurity", "information security",
        "web developer", "web designer", "web administrator",
        "systems analyst", "systems administrator", "systems engineer",
        "it specialist", "it manager", "it project",
        "cloud computing", "devops",
        "programmer", "user experience", "user interface",
        "machine learning", "artificial intelligence",
        "information technology", "geographic information systems",
        "business intelligence analyst", "business intelligence",
        "robotics technician", "photonics", "search marketing",
        "video game designer",
    ]),

    # ── Healthcare — before Education so "health educators" goes here ────────
    ("healthcare", [
        # Doctors & specialists
        "physician", "surgeon", "doctor ", "psychiatr", "pediatr", "oncol",
        "anesthesi", "cardiolog", "cardiovascular", "dermatolog",
        "endocrinolog", "gastroenterol", "gynecol", "hematolog",
        "neurolog", "ophthalmol", "orthoped", "urolog", "immunolog",
        "allergist", "hospitalist", "podiatrist", "orthodontist",
        "orthoptist", "coroner",
        # Nursing & allied
        "nurse", "nursing", "paramedic", "emergency medical",
        "midwife", "midwives", "phlebotomist",
        # Therapy
        "occupational therapist", "occupational therapy",
        "physical therapist", "respiratory therapist",
        "recreational therapist", "radiation therapist",
        "radiolog", "patholog", "audiolog", "chiropract",
        "acupunctur", "massage therapist",
        # Technicians/technologists (medical)
        "medical ", "medical,", "dental", "dentist",
        "surgical technolog", "surgical assistant",
        "cytogenetic", "cytotechnolog", "histotechnolog", "histology technician",
        "neurodiagnostic", "nuclear medicine", "cardiovascular technolog",
        "magnetic resonance", "endoscopy technician",
        "ophthalmic", "optician", "optom",
        "hearing aid specialist", "orthotist", "prosthetist",
        "pharmacy", "pharmacist",
        # Allied health
        "therapist",  # catches art therapist, music therapist, etc.
        "health educator", "health informatics", "health information",
        "health services", "home health", "hospice",
        "dietitian", "nutritionist", "dietetic",
        "exercise physiologist", "athletic trainer",
        "patient representative", "orderly", "orderlies",
        "veterinar", "mental health", "substance abuse",
        "rehabilitation", "clinical", "health diagnost",
        "adapted physical education",
    ]),

    # ── Finance ─────────────────────────────────────────────────────────────
    ("finance", [
        "accountant", "accounting", "auditor", "auditing",
        "actuar",  # actuary / actuaries
        "financial analyst", "financial quantitative",
        "financial manager", "financial examiner", "financial advisor",
        "loan officer", "loan examiner",
        "credit analyst", "credit counselor",
        "insurance agent", "insurance underwriter", "insurance examiner",
        "underwriter",
        "brokerage", "broker,",
        "securities,", "investment banker", "investment advisor",
        "investment manager", "portfolio manager",
        "economist", "tax examiner", "tax preparer",
        "bookkeeping", "bookkeeper",
        "budget analyst", "claims adjuster", "cost estimator",
        "treasurer", "payroll", "billing clerk",
        "teller", "bank ", "banking",
        "fraud examiner", "fraud investigator",
        "financial quantitative", "new accounts clerk",
        "apprais",  # appraisers
        "bill and account collector", "billing and posting",
        "brokerage clerk",
    ]),

    # ── Engineering (before management so engineers don't fall through) ──────
    ("engineering", [
        " engineer", "engineers,",
        "engineering technician", "engineering technolog",
        "architect,", "architects,", "architect.",
        "naval architect", "landscape architect",
        "drafter", "surveyor", "surveying technician",
        "avionics", "aerospace",
        "chemical plant", "chemical process",
        "power plant operator", "nuclear reactor",
        "petroleum engineer", "mining engineer",
        "geothermal production manager", "hydroelectric production",
        "wind energy development", "wind energy operations",
        "solar energy installation manager",
    ]),

    # ── Legal ────────────────────────────────────────────────────────────────
    ("legal", [
        "lawyer", "attorney", "judge,", "judges,", "magistrate",
        "paralegal", "legal secretary", "legal secretar",
        "court,", "judicial", "arbitrator", "mediator", "conciliator",
        "bailiff", "title examiner", "administrative law",
        "compliance officer", "compliance manager", "compliance specialist",
        "regulatory affairs",
    ]),

    # ── Science & Research ───────────────────────────────────────────────────
    ("science", [
        "scientist", "biologist", "chemist", "physicist", "astronomer",
        "geologist", "geographer", "ecologist", "microbiolog",
        "biochemist", "biophysicist", "hydrologist", "zoologist",
        "botanist", "soil scientist", "materials scientist",
        "atmospheric", "forensic science",
        "political scientist", "sociologist", "anthropolog", "archeolog",
        "epidemiolog", "statistician", "mathematician",
        "operations research analyst",
        "geneticist", "bioinformatics",
        "geological technician", "geothermal technician",
        "chemical technician", "nuclear technician", "nuclear monitoring",
        "biological technician",
        "remote sensing", "cartograph", "photogrammetrist",
        "survey researcher", "urban and regional planner",
        "water resource specialist", "environmental scientist",
        "environmental specialist", "environmental restoration",
        "environmental science and protection",
        "environmental engineer",
        "geographic information systems technolog",
        "climate change", "sustainability specialist",
        "park naturalist", "range manager",
        "precision agriculture technician",
        "natural sciences manager",
        "non-destructive testing",
    ]),

    # ── Education ────────────────────────────────────────────────────────────
    ("education", [
        " teacher,", "teachers,", ", teacher", "postsecondary",
        "instructor", "professor", "librarian", "archivist",
        "curator,", "principal,", "principal.",
        "education administrator", "special education",
        "tutors", "teaching assistant", "library technician",
        "library assistant", "instructional coordinator",
        "adult basic education", "farm and home management educator",
        "directors, religious activities and education",
    ]),

    # ── Arts & Media ─────────────────────────────────────────────────────────
    ("arts", [
        "actor", "actress", "artist,", "artists,",
        "author,", "writer,", "editor,",
        "musician", "singer", "composer", "choreograph", "dancer",
        "photographer", "videographer", "journalist", "reporter",
        "broadcast", "film ",
        "animator", "graphic designer", "multimedia",
        "art director", "fashion designer", "floral designer",
        "interior designer", "set and exhibit designer",
        "makeup artist", "model,", "models,",
        "entertainer", "producer,", "producers and",
        "directors,",  # "Producers and Directors"
        "camera operator", "motion picture",
        "desktop publisher", "prepress technician",
        "print binding", "proofreader",
        "costume attendant", "talent director",
        "media programming", "media technical",
        "merchandise displayer",
        "tailors, dressmakers", "custom sewers",
        "museum technician",
        "ushers, lobby",
        "coaches and scouts",
        "athletes and sports", "umpires, referees",
    ]),

    # ── Trades & Manufacturing ───────────────────────────────────────────────
    ("trades", [
        "electrician", "plumber", "pipefitter", "steamfitter",
        "carpenter", "welder", "welding",
        "machinist", "brickmason", "stonemason",
        "ironworker", "boilermaker", "millwright",
        "sheet metal", "hvac", "heating, air",
        "assembler", "fabricator",
        "mechanic",  # no trailing comma — catches aircraft/bus/auto mechanics
        "repairer", "repairers",  # catches body repairers
        "maintenance mechanic", "maintenance worker",
        "machine setters, operators", "machine tool setters",
        "machine operators and tenders", "machine operator",
        "extruding", "forging machine", "rolling machine",
        "milling and planing machine", "plating machine",
        "sawing machine", "lathe and turning", "drilling and boring",
        "multiple machine tool", "grinding, lapping",
        "cutting, punching", "cutting and slicing",
        "mixing and blending machine", "paper goods machine",
        "molding, coremaking", "molders, shapers",
        "foundry mold", "heat treating equipment",
        "separating, filtering",
        "woodworking machine", "patternmakers, metal",
        "patternmakers, wood",
        "cabinetmaker", "woodworker", "upholsterer",
        "glazier", "roofer", "plasterer", "drywall",
        "insulation worker", "painter, construction",
        "paving, surfacing", "reinforcing iron",
        "structural iron and steel",
        "gem and diamond", "glass blower",
        "jeweler", "precious stone",
        "floor layer", "floor sander", "floor finisher",
        "furniture finisher",
        "fence erector",
        "roof bolter", "rock splitter",
        "segmental paver", "tapers,", "terrazzo",
        "tire builder",
        "tool grinder",
        "semiconductor",
        "packaging machine",
        "coating, painting", "painting, coating",
        "coil winder",
        "construction manager", "construction worker",
        "cement mason", "concrete finisher",
        "installer",
        "inspectors, testers, sorters",
        "pest control",
        "bicycle repair",
        "automotive body", "automotive service", "automotive technician",
        "recreational vehicle service",
        "aircraft mechanic", "aircraft service technician",
        "bus and truck mechanic",
        "etchers and engravers",
        "laser technician",
        "layout workers, metal",
        "pourers and casters",
        "sewing machine operator",
        "tool and die",
        "hazardous materials removal",
        "adhesive bonding machine",
        "audio and video technician",
    ]),

    # ── Government & Public Safety ────────────────────────────────────────────
    ("government", [
        "police", "firefighter", "fire inspector", "fire investigator",
        "detective", "correctional", "probation", "parole",
        "border patrol", "customs,", "immigration",
        "military", "intelligence analyst",
        "security guard", "security officer", "lifeguard",
        "crossing guard", "parking enforcement",
        "fish and game warden", "animal control",
        "public safety telecommunicator",
        "transportation security screener",
        "emergency management director",
        "explosives workers", "equal opportunity",
        "gambling surveillance",
        "first-line supervisors of firefighting",
        "first-line supervisors of security",
        "loss prevention",
        "environmental compliance",
    ]),

    # ── Transportation ────────────────────────────────────────────────────────
    ("transport", [
        "driver", "airline pilot", "commercial pilot",
        "captains, mates",
        "sailor", "marine ",
        "ship ",
        "locomotive",
        "air traffic", "flight attendant",
        "cargo and freight agent",
        "postal",
        "dispatcher",
        "transit ",
        "taxi ",
        "subway and streetcar",
        "motorboat operator",
        "railroad conductor",
        "logistician", "logistics analyst",
        "freight forwarder",
        "transportation planner",
        "transportation vehicle",
        "transportation, storage, and distribution",
        "passenger attendant",
        "shipping clerk",
        "postmaster",
        "first-line supervisors of material-moving",
        "bridge and lock tender",
        "airfield operations",
        "aircraft cargo handling",
        "crane and tower operator",
        "hoist and winch",
        "dredge operator",
        "rotary drill operator",
        "derrick operator",
        "loading and moving machine",
        "excavating and loading",
    ]),

    # ── Hospitality & Food ────────────────────────────────────────────────────
    ("hospitality", [
        "chef", "cook,", "cooks,",
        "baker", "baking",
        "bartender", "barista",
        "waiter", "waitress",
        "food ", "restaurant",
        "hotel,", "lodging", "housekeeping", "concierge",
        "event planner", "meeting planner",
        "gaming ", "gambling dealer", "gambling cage",
        "amusement", "recreation attendant",
        "tour guide", "travel agent", "travel guide",
        "reservation",
        "dishwasher",
        "butcher", "meat cutter", "meat, poultry",
        "slaughterer",
        "hairdresser", "hairstylist", "cosmetologist",
        "manicurist", "pedicurist", "barber",
        "skincare specialist", "shampooer",
        "spa manager",
        "laundry and dry-cleaning",
        "funeral attendant", "funeral home",
        "entertainment and recreation manager",
        "ushers, lobby",
        "counter and rental clerk",
        "locker room, coatroom",
    ]),

    # ── Agriculture & Environment ─────────────────────────────────────────────
    ("agriculture", [
        "farmer,", "farmers,", "rancher", "farmworker",
        "agricultural", "crop ", "harvesting",
        "forest", "conservation", "wildlife",
        "fishing", "hunting",
        "animal breed", "animal caretaker", "animal scientist",
        "animal trainer",
        "log grader", "logging equipment",
        "tree trimmer",
        "landscaping and groundskeeping",
        "first-line supervisors of landscaping",
        "first-line supervisors of farming",
        "buyers and purchasing agents, farm",
        "grader,", "sorter,",
        "pesticide",
        "recycling coordinator", "recycling and reclamation",
        "refuse and recyclable",
        "water and wastewater treatment",
        "geothermal technician",
        "hydroelectric plant technician",
        "biomass plant technician",
        "biofuels",
        "solar sales", "solar panel",
        "wind turbine",
        "petroleum pump system",
        "gas compressor", "gas plant operator",
        "brownfield redevelopment",
    ]),

    # ── Social Services ────────────────────────────────────────────────────────
    ("social", [
        "social worker", "social and human service",
        "social science research",
        "counselor,", "counselors,",
        "child care", "childcare",
        "community service", "community health",
        "personal care", "home care aide",
        "residential advisor",
        "eligibility interviewer",
        "clergy",
        "recreation worker",
        "fitness and wellness",
        "coaches, except",
        "nanny", "nannies",
        "interpreters and translators",
    ]),

    # ── Management & Business (broad catch-all) ────────────────────────────────
    ("management", [
        " manager", "managers,",
        "executive", "administrator",
        "supervisor", "director,",
        "coordinator",
        "analyst", "consultant",
        "specialist",
        "buyer,", "purchasing",
        "human resources",
        "training and development",
        "sales representative", "sales agent",
        "marketing ", "advertising",
        "real estate",
        "property, real estate",
        "secretary", "administrative assistant",
        "clerk,", "clerks,",
        "receptionist",
    ]),
]

# ── Explicit fallback for any remaining uncaught titles ────────────────────────

_FALLBACK: Dict[str, str] = {
    "Actors": "arts",
    "Embalmers": "healthcare",
    "Fallers": "agriculture",
    "Fashion Models": "arts",
    "Instructional Coordinators": "education",
    "Models": "arts",
    "Orderlies": "healthcare",
    "Public Relations Specialists": "management",
    "Upholsterers": "trades",
}


# ── Public API ────────────────────────────────────────────────────────────────

def classify_title(title: str) -> str:
    """Return an industry_id for a single job title."""
    lower = title.lower()
    for industry_id, keywords in _RULES:
        if any(kw in lower for kw in keywords):
            return industry_id
    if title in _FALLBACK:
        return _FALLBACK[title]
    return "management"  # last-resort


def classify_titles(titles: Iterable[str]) -> Dict[str, str]:
    """Return {title -> industry_id} for all given titles."""
    return {t: classify_title(t) for t in titles}
