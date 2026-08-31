"""Full audit: companies, questions per skill, linking, duplicates."""
import asyncio, os, sys
sys.path.insert(0, os.path.dirname(__file__))

async def audit():
    from app.db import init_store
    await init_store()
    from app.models.tenant import (
        Company, ReadingPassage, ListeningPassage, WritingPrompt,
        QuizItem, TaskItem, SimulationProfile, ProfileSection,
    )

    print("=" * 60)
    print("1. COMPANIES IN Company MODEL")
    print("=" * 60)
    companies = await Company.find().to_list()
    print(f"  Total companies in Company collection: {len(companies)}")
    for c in companies:
        print(f"    {c.name} (active={c.is_active}, slug={c.slug})")

    print()
    print("=" * 60)
    print("2. READING PASSAGES - by company")
    print("=" * 60)
    rps = await ReadingPassage.find().to_list()
    rp_by_company = {}
    for p in rps:
        c = getattr(p, "company", None) or ""
        rp_by_company.setdefault(c, 0)
        rp_by_company[c] += 1
    for c, cnt in sorted(rp_by_company.items()):
        print(f"    company={c!r}: {cnt} passages")

    print()
    print("=" * 60)
    print("3. LISTENING PASSAGES - by company")
    print("=" * 60)
    lps = await ListeningPassage.find().to_list()
    lp_by_company = {}
    for p in lps:
        c = getattr(p, "company", None) or ""
        lp_by_company.setdefault(c, 0)
        lp_by_company[c] += 1
    for c, cnt in sorted(lp_by_company.items()):
        print(f"    company={c!r}: {cnt} passages")

    print()
    print("=" * 60)
    print("4. WRITING PROMPTS - by company")
    print("=" * 60)
    wps = await WritingPrompt.find().to_list()
    wp_by_company = {}
    for p in wps:
        c = getattr(p, "company", None) or ""
        wp_by_company.setdefault(c, 0)
        wp_by_company[c] += 1
    for c, cnt in sorted(wp_by_company.items()):
        print(f"    company={c!r}: {cnt} prompts")

    print()
    print("=" * 60)
    print("5. QUIZ ITEMS (grammar/vocab) - by category + company")
    print("=" * 60)
    coll = QuizItem.get_motor_collection()
    quiz_data = await coll.aggregate([
        {"$group": {"_id": {"cat": "$category", "company": "$company"}, "count": {"$sum": 1}}}
    ]).to_list()
    for d in sorted(quiz_data, key=lambda x: (-x["count"])):
        print(f"    {d['_id']['cat']} / {d['_id']['company']!r}: {d['count']}")

    print()
    print("=" * 60)
    print("6. TASK ITEMS (speaking) - by skill + company")
    print("=" * 60)
    ti_coll = TaskItem.get_motor_collection()
    ti_data = await ti_coll.aggregate([
        {"$group": {"_id": {"skill": "$skill", "company": getattr(TaskItem, 'company', '?')}, "count": {"$sum": 1}}}
    ]).to_list()
    # Simpler approach
    ti_total = await ti_coll.count_documents({})
    print(f"  Total TaskItems: {ti_total}")
    ti_skills = await ti_coll.aggregate([
        {"$group": {"_id": "$skill", "count": {"$sum": 1}}}
    ]).to_list()
    for d in ti_skills:
        print(f"    skill={d['_id']!r}: {d['count']}")

    print()
    print("=" * 60)
    print("7. PROFILES & SECTIONS")
    print("=" * 60)
    profiles = await SimulationProfile.find().to_list()
    for p in profiles:
        secs = await ProfileSection.find(ProfileSection.profile_id == p.id).sort(ProfileSection.position).to_list()
        company = getattr(p, 'company', '') or ''
        print(f"  Profile: {p.name} ({p.code}) company={company!r}")
        for s in secs:
            print(f"    [{s.position}] {s.title}: task={s.task_type} items={s.item_count}")

    print()
    print("=" * 60)
    print("8. DUPLICATE CHECK")
    print("=" * 60)
    # Check for duplicate quiz items
    dup_check = await coll.aggregate([
        {"$group": {"_id": "$stem", "count": {"$sum": 1}, "ids": {"$push": "$_id"}}},
        {"$match": {"count": {"$gt": 1}}}
    ]).to_list()
    print(f"  Quiz items with duplicate stems: {len(dup_check)}")
    for d in dup_check[:5]:
        print(f"    stem={d['_id'][:50]}... count={d['count']}")

    print()
    print("=" * 60)
    print("9. PASSAGE-QUIZITEM LINKING")
    print("=" * 60)
    r_ids = set(p.id for p in rps)
    qi_rpid = await coll.distinct("passage_id", {"category": "reading_comprehension"})
    matched = set(qi_rpid) & r_ids
    unmatched = set(qi_rpid) - r_ids
    print(f"  Reading: {len(r_ids)} passages, {len(qi_rpid)} quiz_item passage_refs, {len(matched)} matched, {len(unmatched)} orphaned")
    if unmatched:
        for uid in list(unmatched)[:3]:
            print(f"    orphaned: {uid}")

    l_ids = set(p.id for p in lps)
    qi_lpid = await coll.distinct("passage_id", {"category": "audio_comprehension"})
    matched_l = set(qi_lpid) & l_ids
    unmatched_l = set(qi_lpid) - l_ids
    print(f"  Listening: {len(l_ids)} passages, {len(qi_lpid)} quiz_item passage_refs, {len(matched_l)} matched, {len(unmatched_l)} orphaned")

asyncio.run(audit())
