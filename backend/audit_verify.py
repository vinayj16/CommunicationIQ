"""Comprehensive automated audit: verify all endpoints, linking, and data flow."""
import asyncio, os, sys
sys.path.insert(0, os.path.dirname(__file__))

async def audit():
    from app.db import init_store
    await init_store()
    from app.models.tenant import (
        Company, ReadingPassage, ListeningPassage, WritingPrompt,
        QuizItem, SimulationProfile, ProfileSection,
    )

    errors = []
    warnings = []

    # =========================================================
    # 1. COMPANIES
    # =========================================================
    companies = await Company.find(Company.is_active == True).to_list()
    print(f"[1] COMPANIES: {len(companies)} active")
    if len(companies) < 8:
        errors.append(f"Expected 8 companies, found {len(companies)}")
    for c in companies:
        print(f"    {c.name} (slug={c.slug}, color={c.color})")

    # =========================================================
    # 2. READING: passages + linked quiz items
    # =========================================================
    print()
    rps = await ReadingPassage.find(ReadingPassage.status == "published").to_list()
    rp_by_company = {}
    for p in rps:
        c = getattr(p, "company", "") or ""
        rp_by_company.setdefault(c, 0)
        rp_by_company[c] += 1

    coll_qi = QuizItem.get_motor_collection()
    reading_qi_by_company = {}
    for d in await coll_qi.aggregate([
        {"$match": {"category": "reading_comprehension", "status": "published"}},
        {"$group": {"_id": "$company", "count": {"$sum": 1}, "passages": {"$addToSet": "$passage_id"}}}
    ]).to_list():
        reading_qi_by_company[d["_id"]] = {"count": d["count"], "passages": len(d["passages"])}

    print(f"[2] READING: {len(rps)} passages")
    for c in sorted(rp_by_company.keys()):
        qi = reading_qi_by_company.get(c, {"count": 0, "passages": 0})
        status = "OK" if rp_by_company[c] >= 10 and qi["count"] >= 5 else "LOW"
        print(f"    {c!r}: {rp_by_company[c]} passages, {qi['count']} quiz_items, {qi['passages']} linked passages [{status}]")
        if rp_by_company[c] < 10:
            warnings.append(f"Reading {c}: only {rp_by_company[c]} passages")

    # Check orphaned quiz_items
    rp_ids = set(p.id for p in rps)
    orphaned_r = set()
    for d in await coll_qi.distinct("passage_id", {"category": "reading_comprehension"}):
        if d and d not in rp_ids:
            orphaned_r.add(d)
    if orphaned_r:
        warnings.append(f"Reading: {len(orphaned_r)} orphaned passage_ids in quiz_items")
        print(f"    WARNING: {len(orphaned_r)} orphaned passage_ids")

    # =========================================================
    # 3. LISTENING: passages + linked quiz items
    # =========================================================
    lps = await ListeningPassage.find(ListeningPassage.status == "published").to_list()
    lp_by_company = {}
    for p in lps:
        c = getattr(p, "company", "") or ""
        lp_by_company.setdefault(c, 0)
        lp_by_company[c] += 1

    listening_qi_by_company = {}
    for d in await coll_qi.aggregate([
        {"$match": {"category": "audio_comprehension", "status": "published"}},
        {"$group": {"_id": "$company", "count": {"$sum": 1}, "passages": {"$addToSet": "$passage_id"}}}
    ]).to_list():
        listening_qi_by_company[d["_id"]] = {"count": d["count"], "passages": len(d["passages"])}

    print(f"\n[3] LISTENING: {len(lps)} passages")
    for c in sorted(lp_by_company.keys()):
        qi = listening_qi_by_company.get(c, {"count": 0, "passages": 0})
        status = "OK" if lp_by_company[c] >= 10 and qi["count"] >= 5 else "LOW"
        print(f"    {c!r}: {lp_by_company[c]} passages, {qi['count']} quiz_items, {qi['passages']} linked [{status}]")

    lp_ids = set(p.id for p in lps)
    orphaned_l = set()
    for d in await coll_qi.distinct("passage_id", {"category": "audio_comprehension"}):
        if d and d not in lp_ids:
            orphaned_l.add(d)
    if orphaned_l:
        warnings.append(f"Listening: {len(orphaned_l)} orphaned passage_ids")

    # =========================================================
    # 4. WRITING: prompts per company
    # =========================================================
    wps = await WritingPrompt.find(WritingPrompt.status == "published").to_list()
    wp_by_company = {}
    for p in wps:
        c = getattr(p, "company", "") or ""
        wp_by_company.setdefault(c, 0)
        wp_by_company[c] += 1

    print(f"\n[4] WRITING: {len(wps)} prompts")
    for c in sorted(wp_by_company.keys()):
        status = "OK" if wp_by_company[c] >= 10 else "LOW"
        print(f"    {c!r}: {wp_by_company[c]} prompts [{status}]")

    # =========================================================
    # 5. QUIZ: grammar + vocab per company
    # =========================================================
    quiz_by_cat_company = {}
    for d in await coll_qi.aggregate([
        {"$match": {"category": {"$in": ["grammar", "vocabulary"]}, "status": "published"}},
        {"$group": {"_id": {"cat": "$category", "company": "$company"}, "count": {"$sum": 1}}}
    ]).to_list():
        key = (d["_id"]["cat"], d["_id"]["company"])
        quiz_by_cat_company[key] = d["count"]

    print(f"\n[5] QUIZ (grammar + vocab)")
    all_companies = sorted(set(c for _, c in quiz_by_cat_company.keys()))
    for c in all_companies:
        g = quiz_by_cat_company.get(("grammar", c), 0)
        v = quiz_by_cat_company.get(("vocabulary", c), 0)
        total = g + v
        status = "OK" if total >= 10 else "LOW"
        print(f"    {c!r}: grammar={g}, vocab={v}, total={total} [{status}]")

    # =========================================================
    # 6. PROFILES: company exam profiles
    # =========================================================
    profiles = await SimulationProfile.find().to_list()
    company_profiles = [p for p in profiles if p.company]
    general_profiles = [p for p in profiles if not p.company]

    print(f"\n[6] PROFILES: {len(profiles)} total ({len(company_profiles)} company, {len(general_profiles)} general)")
    for p in company_profiles:
        secs = await ProfileSection.find(ProfileSection.profile_id == p.id).count()
        total_items = sum(s.item_count for s in await ProfileSection.find(ProfileSection.profile_id == p.id).to_list())
        status = "OK" if secs >= 4 and total_items >= 20 else "LOW"
        print(f"    {p.company}: {p.name} - {secs} sections, {total_items} items [{status}]")

    for p in general_profiles:
        secs = await ProfileSection.find(ProfileSection.profile_id == p.id).count()
        total_items = sum(s.item_count for s in await ProfileSection.find(ProfileSection.profile_id == p.id).to_list())
        print(f"    General: {p.name} - {secs} sections, {total_items} items")

    # =========================================================
    # 7. CROSS-CHECK: company in Company model matches profiles
    # =========================================================
    company_names = {c.name for c in companies}
    profile_companies = {p.company for p in company_profiles}
    missing_in_company = profile_companies - company_names
    missing_profiles = company_names - profile_companies
    print(f"\n[7] CROSS-CHECK")
    if missing_in_company:
        errors.append(f"Profiles reference companies not in Company model: {missing_in_company}")
        print(f"    ERROR: Profiles reference missing companies: {missing_in_company}")
    if missing_profiles:
        warnings.append(f"Companies without profiles: {missing_profiles}")
        print(f"    WARNING: Companies without profiles: {missing_profiles}")
    if not missing_in_company and not missing_profiles:
        print(f"    All {len(companies)} companies have matching profiles")

    # =========================================================
    # 8. DUPLICATE CHECK
    # =========================================================
    dups = await coll_qi.aggregate([
        {"$group": {"_id": "$stem", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}}
    ]).to_list()
    print(f"\n[8] DUPLICATES: {len(dups)} duplicate stems in quiz_items")
    if dups:
        warnings.append(f"{len(dups)} duplicate quiz item stems")

    # =========================================================
    # SUMMARY
    # =========================================================
    print(f"\n{'='*60}")
    print(f"SUMMARY: {len(errors)} errors, {len(warnings)} warnings")
    print(f"{'='*60}")
    for e in errors:
        print(f"  ERROR: {e}")
    for w in warnings:
        print(f"  WARN:  {w}")
    if not errors and not warnings:
        print("  ALL CHECKS PASSED")

asyncio.run(audit())
