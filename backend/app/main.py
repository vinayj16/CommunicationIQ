"""CommunicationIQ backend.

FastAPI backed by MongoDB, with one control-plane database and one database per
institution. The authenticated session resolves the tenant database; callers
never supply it.
"""
import asyncio
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import (attempts, auth, game, invitations, listening,
                          platform_admin, platform_export,
                          reading, report, writing,
                          platform_writes, practice, student, tenant_admin,
                          tenant_writes)

log = logging.getLogger(__name__)


@asynccontextmanager
async def _seed_core_tests():
    """Create the 4 core exam tests if none exist."""
    from app.models.platform import ExamTest
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    core_tests = [
        {
            "name": "Baseline Diagnostic",
            "description": "Short diagnostic taken once, before any training is assigned. Establishes the starting point every later attempt is measured against.",
            "slug": "baseline-diagnostic",
            "duration_minutes": 15,
            "reading_questions": 10, "listening_questions": 10,
            "writing_questions": 10, "speaking_questions": 5,
            "reading_seconds": 300, "listening_seconds": 300,
            "writing_seconds": 300, "speaking_seconds": 60,
            "is_active": True, "is_baseline": True, "company": "",
            "one_shot_audio": True, "show_timer": True, "allow_pause": False,
        },
        {
            "name": "Professional English",
            "description": "The long one: ten parts across all four skills, on workplace material throughout. Built to be sat once and read carefully, not repeated weekly.",
            "slug": "professional-english",
            "duration_minutes": 55,
            "reading_questions": 10, "listening_questions": 10,
            "writing_questions": 10, "speaking_questions": 10,
            "reading_seconds": 600, "listening_seconds": 600,
            "writing_seconds": 600, "speaking_seconds": 120,
            "is_active": True, "is_baseline": False, "company": "",
            "one_shot_audio": True, "show_timer": True, "allow_pause": False,
        },
        {
            "name": "Versant-style 4 Skills",
            "description": "Speaking, listening, reading and writing in one sitting. The report gives a score per skill, because a single number over four different abilities describes none of them.",
            "slug": "versant-4-skills",
            "duration_minutes": 30,
            "reading_questions": 10, "listening_questions": 10,
            "writing_questions": 10, "speaking_questions": 10,
            "reading_seconds": 450, "listening_seconds": 450,
            "writing_seconds": 450, "speaking_seconds": 90,
            "is_active": True, "is_baseline": False, "company": "",
            "one_shot_audio": True, "show_timer": True, "allow_pause": False,
        },
        {
            "name": "Versant-style Speaking Test",
            "description": "The Pearson Versant-style spoken test, six parts: read on cue, repeat what you hear, short answers, sentence builds, story retelling, and open questions.",
            "slug": "versant-speaking",
            "duration_minutes": 22,
            "reading_questions": 0, "listening_questions": 10,
            "writing_questions": 0, "speaking_questions": 20,
            "reading_seconds": 0, "listening_seconds": 300,
            "writing_seconds": 0, "speaking_seconds": 60,
            "is_active": True, "is_baseline": False, "company": "",
            "one_shot_audio": True, "show_timer": True, "allow_pause": False,
        },
    ]
    for t in core_tests:
        await ExamTest(**t, created_at=now, updated_at=now).create()
    log.info("Seeded %d core exam tests", len(core_tests))


async def _sync_exam_test_profiles():
    """Create SimulationProfiles + ProfileSections for every ExamTest that lacks one."""
    import uuid as _uuid
    from datetime import datetime as _dt, timezone as _tz
    from app.db import control_db as _cdb
    from app.models.platform import ExamTest as _ET

    db = _cdb()
    now = _dt.now(_tz.utc)
    task_types = {
        'reading': 'reading_comprehension',
        'listening': 'audio_comprehension',
        'writing': 'writing_task',
        'speaking': 'open_response',
    }
    tests = await _ET.find_all().to_list()
    for t in tests:
        existing = await db.simulation_profiles.find_one({'name': t.name})
        if existing:
            continue
        profile_id = str(_uuid.uuid4())
        sections = []
        pos = 1
        for module, count in [
            ('reading', t.reading_questions),
            ('listening', t.listening_questions),
            ('writing', t.writing_questions),
            ('speaking', t.speaking_questions),
        ]:
            if count <= 0:
                continue
            secs_key = f'{module}_seconds'
            resp_secs = getattr(t, secs_key, 300) // count if count else 30
            sections.append({
                '_id': str(_uuid.uuid4()), 'profile_id': profile_id,
                'position': pos, 'title': module.capitalize(),
                'task_type': task_types.get(module, 'reading_comprehension'),
                'instructions': f'Complete the {module} section.',
                'item_count': count, 'prep_seconds': 10,
                'response_seconds': resp_secs,
                'prompt_plays_allowed': 1 if module == 'listening' else 0,
                'allow_replay': False, 'weight': 1.0, 'selection': {},
            })
            pos += 1
        await db.simulation_profiles.insert_one({
            '_id': profile_id, 'name': t.name, 'code': '',
            'style': 'simulation', 'company': t.company,
            'description': t.description, 'status': 'published',
            'estimated_minutes': t.duration_minutes,
            'is_baseline': t.is_baseline, 'scoring_weights': {},
            'pass_threshold': 0.6, 'skill_thresholds': {},
            'created_at': now, 'updated_at': now,
        })
        if sections:
            await db.profile_sections.insert_many(sections)
        log.info("Created SimulationProfile for ExamTest: %s", t.name)


async def lifespan(_app: FastAPI):
    """Load the speech model before the first student needs it.

    In a thread, and without blocking startup: a cold load is a couple of
    seconds from cache and a couple of minutes on a machine that has never
    downloaded the weights. Neither should delay the health check, and
    neither should stop the API serving ΓÇö a host where the model will not
    load falls back to Tier 0 and says so in the provider console.
    """
    # Connect to MongoDB and register the control-plane documents. Tenant
    # databases are bound lazily on first use, so nothing here names a real
    # institution schema.
    try:
        from app.db import init_store

        await init_store()
    except Exception:  # noqa: BLE001 — never block startup on this
        log.exception("MongoDB init failed")

    # Seed default companies if none exist
    try:
        from app.db import control_db
        from app.models.tenant import Company
        db = control_db()
        existing = await db.companies.count_documents({})
        if existing == 0:
            companies_data = [
                {"name": "Deloitte", "slug": "deloitte", "color": "#86bc25", "description": "Deloitte Touche Tohmatsu Limited"},
                {"name": "IBM", "slug": "ibm", "color": "#0530ad", "description": "International Business Machines Corporation"},
                {"name": "HCL", "slug": "hcl", "color": "#0072c6", "description": "HCL Technologies Limited"},
                {"name": "ADP", "slug": "adp", "color": "#d0271d", "description": "Automatic Data Processing, Inc."},
                {"name": "Virtusa", "slug": "virtusa", "color": "#00a651", "description": "Virtusa Corporation"},
                {"name": "LTI", "slug": "lti", "color": "#e4002b", "description": "Larsen & Toubro Infotech Limited"},
            ]
            for c in companies_data:
                company = Company(**c)
                await company.create()
            log.info("Seeded %d default companies", len(companies_data))
    except Exception:
        log.exception("Company seeding failed")

    # Seed general tenant for external users if not exists
    try:
        from app.models.platform import Tenant, TenantUserDirectory
        existing = await Tenant.find_one(Tenant.slug == "general")
        if not existing:
            general_tenant = Tenant(
                name="General Users",
                slug="general",
                tenant_type="other",
                status="active",
                seat_limit=10000,
            )
            await general_tenant.create()
            log.info("Created general tenant for external users")
    except Exception:
        log.exception("General tenant seeding failed")

    # Seed default subscription plans if none exist
    try:
        from app.db import control_db as _cdb
        from app.models.platform import Plan
        _db = _cdb()
        plan_count = await _db.plans.count_documents({})
        if plan_count == 0:
            plans_data = [
                {
                    "name": "Free Trial",
                    "slug": "free-trial",
                    "description": "Get started with limited practice questions and basic features. Perfect for trying out CommunicationIQ.",
                    "price_monthly": 0.0,
                    "price_yearly": 0.0,
                    "seat_limit": 1,
                    "features": ["5 practice questions per day", "Basic analytics", "1 attempt per test"],
                    "max_questions": 5,
                    "max_exams_per_day": 1,
                    "has_proctoring": False,
                    "has_analytics": True,
                    "has_custom_branding": False,
                    "has_api_access": False,
                    "is_active": True,
                    "is_default": True,
                },
                {
                    "name": "1-Week Trial",
                    "slug": "weekly-trial",
                    "description": "Full access for 7 days. Try all features including proctoring and company-specific tests.",
                    "price_monthly": 9.99,
                    "price_yearly": 0.0,
                    "seat_limit": 1,
                    "features": ["Unlimited practice questions", "Full analytics", "3 attempts per test", "Proctoring", "Company-specific tests"],
                    "max_questions": 500,
                    "max_exams_per_day": 3,
                    "has_proctoring": True,
                    "has_analytics": True,
                    "has_custom_branding": False,
                    "has_api_access": False,
                    "is_active": True,
                    "is_default": False,
                },
                {
                    "name": "Monthly Pro",
                    "slug": "monthly-pro",
                    "description": "Unlimited access with proctoring, analytics, and all company tests. Billed monthly.",
                    "price_monthly": 29.99,
                    "price_yearly": 299.99,
                    "seat_limit": 1,
                    "features": ["Unlimited practice", "Advanced analytics", "Unlimited attempts", "Proctoring", "All company tests", "Priority support"],
                    "max_questions": 5000,
                    "max_exams_per_day": 50,
                    "has_proctoring": True,
                    "has_analytics": True,
                    "has_custom_branding": False,
                    "has_api_access": False,
                    "is_active": True,
                    "is_default": False,
                },
                {
                    "name": "Custom Enterprise",
                    "slug": "custom-enterprise",
                    "description": "Tailored solution for institutions and enterprises. Contact us for pricing.",
                    "price_monthly": 0.0,
                    "price_yearly": 0.0,
                    "seat_limit": 10000,
                    "features": ["Everything in Monthly Pro", "Custom branding", "API access", "Dedicated support", "Bulk student management", "Custom test creation"],
                    "max_questions": 999999,
                    "max_exams_per_day": 999,
                    "has_proctoring": True,
                    "has_analytics": True,
                    "has_custom_branding": True,
                    "has_api_access": True,
                    "is_active": True,
                    "is_default": False,
                },
            ]
            for p_data in plans_data:
                plan = Plan(**p_data)
                await plan.create()
            log.info("Seeded %d subscription plans", len(plans_data))
    except Exception:
        log.exception("Plan seeding failed")

    # Operator-configured AI settings: create the table on an estate that
    # predates it, then fold any stored overrides onto the live settings so
    # the configured provider/model/keys are in force before the first
    # narration job runs. Failure falls back to environment defaults.
    try:
        from app import ai_settings
        await ai_settings.ensure_table()
        applied = await ai_settings.load_and_apply()
        if applied:
            log.info("AI narration overrides applied: %s",
                     ", ".join(sorted(applied)))
    except Exception:  # noqa: BLE001 ΓÇö env defaults still work
        log.exception("AI settings load failed; using environment defaults")

    engine = _engine_tier()
    if engine["tier"] == 0:
        log.warning(
            "TIER 0 ONLY - speech models unavailable (%s). Pronunciation, "
            "accuracy, grammar and content will report as unscored.",
            ", ".join(engine["missing"]))
    else:
        log.info("Tier 1 speech engine available")



    # The narration recovery sweeper. The fast path is a BackgroundTask fired
    # when an attempt is scored; this loop is the durability net, so a job left
    # pending or half-processed by a restart is picked up rather than lost.
    narration_task = None
    if settings.narration_enabled and settings.narration_worker_enabled:
        from app.narration.worker import run_forever
        narration_task = asyncio.create_task(run_forever())

    # Seed core exam tests if none exist
    try:
        from app.db import control_db as _cdb2
        _db2 = _cdb2()
        count = await _db2.exam_tests.count_documents({})
        if count == 0:
            await _seed_core_tests()
    except Exception:
        log.exception("Failed to seed core exam tests")

    # Ensure SimulationProfiles exist for every ExamTest
    try:
        await _sync_exam_test_profiles()
    except Exception:
        log.exception("Failed to sync exam test profiles")

    # AI question generation scheduler
    question_gen_task = None
    if settings.auto_question_generation and settings.groq_api_key:
        from app.question_generator import start_scheduler
        start_scheduler()
        log.info("AI question generation scheduler started")

    yield

    if narration_task is not None:
        narration_task.cancel()
        try:
            await narration_task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass

    from app.question_generator import stop_scheduler
    stop_scheduler()


app = FastAPI(
    lifespan=lifespan,
    title="CommunicationIQ API",
    version="0.1.0",
    description=(
        "Communication assessment and training for placement readiness. "
        "Every AI capability sits behind a versioned provider contract; every "
        "score carries the provider and version that produced it."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API = "/api/v1"
app.include_router(auth.router, prefix=API)
app.include_router(student.router, prefix=API)
app.include_router(student.consent_router, prefix=API)
app.include_router(attempts.router, prefix=API)
app.include_router(listening.router, prefix=API)
app.include_router(reading.router, prefix=API)
app.include_router(writing.router, prefix=API)
app.include_router(game.router, prefix=API)
app.include_router(practice.router, prefix=API)
app.include_router(tenant_admin.router, prefix=API)
app.include_router(tenant_writes.router, prefix=API)
app.include_router(platform_admin.router, prefix=API)
app.include_router(platform_admin.asset_router, prefix=API)
app.include_router(platform_writes.router, prefix=API)
app.include_router(platform_export.router, prefix=API)
app.include_router(invitations.router, prefix=API)
app.include_router(report.router, prefix=API)
# Unauthenticated. A candidate arrives holding a token and nothing else, so
# this is the one router with no session behind it -- see its module docstring
# for the three rules that make that safe.
app.include_router(invitations.public, prefix=API)


def _engine_tier() -> dict:
    """Which scoring tier this instance can actually run.

    Reported rather than assumed. The Tier-1 imports sit inside their
    providers, so an instance without them starts perfectly and then scores
    nothing but timing -- a difference invisible from the outside and easy to
    mistake for the model simply disagreeing with you. Anyone looking at a
    deployment should be able to see which one they have.
    """
    missing: list[str] = []
    for name in ("torch", "torchaudio", "transformers"):
        try:
            __import__(name)
        except Exception:  # noqa: BLE001 ΓÇö absent or broken, same conclusion
            missing.append(name)

    if not missing:
        return {"tier": 1, "speech_models": "available"}
    return {
        "tier": 0,
        "speech_models": "unavailable",
        "missing": missing,
        "effect": ("Pronunciation, accuracy, grammar and content report as "
                   "unscored. Timing measures still work. Install "
                   "requirements-engine.txt to enable them."),
    }


def _build_commit() -> str:
    """Which commit this process is running, if it can tell.

    Render injects RENDER_GIT_COMMIT into every service; a local checkout has
    a .git directory instead. Either way this is read once at import and never
    guessed -- an endpoint that reports a version it is not sure about is
    worse than one that admits it does not know.
    """
    import os
    import subprocess

    commit = os.environ.get("RENDER_GIT_COMMIT", "").strip()
    if commit:
        return commit[:12]
    try:
        out = subprocess.run(["git", "rev-parse", "--short=12", "HEAD"],
                             capture_output=True, text=True, timeout=5,
                             cwd=str(Path(__file__).resolve().parent.parent))
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:  # noqa: BLE001 - no git, no repo, no matter
        return ""


BUILD_COMMIT = _build_commit()


@app.get("/healthz", tags=["ops"])
async def healthz() -> dict:
    """Liveness, plus what is actually running here.

    The commit is reported because working out which build was live took
    behavioural fingerprinting -- probing for an endpoint that only exists in
    a later commit, and diffing a user-visible string against the source. That
    works, but it is archaeology, and it gets harder every release.
    """
    return {"status": "ok", "service": "communicationiq-api",
            "commit": BUILD_COMMIT or "unknown",
            "engine": _engine_tier()}


@app.get(API + "/meta/capability", tags=["ops"])
async def capability() -> dict:
    """What this deployment can actually measure, for the client to say so.

    /healthz reports the same thing for operators. This exists because the
    people who most need to know are candidates: a student who spends twenty
    minutes on a simulation deserves to be told beforehand that this server
    cannot score pronunciation, rather than discovering it on a results page
    with four blanks on it. Unauthenticated, because it describes the server
    and nothing about anyone using it.
    """
    engine = _engine_tier()
    full = engine["tier"] >= 1
    return {
        "tier": engine["tier"],
        "full_scoring": full,
        "measures": (["pronunciation", "accuracy", "grammar", "content",
                      "fluency", "latency", "disfluency"] if full
                     else ["fluency", "latency"]),
        # Said plainly, and only when it is true.
        "note": "" if full else (
            "This server measures timing and fluency only. Pronunciation, "
            "accuracy, grammar and content need speech-recognition models that "
            "are not installed here, so they will show as not measured ΓÇö and "
            "there will be no overall score, which needs at least three "
            "measures. Your practice still counts."),
    }
