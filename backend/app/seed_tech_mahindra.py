"""Add Tech Mahindra questions to the question bank."""
from __future__ import annotations
import asyncio
import uuid
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from app.models.tenant import (
    QuizItem, ReadingPassage, ListeningPassage, WritingPrompt, TaskItem,
)

MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "CommunicationIQ"
def uid() -> str:
    return str(uuid.uuid4())

def _rand_difficulty() -> float:
    import random as _r
    r = _r.random()
    if r < 0.30:
        return round(_r.uniform(0.1, 0.33), 2)
    elif r < 0.70:
        return round(_r.uniform(0.34, 0.66), 2)
    else:
        return round(_r.uniform(0.67, 0.95), 2)

TECH_MAHINDRA_QUIZ = [
    {"stem": "Tech Mahindra was founded in:", "options": ["1975", "1986", "1995", "2000"], "correct_index": 1, "explanation": "Tech Mahindra was founded in 1986."},
    {"stem": "Tech Mahindra is headquartered in:", "options": ["Mumbai", "Pune", "Noida", "Hyderabad"], "correct_index": 1, "explanation": "Tech Mahindra is headquartered in Pune, Maharashtra."},
    {"stem": "Tech Mahindra is a subsidiary of:", "options": ["Tata Group", "Mahindra Group", "Reliance", "Adani"], "correct_index": 1, "explanation": "Tech Mahindra is part of the Mahindra Group."},
    {"stem": "Tech Mahindra's stock trades on:", "options": ["NYSE", "BSE and NSE", "NASDAQ", "LSE"], "correct_index": 1, "explanation": "Tech Mahindra trades on BSE and NSE in India."},
    {"stem": "Tech Mahindra acquired which company in 2015?", "options": ["Wipro", "Satyam Computer Services", "HCL", "Infosys"], "correct_index": 1, "explanation": "Tech Mahindra merged with Satyam Computer Services in 2015."},
    {"stem": "Tech Mahindra operates in approximately how many countries?", "options": ["30", "50", "90", "120"], "correct_index": 2, "explanation": "Tech Mahindra operates in approximately 90 countries."},
    {"stem": "Tech Mahindra employs approximately how many people?", "options": ["100,000", "150,000", "200,000+", "350,000"], "correct_index": 2, "explanation": "Tech Mahindra has 200,000+ employees worldwide."},
    {"stem": "What is Tech Mahindra's focus area?", "options": ["Only IT services", "IT, telecom, and digital transformation", "Only consulting", "Only manufacturing"], "correct_index": 1, "explanation": "Tech Mahindra focuses on IT, telecom, and digital transformation."},
    {"stem": "Tech Mahindra's annual revenue is approximately:", "options": ["$3 billion", "$5 billion", "$7 billion", "$15 billion"], "correct_index": 2, "explanation": "Tech Mahindra's annual revenue is approximately $7+ billion."},
    {"stem": "What is Tech Mahindra's digital platform called?", "options": ["Nia", "HOLMES", "TechM AirVil", "iON"], "correct_index": 2, "explanation": "TechM AirVil is Tech Mahindra's digital platform."},
]

TECH_MAHINDRA_READING = [{
    "title": "Tech Mahindra Digital Transformation",
    "body": "Tech Mahindra is a leading provider of digital transformation, consulting, and business re-engineering services. With over 200,000 employees across 90 countries, the company serves clients in telecommunications, manufacturing, financial services, and healthcare. Tech Mahindra's integrated portfolio of services includes 5G, cloud, cybersecurity, AI/ML, and IoT solutions. The company's NP-SAT employee engagement model and focus on diversity have earned it recognition as a Top Employer globally. Their merger with Satyam Computer Services in 2015 created one of India's largest IT services companies.",
    "kind": "Tech Mahindra",
    "questions": [
        {"stem": "How many employees does Tech Mahindra have?", "options": ["100,000", "150,000", "200,000+", "350,000"], "correct_index": 2, "explanation": "Tech Mahindra has over 200,000 employees."},
        {"stem": "Which company did Tech Mahindra merge with?", "options": ["Wipro", "Satyam Computer Services", "HCL", "Infosys"], "correct_index": 1, "explanation": "Tech Mahindra merged with Satyam Computer Services."},
        {"stem": "In how many countries does Tech Mahindra operate?", "options": ["30", "50", "90", "120"], "correct_index": 2, "explanation": "Tech Mahindra operates in approximately 90 countries."},
        {"stem": "What sectors does Tech Mahindra serve?", "options": ["Only telecom", "Telecom, manufacturing, financial services, healthcare", "Only IT", "Only consulting"], "correct_index": 1, "explanation": "Tech Mahindra serves telecom, manufacturing, financial services, and healthcare."},
        {"stem": "What is Tech Mahindra's employee engagement model called?", "options": ["MyEureka", "NP-SAT", "Lex", "Ultimatix"], "correct_index": 1, "explanation": "NP-SAT is Tech Mahindra's employee engagement model."},
    ],
}]

TECH_MAHINDRA_LISTENING = [{
    "title": "Tech Mahindra Project Standup",
    "transcript": "Good morning team. Let's do a quick standup. Priya, what did you complete yesterday? Priya: I finished the 5G network optimization module. Raj: I resolved the API integration issue with the client's legacy system. Anita: I completed the test automation suite. Great progress. What's planned for today? Priya: Starting the cloud migration phase. Raj: Documenting the API changes. Anita: Running regression tests. Any blockers? Raj needs access to the client's staging environment. I'll escalate that today. Sprint review is on Friday. Let's ensure all deliverables are on track.",
    "kind": "Tech Mahindra",
    "questions": [
        {"stem": "What did Priya complete yesterday?", "options": ["API integration", "5G network optimization module", "Test automation", "Cloud migration"], "correct_index": 1, "explanation": "Priya finished the 5G network optimization module."},
        {"stem": "What issue did Raj resolve?", "options": ["Database issue", "API integration with legacy system", "Cloud deployment", "Test failure"], "correct_index": 1, "explanation": "Raj resolved the API integration issue."},
        {"stem": "What is Priya's plan for today?", "options": ["Finish testing", "Start cloud migration", "Document changes", "Client meeting"], "correct_index": 1, "explanation": "Priya will start the cloud migration phase."},
        {"stem": "What blocker is mentioned?", "options": ["Budget constraints", "Access to client's staging environment", "Team availability", "Technical debt"], "correct_index": 1, "explanation": "Raj needs access to the client's staging environment."},
        {"stem": "When is the sprint review?", "options": ["Today", "Tomorrow", "Friday", "Next week"], "correct_index": 2, "explanation": "The sprint review is on Friday."},
    ],
}]

TECH_MAHINDRA_WRITING = [
    {"title": "Tech Mahindra Project Proposal", "prompt": "Write a proposal for implementing Tech Mahindra's 5G solutions for a telecom client. Include technical approach, timeline, and expected benefits.", "kind": "Tech Mahindra", "key_points": ["5G technology overview", "Implementation phases", "Expected benefits", "Timeline", "Risk assessment"]},
    {"title": "Tech Mahindra Client Presentation", "prompt": "Write a presentation outline for Tech Mahindra's digital transformation capabilities. Include service offerings, case studies, and pricing model.", "kind": "Tech Mahindra", "key_points": ["Service overview", "Case studies", "Differentiators", "Pricing model", "Next steps"]},
]

TECH_MAHINDRA_SPEAKING = [
    {"prompt": "Describe Tech Mahindra's role in the 5G revolution. What solutions do they offer?", "task_type": "professional", "reference_text": "Cover 5G capabilities, telecom expertise, digital solutions, and market position"},
    {"prompt": "Explain Tech Mahindra's approach to digital transformation for enterprises.", "task_type": "professional", "reference_text": "Cover cloud, AI/ML, IoT, cybersecurity, and consulting services"},
]

async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    await init_beanie(
        database=client[DB_NAME],
        document_models=[QuizItem, ReadingPassage, ListeningPassage, WritingPrompt, TaskItem],
    )
    
    count = 0
    
    # Quiz items
    for q in TECH_MAHINDRA_QUIZ:
        existing = await QuizItem.find(QuizItem.stem == q["stem"]).first()
        if existing:
            continue
        item = QuizItem(
            id=uid(), category="company_info", stem=q["stem"],
            options=q["options"], correct_index=q["correct_index"],
            explanation=q["explanation"], company="Tech Mahindra",
            seconds_allowed=30, difficulty=_rand_difficulty(), status="published",
        )
        await item.create()
        count += 1
    
    # Reading passages
    for p in TECH_MAHINDRA_READING:
        existing = await ReadingPassage.find(ReadingPassage.title == p["title"]).first()
        if existing:
            continue
        passage = ReadingPassage(
            id=uid(), title=p["title"], body=p["body"], kind=p["kind"],
            status="published", questions=[
                {"id": uid(), "stem": q["stem"], "options": q["options"],
                 "correct_index": q["correct_index"], "explanation": q["explanation"]}
                for q in p["questions"]
            ],
        )
        await passage.create()
        count += 1
    
    # Listening passages
    for p in TECH_MAHINDRA_LISTENING:
        existing = await ListeningPassage.find(ListeningPassage.title == p["title"]).first()
        if existing:
            continue
        passage = ListeningPassage(
            id=uid(), title=p["title"], transcript=p["transcript"], kind=p["kind"],
            status="published", questions=[
                {"id": uid(), "stem": q["stem"], "options": q["options"],
                 "correct_index": q["correct_index"], "explanation": q["explanation"]}
                for q in p["questions"]
            ],
        )
        await passage.create()
        count += 1
    
    # Writing prompts
    for p in TECH_MAHINDRA_WRITING:
        existing = await WritingPrompt.find(WritingPrompt.title == p["title"]).first()
        if existing:
            continue
        wp = WritingPrompt(
            id=uid(), title=p["title"], prompt=p["prompt"], kind=p["kind"],
            status="published", key_points=p["key_points"],
        )
        await wp.create()
        count += 1
    
    # Speaking items
    for p in TECH_MAHINDRA_SPEAKING:
        existing = await TaskItem.find(TaskItem.prompt_text == p["prompt"]).first()
        if existing:
            continue
        item = TaskItem(
            id=uid(), task_type=p["task_type"], prompt_text=p["prompt"],
            company="Tech Mahindra", reference_text=p["reference_text"],
            status="published",
        )
        await item.create()
        count += 1
    
    # Count totals
    total_quiz = await QuizItem.find(QuizItem.company == "Tech Mahindra").count()
    total_reading = await ReadingPassage.find(ReadingPassage.kind == "Tech Mahindra").count()
    total_listening = await ListeningPassage.find(ListeningPassage.kind == "Tech Mahindra").count()
    total_writing = await WritingPrompt.find(WritingPrompt.kind == "Tech Mahindra").count()
    total_speaking = await TaskItem.find(TaskItem.company == "Tech Mahindra").count()
    
    print(f"Added {count} new Tech Mahindra questions")
    print(f"Tech Mahindra totals: Quiz={total_quiz}, Reading={total_reading}, Listening={total_listening}, Writing={total_writing}, Speaking={total_speaking}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
