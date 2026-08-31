"""
MIGRATION SEEDER — converts old-format data to new schema and seeds it.

Old format:
  Writing: { essayTopic: "...", emailTopic: "...", timeLimit: 30 }
  Reading: { paragraph: "...", questions: [{ question, options, correctAnswer }] }

New format:
  WritingPrompt: { title, kind (email/essay), prompt, company, key_points, min_words, suggested_minutes }
  ReadingPassage: { title, kind, body, company, word_count }
  QuizItem: { category: "reading_comprehension", stem, options, correct_index, passage_id, company }

Run:
    cd backend
    python -m app.migrate_data
"""
from __future__ import annotations
import asyncio
import uuid
import hashlib
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie, Document
from pydantic import Field
from app.config import settings

def uid() -> str:
    return str(uuid.uuid4())


# ── Inline models (same as seed_local_all) ────────────────────────────────

class QuizItem(Document):
    id: str = Field(default_factory=uid, alias="_id")
    tenant_id: str = ""
    category: str = ""
    stem: str
    options: list = Field(default_factory=list)
    correct_index: int = 0
    explanation: str = ""
    company: str = ""
    clip_audio_key: str = ""
    passage_id: str = ""
    seconds_allowed: int = 30
    difficulty: float = 0.0
    discrimination: float = 1.0
    skill_tags: list = Field(default_factory=list)
    topic: str = ""
    version: int = 1
    status: str = "published"
    class Settings:
        name = "quiz_items"

class ReadingPassage(Document):
    id: str = Field(default_factory=uid, alias="_id")
    tenant_id: str = ""
    title: str
    kind: str = "article"
    body: str
    company: str = ""
    word_count: int = 0
    difficulty: float = 0.0
    status: str = "published"
    class Settings:
        name = "reading_passages"

class WritingPrompt(Document):
    id: str = Field(default_factory=uid, alias="_id")
    tenant_id: str = ""
    title: str
    kind: str = "email"
    prompt: str
    company: str = ""
    scenario: str = ""
    key_points: list = Field(default_factory=list)
    min_words: int = 120
    suggested_minutes: int = 20
    difficulty: float = 0.0
    status: str = "published"
    class Settings:
        name = "writing_prompts"


MODELS = [QuizItem, ReadingPassage, WritingPrompt]


# ── Old-format writing prompts (from pasted JSON) ─────────────────────────
# Format: { essayTopic: "...", emailTopic: "...", timeLimit: 30 }

OLD_WRITING_PROMPTS = [
    {"essayTopic": "Should colleges make internships compulsory for final-year students?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Is artificial intelligence more helpful than harmful to education?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Should students be allowed to use mobile phones during college hours?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Does online education provide the same value as classroom learning?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Should public transport be made free in large cities?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Is social media improving communication or reducing real conversations?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Should companies offer flexible working hours to employees?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "How can young people contribute to environmental protection?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Should exams be replaced with continuous assessment?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Is failure an important part of success?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Should schools teach financial literacy as a compulsory subject?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Does technology make people more productive?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Should cities invest more in cycling infrastructure?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Is reading books still important in the digital age?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Should community service be compulsory for college students?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "How can students manage academic pressure effectively?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Should advertisements aimed at children be restricted?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Is remote work better than working from an office?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Should public places provide more facilities for senior citizens?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "How can individuals reduce household waste?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Should coding be taught to every school student?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Does competition motivate students to perform better?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Should college attendance be completely flexible?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "How can cities reduce traffic congestion?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Is teamwork more important than individual talent?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Should companies prioritize skills over academic qualifications?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "How does volunteering benefit young people?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Should plastic packaging be reduced by law?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Is travelling an important part of education?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Should students be encouraged to take a gap year?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "How can workplaces improve employee well-being?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Should governments provide stronger support for small businesses?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Does online shopping benefit local communities?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Should public libraries receive more funding?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "How can technology improve accessibility for people with disabilities?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Is creativity more important than technical knowledge?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Should schools introduce more project-based learning?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "How can young people protect their personal data online?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Should organizations adopt a four-day working week?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Is learning a second language important in today's world?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Should cities create more public green spaces?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "How can employers encourage ethical use of artificial intelligence?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Should students participate in career guidance programs from an early stage?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Does social media influence career choices?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Should universities focus more on practical skills?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "How can communities prepare for natural disasters?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Is traditional classroom teaching becoming outdated?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Should companies allow employees to work from anywhere?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "How can people maintain a healthy work-life balance?", "emailTopic": "", "timeLimit": 30},
    {"essayTopic": "Should public examinations include more practical tasks?", "emailTopic": "", "timeLimit": 30},
]

OLD_WRITING_EMAILS = [
    {"emailTopic": "Write an email to your college principal requesting permission to attend an external technical workshop.", "timeLimit": 15},
    {"emailTopic": "Write an email to your manager requesting one day of leave for a personal reason.", "timeLimit": 15},
    {"emailTopic": "Write an email to a company HR department asking about the status of your internship application.", "timeLimit": 15},
    {"essayTopic": "", "emailTopic": "Write an email to a professor requesting an extension for submitting an assignment.", "timeLimit": 15},
    {"emailTopic": "Write an email to a customer apologizing for a delay in delivering a service.", "timeLimit": 15},
    {"essayTopic": "", "emailTopic": "Write an email to your teammate explaining that you will be late for a project meeting.", "timeLimit": 15},
    {"emailTopic": "Write an email to the placement officer asking for details about an upcoming campus recruitment drive.", "timeLimit": 15},
    {"essayTopic": "", "emailTopic": "Write an email to a hotel requesting information about available rooms for a college event.", "timeLimit": 15},
    {"emailTopic": "Write an email to your manager suggesting a change that could improve team productivity.", "timeLimit": 15},
    {"essayTopic": "", "emailTopic": "Write an email to a library administrator requesting access to an online research database.", "timeLimit": 15},
    {"emailTopic": "Write an email to HR asking about the company's internship working hours and schedule.", "timeLimit": 15},
    {"essayTopic": "", "emailTopic": "Write an email to a professor asking for clarification about project requirements.", "timeLimit": 15},
    {"emailTopic": "Write an email to a customer explaining how to resolve a common account issue.", "timeLimit": 15},
    {"essayTopic": "", "emailTopic": "Write an email to your team leader submitting the progress report for your assigned task.", "timeLimit": 15},
    {"emailTopic": "Write an email to a college administrator reporting a problem with classroom equipment.", "timeLimit": 15},
    {"essayTopic": "", "emailTopic": "Write an email to a recruiter expressing your interest in an open software internship.", "timeLimit": 15},
    {"emailTopic": "Write an email to your supervisor requesting permission to work remotely for one day.", "timeLimit": 15},
    {"essayTopic": "", "emailTopic": "Write an email to a colleague thanking them for helping you complete a project.", "timeLimit": 15},
    {"emailTopic": "Write an email to an event organizer asking whether late registration is possible.", "timeLimit": 15},
    {"essayTopic": "", "emailTopic": "Write an email to your manager proposing a short team-building activity.", "timeLimit": 15},
    {"emailTopic": "Write an email to a professor informing them that you will miss a class due to an unavoidable commitment.", "timeLimit": 15},
    {"essayTopic": "", "emailTopic": "Write an email to the IT support team reporting a problem with your official account.", "timeLimit": 15},
    {"emailTopic": "Write an email to HR asking how to update your emergency contact information.", "timeLimit": 15},
    {"essayTopic": "", "emailTopic": "Write an email to a supplier requesting an updated quotation for office equipment.", "timeLimit": 15},
    {"emailTopic": "Write an email to your project manager asking for feedback on your recent work.", "timeLimit": 15},
    {"essayTopic": "", "emailTopic": "Write an email to a customer explaining a change in the service schedule.", "timeLimit": 15},
    {"emailTopic": "Write an email to your teammate requesting the latest version of a shared document.", "timeLimit": 15},
    {"essayTopic": "", "emailTopic": "Write an email to the college administration requesting better internet connectivity in the laboratory.", "timeLimit": 15},
    {"emailTopic": "Write an email to a recruiter asking whether fresh graduates are eligible for a position.", "timeLimit": 15},
    {"essayTopic": "", "emailTopic": "Write an email to your manager informing them about a delay caused by a technical issue.", "timeLimit": 15},
    {"emailTopic": "Write an email to a professor requesting a meeting to discuss your final-year project.", "timeLimit": 15},
    {"essayTopic": "", "emailTopic": "Write an email to the placement cell asking whether an upcoming interview will be conducted online.", "timeLimit": 15},
    {"emailTopic": "Write an email to a hotel manager requesting cancellation of a booking.", "timeLimit": 15},
    {"essayTopic": "", "emailTopic": "Write an email to a customer thanking them for providing feedback about your service.", "timeLimit": 15},
    {"emailTopic": "Write an email to HR asking about the documents required for joining.", "timeLimit": 15},
    {"essayTopic": "", "emailTopic": "Write an email to your team lead suggesting a better way to organize project files.", "timeLimit": 15},
    {"emailTopic": "Write an email to your professor informing them that you have completed the assigned task.", "timeLimit": 15},
    {"essayTopic": "", "emailTopic": "Write an email to a college club coordinator requesting permission to organize an event.", "timeLimit": 15},
    {"emailTopic": "Write an email to an HR representative asking about the company's work-from-home policy.", "timeLimit": 15},
    {"essayTopic": "", "emailTopic": "Write an email to your manager requesting approval for attending a professional conference.", "timeLimit": 15},
    {"emailTopic": "Write an email to a customer informing them that their issue has been escalated to the support team.", "timeLimit": 15},
    {"essayTopic": "", "emailTopic": "Write an email to your colleague reminding them about an upcoming deadline.", "timeLimit": 15},
    {"emailTopic": "Write an email to the transport coordinator reporting a problem with the college bus schedule.", "timeLimit": 15},
    {"essayTopic": "", "emailTopic": "Write an email to a recruiter thanking them after completing an interview.", "timeLimit": 15},
    {"emailTopic": "Write an email to your manager requesting clarification about your assigned responsibilities.", "timeLimit": 15},
    {"essayTopic": "", "emailTopic": "Write an email to the finance department asking about the status of a reimbursement.", "timeLimit": 15},
    {"emailTopic": "Write an email to a professor requesting permission to use a particular dataset for your project.", "timeLimit": 15},
    {"essayTopic": "", "emailTopic": "Write an email to a company asking about available entry-level job opportunities.", "timeLimit": 15},
    {"emailTopic": "Write an email to your team informing them about a change in the meeting time.", "timeLimit": 15},
    {"essayTopic": "", "emailTopic": "Write an email to a customer explaining the steps required to return a product.", "timeLimit": 15},
]


# ── Old-format reading passages (from pasted JSON) ────────────────────────
# Format: { paragraph: "...", questions: [{ question, options, correctAnswer }] }

OLD_READING_PASSAGES = [
    {
        "title": "Digital Libraries",
        "paragraph": "Digital libraries allow people to access books, journals, reports, and other resources through computers or mobile devices. They are useful because users can search large collections without travelling to a physical building. Many services also provide tools for saving or organizing material. However, digital access does not automatically make every source reliable, so readers should check the authority and date of information.",
        "questions": [
            {"question": "What is a major benefit of digital libraries?", "options": ["They allow users to search collections without travelling to a physical building.", "They require users to visit a physical building.", "They eliminate the need to check sources.", "They contain only printed books."], "correctAnswer": 0},
            {"question": "What should readers check when using digital resources?", "options": ["The authority and date of the information.", "Only the screen size.", "The color of the website.", "Only the file name."], "correctAnswer": 0},
            {"question": "Which resource can digital libraries contain?", "options": ["Journals.", "Only maps.", "Only newspapers.", "Only audio calls."], "correctAnswer": 0},
            {"question": "What does digital access NOT guarantee?", "options": ["That every source is reliable.", "That users can search collections.", "That resources can be accessed digitally.", "That users can save some material."], "correctAnswer": 0},
            {"question": "What is the passage mainly about?", "options": ["The benefits and limitations of digital libraries.", "The history of printed books.", "How to build a physical library.", "How to repair computers."], "correctAnswer": 0},
        ],
    },
    {
        "title": "Urban Farming",
        "paragraph": "Urban farming involves growing food in city spaces such as rooftops, balconies, vacant plots, and community gardens. It can bring food production closer to consumers and give residents practical experience with plants. However, urban farms usually face limits involving land, water, soil quality, and local rules. Their value is therefore often educational and community-based as well as productive.",
        "questions": [
            {"question": "Where can urban farming take place?", "options": ["On rooftops, balconies, vacant plots, and community gardens.", "Only in rural fields.", "Only inside supermarkets.", "Only in forests."], "correctAnswer": 0},
            {"question": "What is one benefit of urban farming?", "options": ["It can bring food production closer to consumers.", "It removes all water requirements.", "It guarantees large-scale production.", "It eliminates local regulations."], "correctAnswer": 0},
            {"question": "Which is a limitation mentioned in the passage?", "options": ["Available land.", "Number of computers.", "Internet speed.", "Museum space."], "correctAnswer": 0},
            {"question": "Why can urban farming be educational?", "options": ["It gives residents practical experience with plants.", "It teaches people to operate traffic signals.", "It replaces schools.", "It requires no practical work."], "correctAnswer": 0},
            {"question": "What does the passage suggest about urban farms?", "options": ["Their value can be both productive and community-based.", "They are always large commercial farms.", "They can operate without resources.", "They are useful only outside cities."], "correctAnswer": 0},
        ],
    },
    {
        "title": "Public Speaking",
        "paragraph": "Public speaking is easier when a speaker understands the audience and organizes ideas before presenting. Practice can improve confidence and help a speaker notice unclear explanations. Good speakers also listen to questions and adjust their explanations when necessary. Preparation is important, but flexibility matters because an audience may respond differently from what the speaker expected.",
        "questions": [
            {"question": "What can improve public speaking confidence?", "options": ["Practice.", "Avoiding all questions.", "Ignoring the audience.", "Reading without preparation."], "correctAnswer": 0},
            {"question": "Why should a speaker understand the audience?", "options": ["To organize ideas appropriately for them.", "To avoid preparing.", "To eliminate all questions.", "To make the presentation longer."], "correctAnswer": 0},
            {"question": "What should a good speaker do when questions arise?", "options": ["Listen and adjust explanations when necessary.", "Ignore the questions.", "End the presentation immediately.", "Repeat the same sentence."], "correctAnswer": 0},
            {"question": "What is the main contrast in the passage?", "options": ["Preparation is important, but flexibility is also necessary.", "Speaking is impossible without technology.", "Questions should always be avoided.", "Preparation is unnecessary."], "correctAnswer": 0},
            {"question": "Which statement is supported?", "options": ["An audience may respond differently from what a speaker expects.", "Every audience responds identically.", "Practice makes questions unnecessary.", "Speakers should never change explanations."], "correctAnswer": 0},
        ],
    },
    {
        "title": "Electronic Recycling",
        "paragraph": "Old electronic devices contain materials that can sometimes be recovered and reused. They may also contain components that should not be placed in ordinary household waste. Specialized collection and processing can separate useful materials and reduce unsafe disposal. People can contribute by taking unwanted devices to appropriate collection points instead of simply throwing them away.",
        "questions": [
            {"question": "What is the main idea of the passage?", "options": ["Electronic devices contain recoverable materials and should be properly recycled.", "Electronics are harmful and should never be used.", "All electronics can be reused without processing.", "People should throw electronics in regular bins."], "correctAnswer": 0},
            {"question": "Why should e-waste not go in regular bins?", "options": ["It contains components unsuitable for household waste.", "It is too heavy for bins.", "Bins are too small.", "It smells bad."], "correctAnswer": 0},
            {"question": "What can specialized processing do?", "options": ["Separate useful materials and reduce unsafe disposal.", "Create new devices.", "Increase pollution.", "Make electronics cheaper."], "correctAnswer": 0},
            {"question": "How can people contribute?", "options": ["Take devices to appropriate collection points.", "Throw them anywhere.", "Burn them.", "Bury them."], "correctAnswer": 0},
            {"question": "What do electronic devices contain?", "options": ["Materials that can be recovered and reused.", "Only plastic.", "Only glass.", "Nothing useful."], "correctAnswer": 0},
        ],
    },
    {
        "title": "Morning Routines",
        "paragraph": "A simple morning routine can help people begin the day in an organized way. Planning priorities, preparing necessary items, and allowing enough time for breakfast can reduce avoidable decisions later. A useful routine does not have to contain many activities. Its main benefit comes from being realistic enough to follow consistently.",
        "questions": [
            {"question": "What does a morning routine help with?", "options": ["Beginning the day in an organized way.", "Avoiding breakfast.", "Sleeping more.", "Skipping priorities."], "correctAnswer": 0},
            {"question": "What can reduce avoidable decisions later?", "options": ["Planning priorities and preparing necessary items.", "Skipping breakfast.", "Waking up late.", "Ignoring tasks."], "correctAnswer": 0},
            {"question": "Does a routine need many activities?", "options": ["No, it does not have to contain many activities.", "Yes, it must have at least 10.", "Only on weekends.", "Only if you are a manager."], "correctAnswer": 0},
            {"question": "What makes a routine useful?", "options": ["Being realistic enough to follow consistently.", "Being extremely complicated.", "Changing every day.", "Including as many tasks as possible."], "correctAnswer": 0},
            {"question": "What is the main benefit of a morning routine?", "options": ["Being realistic and consistent.", "Being long and complex.", "Including every possible task.", "Starting as late as possible."], "correctAnswer": 0},
        ],
    },
    {
        "title": "Community Volunteering",
        "paragraph": "Community volunteering allows people to contribute their time and skills to local causes. Volunteers may help with education, environmental projects, public events, or support services. The community benefits from the work, while volunteers can develop communication, teamwork, and organizational skills. Successful programs usually give volunteers clear responsibilities and suitable guidance.",
        "questions": [
            {"question": "What does volunteering allow people to do?", "options": ["Contribute time and skills to local causes.", "Earn a salary.", "Avoid all responsibilities.", "Travel internationally."], "correctAnswer": 0},
            {"question": "What can volunteers develop?", "options": ["Communication, teamwork, and organizational skills.", "Only physical strength.", "Only technical skills.", "Nothing."], "correctAnswer": 0},
            {"question": "What makes a volunteer program successful?", "options": ["Clear responsibilities and suitable guidance.", "No supervision at all.", "Unlimited time commitment.", "Working alone."], "correctAnswer": 0},
            {"question": "What areas can volunteers help with?", "options": ["Education, environment, events, and support services.", "Only education.", "Only environmental projects.", "Only public events."], "correctAnswer": 0},
            {"question": "Who benefits from volunteering?", "options": ["Both the community and the volunteers.", "Only the community.", "Only the volunteers.", "Nobody."], "correctAnswer": 0},
        ],
    },
    {
        "title": "Digital Maps",
        "paragraph": "Digital maps provide directions, location information, and sometimes traffic updates. They are particularly useful when people travel through unfamiliar places. Their accuracy depends on the quality and freshness of the underlying data, so users should not rely on them blindly. Physical signs and local conditions remain important when information on a map appears outdated.",
        "questions": [
            {"question": "What do digital maps provide?", "options": ["Directions, location information, and sometimes traffic updates.", "Only directions.", "Only traffic.", "Only weather."], "correctAnswer": 0},
            {"question": "When are digital maps most useful?", "options": ["When traveling through unfamiliar places.", "At home only.", "When the phone is off.", "In emergencies only."], "correctAnswer": 0},
            {"question": "What affects accuracy?", "options": ["Quality and freshness of underlying data.", "Phone color.", "Time of day.", "User's name."], "correctAnswer": 0},
            {"question": "Should users rely on maps blindly?", "options": ["No.", "Yes, always.", "Only at night.", "Only on weekends."], "correctAnswer": 0},
            {"question": "What remains important when maps seem outdated?", "options": ["Physical signs and local conditions.", "Nothing.", "Only phone GPS.", "Only apps."], "correctAnswer": 0},
        ],
    },
    {
        "title": "Workplace Mentoring",
        "paragraph": "Workplace mentoring connects a less experienced employee with someone who can provide guidance. A good mentor does more than give instructions; they encourage questions and help the learner develop independent problem-solving skills. Regular conversations can make it easier to discuss progress and difficulties. The ultimate aim is for the learner to become increasingly confident without depending on the mentor for every decision.",
        "questions": [
            {"question": "What does mentoring connect?", "options": ["A less experienced employee with a guide.", "Two managers.", "A student and a teacher.", "No one."], "correctAnswer": 0},
            {"question": "What does a good mentor do?", "options": ["Encourages questions and develops independent skills.", "Only gives orders.", "Avoids all contact.", "Ignores the learner."], "correctAnswer": 0},
            {"question": "What is the ultimate aim?", "options": ["The learner becomes confident without constant dependence.", "The learner never works alone.", "The mentor takes over all tasks.", "The learner forgets everything."], "correctAnswer": 0},
            {"question": "Why are regular conversations useful?", "options": ["They make it easier to discuss progress and difficulties.", "They waste time.", "They are unnecessary.", "They cause arguments."], "correctAnswer": 0},
            {"question": "What skill does mentoring develop?", "options": ["Independent problem-solving.", "Only memory.", "Only obedience.", "Only following instructions."], "correctAnswer": 0},
        ],
    },
    {
        "title": "Food Labels",
        "paragraph": "Food labels can help consumers compare products by providing information about ingredients, serving sizes, nutrients, and dates. A package may contain several servings even when it appears small. Therefore, consumers should consider the serving size before comparing nutritional values. Reading the ingredient list can also help people identify substances they may want to avoid.",
        "questions": [
            {"question": "What do food labels help with?", "options": ["Comparing products through ingredients and nutritional info.", "Only taste.", "Only price.", "Only color."], "correctAnswer": 0},
            {"question": "Why consider serving size?", "options": ["A package may contain several servings.", "To waste food.", "To eat more.", "Because labels require it."], "correctAnswer": 0},
            {"question": "What can ingredient lists help identify?", "options": ["Substances people may want to avoid.", "Only healthy items.", "Only chemicals.", "Nothing useful."], "correctAnswer": 0},
            {"question": "What information do labels provide?", "options": ["Ingredients, serving sizes, nutrients, and dates.", "Only ingredients.", "Only dates.", "Only nutrients."], "correctAnswer": 0},
            {"question": "Why might a small package have several servings?", "options": ["The package appearance is misleading about portion size.", "It is always oversized.", "Labels are wrong.", "People eat too little."], "correctAnswer": 0},
        ],
    },
    {
        "title": "Rainwater Harvesting",
        "paragraph": "Rainwater harvesting collects rainfall and stores it for later use. Depending on local regulations and treatment requirements, collected water may be suitable for gardening, cleaning, or other non-drinking purposes. Such systems can reduce demand for treated water when rainfall is sufficient. Their usefulness depends on storage capacity, local weather, and appropriate maintenance.",
        "questions": [
            {"question": "What does rainwater harvesting do?", "options": ["Collects and stores rainfall for later use.", "Creates rain.", "Removes water.", "Heats water."], "correctAnswer": 0},
            {"question": "What can collected water be used for?", "options": ["Gardening, cleaning, and other non-drinking purposes.", "Only drinking.", "Only cooking.", "Only industrial use."], "correctAnswer": 0},
            {"question": "What affects usefulness?", "options": ["Storage capacity, local weather, and maintenance.", "Only weather.", "Only storage.", "Nothing."], "correctAnswer": 0},
            {"question": "Can harvesting reduce treated water demand?", "options": ["Yes, when rainfall is sufficient.", "Never.", "Only in deserts.", "Only in winter."], "correctAnswer": 0},
            {"question": "What is required for collected water?", "options": ["Appropriate treatment and local regulations compliance.", "No treatment at all.", "Only filtering.", "Only boiling."], "correctAnswer": 0},
        ],
    },
    {
        "title": "Online Meetings",
        "paragraph": "Online meetings allow people in different locations to communicate without travelling. They can save time, but technical problems, background noise, and unclear agendas may reduce their effectiveness. Sending an agenda before a meeting gives participants time to prepare. Testing microphones and cameras beforehand can also prevent avoidable interruptions.",
        "questions": [
            {"question": "What do online meetings allow?", "options": ["Communication without travelling.", "Only in-person meetings.", "Only phone calls.", "No communication."], "correctAnswer": 0},
            {"question": "What can reduce effectiveness?", "options": ["Technical problems, background noise, and unclear agendas.", "Only technical problems.", "Only noise.", "Nothing."], "correctAnswer": 0},
            {"question": "Why send an agenda beforehand?", "options": ["To give participants time to prepare.", "To confuse them.", "To delay the meeting.", "It is not useful."], "correctAnswer": 0},
            {"question": "What prevents avoidable interruptions?", "options": ["Testing microphones and cameras beforehand.", "Ignoring technical issues.", "Starting without preparation.", "Using old equipment."], "correctAnswer": 0},
            {"question": "Can online meetings save time?", "options": ["Yes.", "Never.", "Only on Fridays.", "Only for managers."], "correctAnswer": 0},
        ],
    },
    {
        "title": "Museums and Learning",
        "paragraph": "Museums support learning by allowing visitors to examine objects, artworks, and exhibits directly. Many museums also provide guided tours, workshops, and interactive displays. These activities can connect abstract information with physical examples. As a result, museums can complement classroom learning rather than simply serving as places where objects are displayed.",
        "questions": [
            {"question": "How do museums support learning?", "options": ["By allowing direct examination of objects and exhibits.", "Only by displaying objects.", "Only through books.", "Only online."], "correctAnswer": 0},
            {"question": "What additional activities do museums offer?", "options": ["Guided tours, workshops, and interactive displays.", "Only tours.", "Only workshops.", "Nothing else."], "correctAnswer": 0},
            {"question": "What can these activities connect?", "options": ["Abstract information with physical examples.", "Nothing.", "Only numbers.", "Only colors."], "correctAnswer": 0},
            {"question": "How do museums relate to classroom learning?", "options": ["They complement it rather than replace it.", "They replace it entirely.", "They are unrelated.", "They compete with it."], "correctAnswer": 0},
            {"question": "What is the main role of museums?", "options": ["Supporting learning through direct experience.", "Only storing old objects.", "Only making money.", "Only entertaining children."], "correctAnswer": 0},
        ],
    },
    {
        "title": "Bicycle Commuting",
        "paragraph": "Cycling to work or college can provide physical activity while reducing dependence on motor vehicles. Its practicality depends on distance, weather, road safety, and facilities such as bicycle parking. Dedicated cycling lanes can make journeys safer. People are more likely to choose cycling when the route is convenient as well as safe.",
        "questions": [
            {"question": "What benefit does cycling provide?", "options": ["Physical activity while reducing vehicle dependence.", "Only speed.", "Only comfort.", "Nothing."], "correctAnswer": 0},
            {"question": "What affects practicality?", "options": ["Distance, weather, road safety, and parking facilities.", "Only distance.", "Only weather.", "Nothing."], "correctAnswer": 0},
            {"question": "What makes journeys safer?", "options": ["Dedicated cycling lanes.", "Faster cars.", "Wider roads.", "More traffic."], "correctAnswer": 0},
            {"question": "When are people more likely to cycle?", "options": ["When the route is convenient and safe.", "Never.", "Only in rain.", "Only at night."], "correctAnswer": 0},
            {"question": "What does cycling help reduce?", "options": ["Dependence on motor vehicles.", "Physical activity.", "Air quality.", "Safety."], "correctAnswer": 0},
        ],
    },
    {
        "title": "Cloud Storage",
        "paragraph": "Cloud storage keeps files on remote servers and allows users to access them through the internet. Shared folders can make collaboration easier because several people can work with common documents. However, cloud storage is not a complete substitute for good security and backup practices. Users should protect accounts and understand how their provider handles stored data.",
        "questions": [
            {"question": "What does cloud storage do?", "options": ["Keeps files on remote servers for internet access.", "Only stores locally.", "Only prints documents.", "Only sends emails."], "correctAnswer": 0},
            {"question": "How does cloud storage help collaboration?", "options": ["Shared folders let several people work with common documents.", "It prevents sharing.", "It only allows one user.", "It creates paper copies."], "correctAnswer": 0},
            {"question": "Is cloud storage a complete security solution?", "options": ["No, it is not a complete substitute.", "Yes, always.", "Only for businesses.", "Only for individuals."], "correctAnswer": 0},
            {"question": "What should users do?", "options": ["Protect accounts and understand data handling.", "Ignore security.", "Share passwords.", "Use only one device."], "correctAnswer": 0},
            {"question": "What is the main subject?", "options": ["Benefits and limitations of cloud storage.", "Only benefits.", "Only limitations.", "Unrelated topic."], "correctAnswer": 0},
        ],
    },
    {
        "title": "Study Groups",
        "paragraph": "Study groups can help learners understand difficult concepts by encouraging them to explain ideas to one another. Explaining a topic often reveals gaps in understanding that may not be noticed during silent reading. Groups are most useful when participants prepare beforehand and keep discussions focused. Without preparation, meetings can become social gatherings rather than study sessions.",
        "questions": [
            {"question": "How do study groups help?", "options": ["By encouraging explanation of ideas to one another.", "By avoiding work.", "By being social only.", "By copying answers."], "correctAnswer": 0},
            {"question": "What does explaining reveal?", "options": ["Gaps in understanding.", "Only strengths.", "Nothing.", "Only errors in others."], "correctAnswer": 0},
            {"question": "When are groups most useful?", "options": ["When participants prepare beforehand and stay focused.", "Always.", "Never.", "Only without preparation."], "correctAnswer": 0},
            {"question": "What happens without preparation?", "options": ["Meetings become social gatherings.", "They become more productive.", "Nothing changes.", "They end earlier."], "correctAnswer": 0},
            {"question": "What is the main benefit?", "options": ["Understanding difficult concepts through explanation.", "Making friends.", "Avoiding study.", "Completing homework."], "correctAnswer": 0},
        ],
    },
    {
        "title": "Noise Pollution",
        "paragraph": "Noise pollution can come from traffic, construction, industrial activity, and other sources. Continuous unwanted sound may interfere with concentration and comfort. Cities can reduce unnecessary noise through planning, quieter equipment, suitable restrictions, and better infrastructure. The most effective approach often combines several measures rather than relying on a single solution.",
        "questions": [
            {"question": "What causes noise pollution?", "options": ["Traffic, construction, industrial activity, and other sources.", "Only traffic.", "Only construction.", "Only nature."], "correctAnswer": 0},
            {"question": "What can noise interfere with?", "options": ["Concentration and comfort.", "Only sleep.", "Only work.", "Nothing."], "correctAnswer": 0},
            {"question": "How can cities reduce noise?", "options": ["Planning, quieter equipment, restrictions, and better infrastructure.", "By ignoring it.", "By building more roads.", "By increasing traffic."], "correctAnswer": 0},
            {"question": "What is the most effective approach?", "options": ["Combining several measures.", "Using only one solution.", "Doing nothing.", "Ignoring the problem."], "correctAnswer": 0},
            {"question": "What is the main subject?", "options": ["Causes and solutions for noise pollution.", "Only causes.", "Only solutions.", "Unrelated topic."], "correctAnswer": 0},
        ],
    },
    {
        "title": "Renewable Energy",
        "paragraph": "Renewable energy sources such as solar and wind depend on resources that are naturally replenished. Their availability can change with weather and location, which means energy systems may need storage or other sources to maintain reliability. Investment in transmission and storage can make it easier to use renewable energy on a larger scale.",
        "questions": [
            {"question": "What do renewable sources depend on?", "options": ["Naturally replenished resources.", "Fossil fuels.", "Nuclear power.", "Only sunlight."], "correctAnswer": 0},
            {"question": "What affects availability?", "options": ["Weather and location.", "Only time of day.", "Only location.", "Nothing."], "correctAnswer": 0},
            {"question": "What may energy systems need?", "options": ["Storage or other sources for reliability.", "Nothing extra.", "Only more panels.", "Only more wind turbines."], "correctAnswer": 0},
            {"question": "What can help use renewables at larger scale?", "options": ["Investment in transmission and storage.", "Less investment.", "Only research.", "Nothing."], "correctAnswer": 0},
            {"question": "What is the main subject?", "options": ["Characteristics and challenges of renewable energy.", "Only solar power.", "Only wind power.", "Unrelated topic."], "correctAnswer": 0},
        ],
    },
    {
        "title": "Modern Libraries",
        "paragraph": "Modern libraries often provide much more than physical books. Members may have access to digital databases, study spaces, workshops, computers, and community events. The exact services vary between libraries. New members should therefore learn about the facilities available locally instead of assuming that every library offers the same resources.",
        "questions": [
            {"question": "What do modern libraries provide?", "options": ["More than just physical books.", "Only books.", "Only computers.", "Nothing else."], "correctAnswer": 0},
            {"question": "What services might members access?", "options": ["Digital databases, study spaces, workshops, computers, and events.", "Only books.", "Only study spaces.", "Only computers."], "correctAnswer": 0},
            {"question": "Do all libraries offer the same services?", "options": ["No, services vary between libraries.", "Yes, always.", "Only in cities.", "Only in universities."], "correctAnswer": 0},
            {"question": "What should new members do?", "options": ["Learn about locally available facilities.", "Assume all libraries are the same.", "Only borrow books.", "Nothing."], "correctAnswer": 0},
            {"question": "What is the main point?", "options": ["Modern libraries offer diverse services beyond books.", "Libraries are outdated.", "Books are the only resource.", "Libraries are closing."], "correctAnswer": 0},
        ],
    },
    {
        "title": "Healthy Workspaces",
        "paragraph": "A comfortable workspace can support concentration and productivity. Suitable lighting, seating, screen placement, and organized equipment can reduce unnecessary distractions and discomfort. Taking regular breaks is also important because remaining in one position for a long time may reduce attention. Good workspace design combines the physical environment with sensible work habits.",
        "questions": [
            {"question": "What can a comfortable workspace support?", "options": ["Concentration and productivity.", "Only comfort.", "Only productivity.", "Nothing."], "correctAnswer": 0},
            {"question": "What reduces distractions?", "options": ["Suitable lighting, seating, screen placement, and organized equipment.", "Only lighting.", "Only seating.", "Nothing."], "correctAnswer": 0},
            {"question": "Why take regular breaks?", "options": ["Staying in one position too long reduces attention.", "To waste time.", "To avoid work.", "Breaks are not important."], "correctAnswer": 0},
            {"question": "What does good workspace design combine?", "options": ["Physical environment with sensible work habits.", "Only furniture.", "Only technology.", "Nothing."], "correctAnswer": 0},
            {"question": "What is the main subject?", "options": ["Creating effective and comfortable workspaces.", "Only furniture.", "Only technology.", "Unrelated topic."], "correctAnswer": 0},
        ],
    },
]


async def content_hash(text: str) -> str:
    """Short hash for deduplication."""
    return hashlib.md5(text.strip().lower().encode()).hexdigest()[:12]


async def migrate():
    """Convert old-format data to new schema and seed it."""
    client = AsyncIOMotorClient(settings.mongo_uri, uuidRepresentation="standard")
    await init_beanie(database=client[settings.control_db_name], document_models=MODELS)

    print("=" * 60)
    print("  MIGRATION SEEDER — Old Format → New Schema")
    print("=" * 60)

    # ── 1. Writing prompts ─────────────────────────────────────────────
    print("\n📝 Migrating writing prompts...")
    writing_count = 0
    writing_skipped = 0

    # Check existing prompts for dedup
    existing_prompts = await WritingPrompt.find().to_list()
    existing_hashes = set()
    for p in existing_prompts:
        h = await content_hash(p.prompt)
        existing_hashes.add(h)

    # Essay prompts
    for item in OLD_WRITING_PROMPTS:
        topic = (item.get("essayTopic") or "").strip()
        if not topic:
            continue
        h = await content_hash(topic)
        if h in existing_hashes:
            writing_skipped += 1
            continue
        wp = WritingPrompt(
            title=topic[:100],
            kind="essay",
            prompt=topic,
            company="",
            scenario="",
            key_points=["Clear thesis", "Supporting arguments", "Grammar and vocabulary", "Coherent structure"],
            min_words=200,
            suggested_minutes=item.get("timeLimit", 30),
        )
        await wp.insert()
        existing_hashes.add(h)
        writing_count += 1

    # Email prompts
    for item in OLD_WRITING_EMAILS:
        topic = (item.get("emailTopic") or "").strip()
        if not topic:
            continue
        h = await content_hash(topic)
        if h in existing_hashes:
            writing_skipped += 1
            continue
        wp = WritingPrompt(
            title=topic[:100],
            kind="email",
            prompt=topic,
            company="",
            scenario="",
            key_points=["Professional tone", "Clear purpose", "Proper format", "Concise language"],
            min_words=80,
            suggested_minutes=item.get("timeLimit", 15),
        )
        await wp.insert()
        existing_hashes.add(h)
        writing_count += 1

    print(f"   ✅ Created: {writing_count} | ⏭️  Skipped (duplicates): {writing_skipped}")

    # ── 2. Reading passages + QuizItem questions ───────────────────────
    print("\n📖 Migrating reading passages and questions...")
    passage_count = 0
    question_count = 0
    passage_skipped = 0

    existing_passages = await ReadingPassage.find().to_list()
    existing_passage_hashes = set()
    for p in existing_passages:
        h = await content_hash(p.body)
        existing_passage_hashes.add(h)

    existing_quiz = await QuizItem.find(
        QuizItem.category == "reading_comprehension"
    ).to_list()
    existing_quiz_hashes = set()
    for q in existing_quiz:
        h = await content_hash(q.stem)
        existing_quiz_hashes.add(h)

    for passage_data in OLD_READING_PASSAGES:
        title = passage_data["title"]
        body = passage_data["paragraph"]
        questions = passage_data["questions"]

        h = await content_hash(body)
        if h in existing_passage_hashes:
            passage_skipped += 1
            continue

        word_count = len(body.split())

        # Create reading passage
        rp = ReadingPassage(
            title=title,
            kind="article",
            body=body,
            company="",
            word_count=word_count,
            difficulty=0.3,
        )
        await rp.insert()
        existing_passage_hashes.add(h)
        passage_count += 1

        # Create QuizItem records for each question
        for q in questions:
            qh = await content_hash(q["question"])
            if qh in existing_quiz_hashes:
                continue

            qi = QuizItem(
                category="reading_comprehension",
                stem=q["question"],
                options=q["options"],
                correct_index=q["correctAnswer"],
                explanation="",
                company="",
                passage_id=rp.id,
                difficulty=0.3,
            )
            await qi.insert()
            existing_quiz_hashes.add(qh)
            question_count += 1

    print(f"   ✅ Passages created: {passage_count} | Skipped: {passage_skipped}")
    print(f"   ✅ Questions created: {question_count}")

    # ── 3. Summary ────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  MIGRATION SUMMARY")
    print("=" * 60)

    total_writing = await WritingPrompt.find().count()
    total_passages = await ReadingPassage.find().count()
    total_reading_q = await QuizItem.find(
        QuizItem.category == "reading_comprehension"
    ).count()
    total_quiz = await QuizItem.find(
        QuizItem.category == "grammar"
    ).count()
    total_vocab = await QuizItem.find(
        QuizItem.category == "vocabulary"
    ).count()
    total_listening = await QuizItem.find(
        QuizItem.category == "audio_comprehension"
    ).count()

    print(f"  Writing prompts:      {total_writing}")
    print(f"  Reading passages:     {total_passages}")
    print(f"  Reading questions:    {total_reading_q}")
    print(f"  Grammar questions:    {total_quiz}")
    print(f"  Vocabulary questions: {total_vocab}")
    print(f"  Listening questions:  {total_listening}")
    print(f"\n  Total items in DB:    {total_writing + total_passages + total_reading_q + total_quiz + total_vocab + total_listening}")
    print("=" * 60)

    # ── 4. Verify company separation ──────────────────────────────────
    print("\n🔍 Verifying company/general separation...")
    general_writing = await WritingPrompt.find(WritingPrompt.company == "").count()
    company_writing = await WritingPrompt.find(WritingPrompt.company != "").count()
    general_reading = await ReadingPassage.find(ReadingPassage.company == "").count()
    company_reading = await ReadingPassage.find(ReadingPassage.company != "").count()

    print(f"  Writing — General: {general_writing} | Company: {company_writing}")
    print(f"  Reading — General: {general_reading} | Company: {company_reading}")

    if company_writing > 0 or company_reading > 0:
        print("\n  Company breakdown:")
        for company in ["Accenture", "TCS", "Cognizant", "Wipro", "Infosys", "HCL", "Tech Mahindra", "Capgemini"]:
            cw = await WritingPrompt.find(WritingPrompt.company == company).count()
            cr = await ReadingPassage.find(ReadingPassage.company == company).count()
            cq = await QuizItem.find(QuizItem.company == company).count()
            if cw + cr + cq > 0:
                print(f"    {company}: Writing={cw}, Reading={cr}, Quiz={cq}")

    print("\n✅ Migration complete!")
    client.close()


if __name__ == "__main__":
    asyncio.run(migrate())
