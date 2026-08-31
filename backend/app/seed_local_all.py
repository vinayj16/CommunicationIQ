"""
MASTER SEEDER v2 — creates ALL question types with proper linking.

Key insight: Reading and listening questions are stored as QuizItem records
with category="reading_comprehension" or "audio_comprehension" and a
passage_id linking them to the passage document.

Run:
    cd backend
    python -m app.seed_local_all
"""
from __future__ import annotations
import asyncio
import uuid
import random
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from beanie import Document
from pydantic import Field

def uid() -> str:
    return str(uuid.uuid4())

# ── Inline models ─────────────────────────────────────────────────────────
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

class ListeningPassage(Document):
    id: str = Field(default_factory=uid, alias="_id")
    tenant_id: str = ""
    title: str
    kind: str = "short_talk"
    transcript: str
    company: str = ""
    audio_key: str = ""
    accent: str = "indian"
    plays_allowed: int = 1
    approx_seconds: int = 45
    difficulty: float = 0.0
    status: str = "published"
    class Settings:
        name = "listening_passages"

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

class TaskItem(Document):
    id: str = Field(default_factory=uid, alias="_id")
    tenant_id: str = ""
    task_type: str = ""
    prompt_text: str = ""
    company: str = ""
    prompt_audio_key: str = ""
    prompt_accent: str = "indian"
    reference_text: str = ""
    rubric: dict = Field(default_factory=dict)
    word_count: int = 0
    difficulty: float = 0.0
    discrimination: float = 1.0
    calibrated: bool = False
    l1_group: str = ""
    skill_tags: list = Field(default_factory=list)
    topic: str = ""
    role: str = ""
    industry: str = ""
    language: str = ""
    source: str = "authored"
    version: int = 1
    status: str = "published"
    class Settings:
        name = "task_items"

MODELS = [QuizItem, ReadingPassage, ListeningPassage, WritingPrompt, TaskItem]
COMPANIES = ["Accenture", "TCS", "Cognizant", "Wipro", "Infosys", "HCL", "Tech Mahindra", "Capgemini"]

# ============================================================================
# QUIZ: 15 grammar + 15 vocabulary (general) + 10 per company
# ============================================================================
GENERAL_GRAMMAR = [
    ("Choose the correct sentence:", ["He don't like coffee.", "He doesn't likes coffee.", "He doesn't like coffee.", "He not like coffee."], 2, "Use 'doesn't' + base verb."),
    ("Which sentence is correct?", ["She have been working here.", "She has been working here.", "She has been work here.", "She have been work here."], 1, "Present perfect continuous."),
    ("Error in: 'The team are working hard to meets the deadline.'", ["are working", "to meets", "the deadline", "No error"], 1, "Use base form 'to meet'."),
    ("'She is interested ___ learning.'", ["in", "on", "at", "for"], 0, "Interested in."),
    ("Passive of 'The manager approved the proposal':", ["Proposal approved manager.", "Proposal was approved by manager.", "Proposal has approved.", "Proposal is approving."], 1, "Object + was + past participle."),
    ("'The company ___ its new office last month.'", ["opened", "opens", "opening", "open"], 0, "Past tense 'opened'."),
    ("Which uses semicolon correctly?", ["I like coffee; and tea.", "I like coffee; however, I don't drink tea.", "I like coffee; tea is nice.", "I like coffee; because it tastes."], 1, "Semicolon connects clauses."),
    ("'Neither the manager ___ the team was available.'", ["or", "nor", "and", "but"], 1, "Neither pairs with nor."),
    ("Comparative of 'good':", ["gooder", "more good", "better", "best"], 2, "Irregular comparative."),
    ("Correct sentence:", ["Everyone have their opinion.", "Everyone has their opinion.", "Everyone are having.", "Everyone having their."], 1, "Everyone is singular."),
    ("'The information ___ very useful.'", ["are", "is", "were", "have been"], 1, "Information is uncountable."),
    ("Tag question: 'She is a doctor, ___?'", ["is she", "isn't she", "doesn't she", "does she"], 1, "Positive → negative tag."),
    ("'She enjoys ___ books.'", ["read", "reading", "to read", "reads"], 1, "Enjoy + gerund."),
    ("'I wish I ___ fly.'", ["can", "could", "will", "may"], 1, "Wish + past tense."),
    ("'She suggested that he ___ early.'", ["comes", "come", "came", "coming"], 1, "Subjunctive: base form."),
]

GENERAL_VOCABULARY = [
    ("What does 'ubiquitous' mean?", ["Rare", "Found everywhere", "Expensive", "Old"], 1, "Present everywhere."),
    ("Synonym for 'mandatory':", ["Optional", "Required", "Suggested", "Voluntary"], 1, "Required."),
    ("What does 'ROI' stand for?", ["Rate of Interest", "Return on Investment", "Range of Income", "Risk of Inflation"], 1, "Return on Investment."),
    ("What is a 'stakeholder'?", ["Holds a stick", "Someone with interest", "Shareholder only", "Manager"], 1, "Anyone with interest."),
    ("'The team needs to ___ the deadline.'", ["meet", "do", "make", "take"], 0, "Meet the deadline."),
    ("What does 'leverage' mean?", ["Lose something", "Use to max advantage", "Borrow money", "Avoid responsibility"], 1, "Use to max advantage."),
    ("Antonym of 'transparent':", ["Clear", "Opaque", "Visible", "Bright"], 1, "Opaque."),
    ("What is 'procurement'?", ["Selling", "Buying goods/services", "Manufacturing", "Storing"], 1, "Acquiring goods."),
    ("'The project was completed ___ schedule.'", ["in", "on", "at", "by"], 1, "On schedule."),
    ("What does 'endeavor' mean?", ["Give up", "Try or attempt", "Rest", "Ignore"], 1, "Try or attempt."),
    ("Synonym for 'commence':", ["End", "Begin", "Pause", "Continue"], 1, "Begin."),
    ("What does 'mitigate' mean?", ["Aggravate", "Make less severe", "Accelerate", "Accentuate"], 1, "Make less severe."),
    ("Antonym of 'ephemeral':", ["Temporary", "Permanent", "Brief", "Fleeting"], 1, "Permanent."),
    ("What does 'resilient' mean?", ["Fragile", "Recover quickly", "Weak", "Stiff"], 1, "Recover quickly."),
    ("Synonym for 'diligent':", ["Lazy", "Hardworking", "Careless", "Slow"], 1, "Hardworking."),
]

COMPANY_QUIZ = {
    "Accenture": [
        ("Accenture HQ:", ["New York", "Dublin, Ireland", "London", "Bangalore"], 1, "Dublin."),
        ("Originally:", ["IBM", "Andersen Consulting", "Deloitte", "KPMG"], 1, "Andersen Consulting."),
        ("Ticker:", ["ACN", "ACC", "ACNT", "ASC"], 0, "NYSE: ACN."),
        ("Countries:", ["50", "100", "120+", "200"], 2, "120+."),
        ("Services:", ["Only IT", "Strategy, Consulting, Digital, Tech, Ops", "Only mgmt", "Only outsource"], 1, "Full range."),
        ("Renamed:", ["1995", "2000", "2001", "2005"], 2, "2001."),
        ("Hiring:", ["Only interview", "Online test, interviews, HR", "Only aptitude", "GD only"], 1, "Complete."),
        ("Employees:", ["200K", "400K", "600K+", "800K"], 2, "600K+."),
        ("Innovation:", ["Hub", "Innovation Architecture", "Tech Lab", "Digital Factory"], 1, "Architecture."),
        ("Cloud First:", ["Platform", "Cloud adoption", "Training", "Consulting"], 1, "Adoption."),
    ],
    "TCS": [
        ("TCS:", ["Tata Computer", "Tata Consultancy Services", "Tata Computing", "Tata Comm"], 1, "Consultancy."),
        ("iON:", ["Software", "Cloud platform", "Hardware", "Language"], 1, "Cloud."),
        ("Core value:", ["Speed", "Leading change", "Individual", "Short-term"], 1, "Leading Change."),
        ("Hiring:", ["Only technical", "Aptitude, Technical, HR", "Only HR", "GD only"], 1, "Multiple."),
        ("Founded:", ["1968", "1975", "1985", "1990"], 0, "1968."),
        ("Banking:", ["iON", "BaNCS", "Finacle", "EdgeVerve"], 1, "BaNCS."),
        ("Training:", ["1 month", "2-3 months", "6 months", "1 year"], 1, "2-3 months."),
        ("Countries:", ["20", "46", "60", "80"], 1, "46."),
        ("Employees:", ["400K", "500K", "600K+", "800K"], 2, "600K+."),
        ("Part of:", ["Reliance", "Tata Group", "Adani", "Birla"], 1, "Tata."),
    ],
    "Cognizant": [
        ("HQ:", ["Mumbai", "Teaneck, NJ", "Chennai", "Hyderabad"], 1, "Teaneck."),
        ("Founded:", ["1990", "1994", "2000", "2005"], 1, "1994."),
        ("Focus:", ["Hardware", "IT services & consulting", "Software", "Telecom"], 1, "IT services."),
        ("Originally:", ["TCS", "D&B", "Infosys", "Wipro"], 1, "D&B."),
        ("Countries:", ["20", "35", "50+", "80"], 2, "50+."),
        ("Exchange:", ["NYSE", "NASDAQ", "BSE", "LSE"], 1, "NASDAQ."),
        ("Employees:", ["100K", "200K", "300K+", "500K"], 2, "300K+."),
        ("Services:", ["Only IT", "Digital, Tech, Consulting, Ops", "Only SW", "Only BPO"], 1, "Full range."),
        ("Strategy:", ["Traditional", "Edge Concentration", "Outsourcing", "Hardware"], 1, "Edge."),
        ("Delivery:", ["Waterfall", "Squads and Pods", "Remote", "Fixed"], 1, "Squads/Pods."),
    ],
    "Wipro": [
        ("Founded by:", ["Narayana Murthy", "Azim Premji", "Birla", "Ratan Tata"], 1, "Azim Premji."),
        ("HQ:", ["Mumbai", "Bangalore", "Hyderabad", "Chennai"], 1, "Bangalore."),
        ("Known for:", ["Only IT", "IT, consulting, BPS", "Only mfg", "Only healthcare"], 1, "Multiple."),
        ("Originally:", ["Software", "Vegetable oil", "Computers", "Phones"], 1, "Vegetable oil."),
        ("Tagline:", ["Think Big", "Applying Thought", "Innovation", "Building Future"], 1, "Applying Thought."),
        ("Countries:", ["20", "35", "50", "70"], 1, "35+."),
        ("Revenue:", ["$5B", "$10B", "$20B", "$50B"], 1, "$10B+."),
        ("Competitors:", ["Only TCS", "TCS, Infosys, HCL", "Only Google", "Only MS"], 1, "Multiple."),
        ("Full name:", ["Western India Palm Refined Oils", "Worldwide", "Wipro Products", "Wipro Intl"], 0, "Western India."),
        ("AI:", ["BaNCS", "HOLMES", "Nia", "Cloud First"], 1, "HOLMES."),
    ],
    "Infosys": [
        ("Founded by:", ["Narayana Murthy", "Azim Premji", "Birla", "Ratan Tata"], 0, "Narayana Murthy."),
        ("HQ:", ["Mumbai", "Bangalore", "Hyderabad", "Chennai"], 1, "Bangalore."),
        ("Training:", ["Mysore Campus", "Bangalore Academy", "Hyderabad", "Chennai"], 0, "Mysore."),
        ("AI:", ["iON", "Nia", "Wingspan", "EdgeVerve"], 1, "Nia."),
        ("Incorporated:", ["1975", "1981", "1990", "1995"], 1, "1981."),
        ("NASDAQ:", ["TCS", "Wipro", "Infosys", "HCL"], 2, "Infosys."),
        ("EdgeVerve:", ["Cloud", "Enterprise SW", "Hardware", "Social media"], 1, "Enterprise SW."),
        ("Foundation:", ["Only education", "Education, healthcare, rural", "Only healthcare", "Only tech"], 1, "Multiple."),
        ("Employees:", ["50K", "100K", "250K", "500K"], 2, "250K+."),
        ("Learning:", ["Ultimatix", "Lex", "iLearn", "MyEureka"], 1, "Lex."),
    ],
    "HCL": [
        ("Founded:", ["1970", "1976", "1985", "1990"], 1, "1976."),
        ("HQ:", ["Bangalore", "Noida", "Mumbai", "Chennai"], 1, "Noida."),
        ("Strategy:", ["Mode 1-2-3", "Digital First", "Cloud Ready", "Innovation Hub"], 0, "Mode 1-2-3."),
        ("Countries:", ["30", "40", "52", "65"], 2, "52."),
        ("Employees:", ["150K", "175K", "225K+", "300K"], 2, "225K+."),
        ("Innovation:", ["Hub", "MyEureka", "IdeaStream", "ThinkTank"], 1, "MyEureka."),
        ("Digital Foundation:", ["Only cloud", "Cloud-native", "Only data", "Only security"], 1, "Cloud-native."),
        ("Known for:", ["Hardware", "Employee-first", "Only SW", "Only consulting"], 1, "Employee-first."),
        ("Revenue:", ["$5B", "$8B", "$12B+", "$20B"], 2, "$12B+."),
        ("Core:", ["Only IT", "IT, engineering, R&D", "Only mfg", "Only consulting"], 1, "Multiple."),
    ],
    "Tech Mahindra": [
        ("Founded:", ["1975", "1986", "1995", "2000"], 1, "1986."),
        ("HQ:", ["Mumbai", "Pune", "Noida", "Hyderabad"], 1, "Pune."),
        ("Subsidiary:", ["Tata", "Mahindra Group", "Reliance", "Adani"], 1, "Mahindra."),
        ("Trades:", ["NYSE", "BSE and NSE", "NASDAQ", "LSE"], 1, "BSE/NSE."),
        ("Merged:", ["Wipro", "Satyam", "HCL", "Infosys"], 1, "Satyam."),
        ("Countries:", ["30", "50", "90", "120"], 2, "90."),
        ("Employees:", ["100K", "150K", "200K+", "350K"], 2, "200K+."),
        ("Focus:", ["Only IT", "IT, telecom, digital", "Only consulting", "Only mfg"], 1, "Multiple."),
        ("Revenue:", ["$3B", "$5B", "$7B", "$15B"], 2, "$7B+."),
        ("Platform:", ["Nia", "HOLMES", "TechM AirVil", "iON"], 2, "AirVil."),
    ],
    "Capgemini": [
        ("Founded:", ["1960", "1967", "1975", "1980"], 1, "1967."),
        ("HQ:", ["London", "Paris", "New York", "Berlin"], 1, "Paris."),
        ("Countries:", ["30", "40", "50+", "70"], 2, "50+."),
        ("Employees:", ["200K", "275K", "350K", "500K"], 2, "350K."),
        ("Acquired:", ["Accenture", "Altran", "Deloitte", "McKinsey"], 1, "Altran."),
        ("Strategy:", ["Cloud First", "Connected Platform", "Digital Hub", "Innovation"], 1, "Connected."),
        ("Innovation:", ["Labs", "Invent", "Studio", "Hub"], 1, "Invent."),
        ("Revenue:", ["€10B", "€15B", "€22B", "€30B"], 2, "€22B+."),
        ("Services:", ["Only consulting", "Consulting, tech, digital", "Only tech", "Only outsource"], 1, "Full range."),
        ("Platform integrates:", ["Only cloud", "Cloud, data, AI, security", "Only AI", "Only security"], 1, "Multiple."),
    ],
}

# ============================================================================
# READING: 1 general + 1 per company, with 5 questions each
# ============================================================================
ALL_READING = [
    # (title, body, company, [(stem, options, correct, explanation), ...])
    ("The Benefits of Reading", "Reading improves cognitive function, reduces stress, and increases empathy. Children who read perform better academically. Reading preserves mental function as we age, reducing Alzheimer's risk. It exposes us to new ideas and perspectives.", "", [
        ("What does reading improve?", ["Only memory", "Cognitive function, reduces stress, increases empathy", "Only physical health", "Only social skills"], 1, "Multiple benefits."),
        ("How do children who read perform?", ["Worse", "Better academically", "Same", "Don't perform"], 1, "Better academically."),
        ("What disease might reading reduce?", ["Cancer", "Alzheimer's", "Diabetes", "Heart disease"], 1, "Alzheimer's."),
        ("What does reading expose us to?", ["Only fiction", "New ideas, cultures, perspectives", "Only history", "Only science"], 1, "New perspectives."),
        ("Why is reading important now?", ["Books are cheaper", "Digital distractions", "More libraries", "Required by law"], 1, "Digital distractions."),
    ]),
    ("Accenture Innovation Architecture", "Accenture's Innovation Architecture consists of hubs, labs, and studios worldwide. They invested over $3 billion in acquisitions. Cloud First helps enterprises adopt cloud. Revenue exceeded $64 billion with 738,000 employees in 120+ countries.", "Accenture", [
        ("Investment?", ["$1B", "$2B", "$3B", "$5B"], 2, "$3 billion."),
        ("Cloud First?", ["Platform", "Adoption service", "Training", "Consulting"], 1, "Adoption service."),
        ("Revenue?", ["$40B", "$50B", "$64B+", "$80B"], 2, "$64B+."),
        ("Employees?", ["500K", "600K", "738K", "900K"], 2, "738K."),
        ("Countries?", ["50", "100", "120+", "200"], 2, "120+."),
    ]),
    ("TCS Digital Transformation", "TCS invested $2 billion in R&D. TCS BaNCS serves 500 million customers. TCS iON provides cloud solutions. With 600,000+ employees in 46 countries, TCS is one of the largest IT services companies.", "TCS", [
        ("R&D investment?", ["$1B", "$1.5B", "$2B", "$3B"], 2, "$2 billion."),
        ("BaNCS customers?", ["100M", "300M", "500M", "1B"], 2, "500 million."),
        ("iON is?", ["Software", "Cloud platform", "Hardware", "Consulting"], 1, "Cloud platform."),
        ("Employees?", ["400K", "500K", "600K+", "800K"], 2, "600K+."),
        ("Founded?", ["1968", "1975", "1985", "1990"], 0, "1968."),
    ]),
    ("Cognizant Digital Growth", "Cognizant focuses on digital transformation. Squads and Pods model provides agile teams. Revenue reached $19.4 billion. Core areas include digital engineering, cloud, data and AI, and cybersecurity.", "Cognizant", [
        ("Delivery model?", ["Waterfall", "Squads and Pods", "Remote", "Fixed"], 1, "Squads and Pods."),
        ("Revenue?", ["$10B", "$15B", "$19.4B", "$25B"], 2, "$19.4B."),
        ("Countries?", ["20", "30", "40+", "60"], 2, "40+."),
        ("Employees?", ["200K", "280K", "350K+", "500K"], 2, "350K+."),
        ("Founded?", ["1990", "1994", "2000", "2005"], 1, "1994."),
    ]),
    ("Wipro Digital Strategy", "Wipro transformed from vegetable oil to global IT leader. HOLMES AI platform powers automation. FullStride Cloud Services help migrate to cloud. Revenue approximately $11 billion with 250,000+ employees.", "Wipro", [
        ("Originally?", ["Tech", "Vegetable oil", "Bank", "Hospital"], 1, "Vegetable oil."),
        ("AI platform?", ["BaNCS", "HOLMES", "Nia", "Cloud First"], 1, "HOLMES."),
        ("Revenue?", ["$5B", "$8B", "$11B", "$15B"], 2, "$11B."),
        ("Countries?", ["30", "45", "66", "80"], 2, "66 countries."),
        ("Employees?", ["100K", "150K", "250K+", "350K"], 2, "250K+."),
    ]),
    ("Infosys Innovation", "Infosys leads in technology innovation. Nia AI platform automates processes. 23 innovation hubs worldwide. Lex provides continuous learning. Revenue exceeded $18 billion.", "Infosys", [
        ("AI platform?", ["Cloud", "Nia", "Mobile", "Database"], 1, "Nia."),
        ("Innovation hubs?", ["10", "15", "23", "30"], 2, "23 hubs."),
        ("Revenue?", ["$10B", "$15B", "$18B+", "$25B"], 2, "$18B+."),
        ("Founded?", ["1975", "1981", "1990", "1995"], 1, "1981."),
        ("HQ?", ["Mumbai", "Bangalore", "Hyderabad", "Chennai"], 1, "Bangalore."),
    ]),
    ("HCL Technologies Overview", "HCL is a global IT services company in Noida. Mode 1-2-3 strategy focuses on core services and platforms. Digital Foundation enables cloud-native transformation. Revenue exceeded $12 billion.", "HCL", [
        ("Founded?", ["1970", "1976", "1985", "1990"], 1, "1976."),
        ("Strategy?", ["Mode 1-2-3", "Digital First", "Cloud Ready", "Innovation Hub"], 0, "Mode 1-2-3."),
        ("Revenue?", ["$8B", "$10B", "$12B+", "$15B"], 2, "$12B+."),
        ("Innovation platform?", ["Hub", "MyEureka", "IdeaStream", "ThinkTank"], 1, "MyEureka."),
        ("Employees?", ["150K", "175K", "225K+", "300K"], 2, "225K+."),
    ]),
    ("Tech Mahindra Digital", "Tech Mahindra provides digital transformation. Merged with Satyam in 2015. Focus on 5G, cloud, and AI. Revenue approximately $7 billion with 200,000+ employees.", "Tech Mahindra", [
        ("Merged with?", ["Wipro", "Satyam", "HCL", "Infosys"], 1, "Satyam."),
        ("Revenue?", ["$3B", "$5B", "$7B", "$15B"], 2, "$7B+."),
        ("HQ?", ["Mumbai", "Pune", "Noida", "Hyderabad"], 1, "Pune."),
        ("Focus?", ["Only IT", "IT, telecom, digital", "Only consulting", "Only mfg"], 1, "Multiple."),
        ("Employees?", ["100K", "150K", "200K+", "350K"], 2, "200K+."),
    ]),
    ("Capgemini Excellence", "Capgemini is a global leader in consulting and digital transformation. Connected Platform integrates cloud, data, AI, and cybersecurity. Acquired Altran in 2020. Revenue exceeds €22 billion.", "Capgemini", [
        ("Founded?", ["1960", "1967", "1975", "1980"], 1, "1967."),
        ("Strategy?", ["Cloud First", "Connected Platform", "Digital Hub", "Innovation"], 1, "Connected Platform."),
        ("Acquired?", ["Accenture", "Altran", "Deloitte", "McKinsey"], 1, "Altran."),
        ("Revenue?", ["€15B", "€18B", "€22B+", "€30B"], 2, "€22B+."),
        ("Employees?", ["200K", "275K", "350K", "500K"], 2, "350K."),
    ]),
]

# ============================================================================
# LISTENING: 1 general + 1 per company, with 5 questions each
# ============================================================================
ALL_LISTENING = [
    ("Daily Commute", "A: How was your commute?\nB: Train delayed 20 mins due to signal failure.\nA: I take the bus—slower but reliable.\nB: How long?\nA: 45 mins, runs every 10 mins.\nB: I'll try tomorrow.", "general", [
        ("Why delayed?", ["Weather", "Signal failure", "Accident", "Strike"], 1, "Signal failure."),
        ("Bus duration?", ["30 mins", "45 mins", "60 mins", "20 mins"], 1, "45 mins."),
        ("Bus frequency?", ["5 mins", "10 mins", "20 mins", "30 mins"], 1, "Every 10 mins."),
        ("Suggestion?", ["Taxi", "Share ride", "Walk", "Cycle"], 1, "Share ride."),
        ("Decision?", ["Keep train", "Try bus", "Quit job", "Move"], 1, "Try bus."),
    ]),
    ("Accenture Client Meeting", "Today we present the digital transformation roadmap. Phase 1: cloud migration. Phase 2: AI analytics. Phase 3: digital operations. Investment: $15M over 18 months. ROI: 40%.", "Accenture", [
        ("Phases?", ["2", "3", "4", "5"], 1, "3 phases."),
        ("Phase 1?", ["AI", "Cloud migration", "Digital ops", "Training"], 1, "Cloud migration."),
        ("Investment?", ["$10M", "$15M", "$20M", "$25M"], 1, "$15M."),
        ("ROI?", ["20%", "30%", "40%", "50%"], 2, "40%."),
        ("Timeline?", ["12 months", "18 months", "24 months", "36 months"], 1, "18 months."),
    ]),
    ("TCS Onboarding", "Welcome to TCS! First week: ILP—Initial Learning Program. Technical training, soft skills, team-building. Mentor assigned. Use Ultimatix for HR. Project allocation within 2 weeks.", "TCS", [
        ("First week?", ["Training", "ILP", "Induction", "Orientation"], 1, "ILP."),
        ("HR platform?", ["Workday", "Ultimatix", "SAP", "Oracle"], 1, "Ultimatix."),
        ("Allocation?", ["Immediately", "1 week", "2 weeks", "1 month"], 2, "2 weeks."),
        ("ILP includes?", ["Only technical", "Technical, soft skills, team-building", "Only soft", "Only team"], 1, "All three."),
        ("Who guides?", ["HR", "Mentor", "CEO", "No one"], 1, "Mentor."),
    ]),
    ("Cognizant Standup", "Mike: finished auth module. Sarah: working on dashboard API. Tom: resolved DB issue. Today: Mike starts payment, Sarah completes API, Tom optimizes queries. Sprint ends Friday.", "Cognizant", [
        ("Mike completed?", ["Payment", "Auth module", "Dashboard", "DB"], 1, "Auth module."),
        ("Sarah on?", ["Auth", "Dashboard API", "Payments", "Testing"], 1, "Dashboard API."),
        ("Tom resolved?", ["Payment bug", "Auth error", "DB connection", "API timeout"], 2, "DB connection."),
        ("Mike today?", ["Finish dashboard", "Start payment", "Write tests", "Optimize"], 1, "Start payment."),
        ("Sprint ends?", ["Today", "Tomorrow", "Friday", "Next week"], 2, "Friday."),
    ]),
    ("Wipro Project Discussion", "Focus: migrate legacy to FullStride Cloud. Raj leads data migration. Priya handles APIs. Deadline March 31. Phase 1 live February. Daily sync 10 AM.", "Wipro", [
        ("Platform?", ["AWS", "FullStride Cloud", "Azure", "GCP"], 1, "FullStride."),
        ("Raj's role?", ["API", "Data migration lead", "PM", "Client"], 1, "Data migration."),
        ("Deadline?", ["Jan 31", "Feb 28", "Mar 31", "Apr 30"], 2, "Mar 31."),
        ("Phase 1 live?", ["January", "February", "March", "April"], 1, "February."),
        ("Sync time?", ["9 AM", "10 AM", "11 AM", "2 PM"], 1, "10 AM."),
    ]),
    ("Infosys Campus Tour", "Mysore campus: 337 acres, 15 training buildings, 800 classrooms, 14,000 trainees. Labs, pool, tennis, golf. Food court worldwide cuisines. Schedule on Lex.", "Infosys", [
        ("Size?", ["100 acres", "200 acres", "337 acres", "500 acres"], 2, "337 acres."),
        ("Capacity?", ["5K", "10K", "14K", "20K"], 2, "14K+."),
        ("Schedule on?", ["Email", "Lex", "Intranet", "Notice board"], 1, "Lex."),
        ("Facilities?", ["Only classrooms", "Labs, pool, tennis, golf", "Only labs", "Only sports"], 1, "All."),
        ("App?", ["Google Maps", "Infosys app", "WhatsApp", "LinkedIn"], 1, "Infosys app."),
    ]),
    ("HCL Innovation Session", "200 ideas via MyEureka. Top 3: AI chatbot, predictive maintenance, blockchain. Each team gets $50K. Prototypes in 6 weeks.", "HCL", [
        ("Ideas?", ["100", "150", "200", "300"], 2, "200."),
        ("Platform?", ["Innovation Hub", "MyEureka", "IdeaStream", "ThinkTank"], 1, "MyEureka."),
        ("First idea?", ["AI chatbot", "Predictive maintenance", "Blockchain", "Cloud"], 0, "AI chatbot."),
        ("Funding?", ["$25K", "$50K", "$100K", "$200K"], 1, "$50K."),
        ("Timeline?", ["2 weeks", "4 weeks", "6 weeks", "8 weeks"], 2, "6 weeks."),
    ]),
    ("Tech Mahindra Standup", "Priya: 5G optimization complete. Raj: API integration resolved. Anita: test automation done. Today: Priya starts cloud migration, Raj documents, Anita runs tests. Review Friday.", "Tech Mahindra", [
        ("Priya completed?", ["API", "5G optimization", "Tests", "Cloud"], 1, "5G optimization."),
        ("Raj resolved?", ["DB", "API integration", "Cloud", "Test"], 1, "API integration."),
        ("Priya today?", ["Finish testing", "Cloud migration", "Document", "Meeting"], 1, "Cloud migration."),
        ("Blocker?", ["Budget", "Staging env access", "Team", "Tech debt"], 1, "Staging env."),
        ("Review?", ["Today", "Tomorrow", "Friday", "Next week"], 2, "Friday."),
    ]),
    ("Capgemini Strategy Meeting", "Connected Platform review. Focus: cloud, data, AI, cybersecurity. Acquired 3 digital agencies. Invent launched 15 projects. Consulting revenue up 18%. Hire 5,000 cloud engineers.", "Capgemini", [
        ("Focus?", ["Only cloud", "Cloud, data, AI, security", "Only AI", "Only security"], 1, "All four."),
        ("Agencies?", ["1", "2", "3", "5"], 2, "3 agencies."),
        ("Projects?", ["5", "10", "15", "20"], 2, "15 projects."),
        ("Growth?", ["10%", "15%", "18%", "25%"], 2, "18%."),
        ("Engineers?", ["1K", "3K", "5K", "10K"], 2, "5K."),
    ]),
]

# ============================================================================
# WRITING: 2 general + 2 per company
# ============================================================================
ALL_WRITING = [
    # (title, prompt, company, [key_points])
    ("Email to Manager", "Write a professional email requesting a day off. Include reason, work handover, and colleague cover.", "", ["Professional tone", "Clear request", "Reason", "Handover plan", "Availability"]),
    ("Team Performance Report", "Write a quarterly team performance report with achievements, areas for improvement, and next quarter recommendations.", "", ["Data-driven", "Achievements", "Areas", "Recommendations", "Metrics"]),
    ("Customer Apology Letter", "Write an apology letter for a defective product. Acknowledge, explain resolution, offer compensation.", "", ["Empathy", "Resolution", "Compensation", "Prevention", "Contact"]),
    ("Meeting Agenda", "Prepare a 1-hour project status meeting agenda with time allocations, topics, and outcomes.", "", ["Time allocation", "Topics", "Outcomes", "Priority", "Buffer"]),
    # Accenture
    ("Cloud First Proposal", "Write a proposal for Accenture Cloud First implementation. Business case, technical approach, governance.", "Accenture", ["Business case", "Architecture", "Governance", "Migration", "Success criteria"]),
    ("Innovation Architecture", "Write a presentation on Accenture Innovation Architecture. Offerings, case studies, pricing.", "Accenture", ["Service overview", "Case studies", "Differentiators", "Pricing", "Timeline"]),
    # TCS
    ("BaNCS Implementation", "Write a proposal for TCS BaNCS for a mid-sized bank. Benefits, timeline, cost.", "TCS", ["BaNCS features", "Phases", "Cost breakdown", "ROI", "Risk mitigation"]),
    ("ILP Feedback", "Write feedback on your ILP experience at TCS. Technical training, soft skills, overall.", "TCS", ["Technical skills", "Soft skills", "Mentor feedback", "Suggestions", "Career impact"]),
    # Cognizant
    ("Digital Transformation Report", "Write a report on Cognizant's digital transformation project. Methodology, results.", "Cognizant", ["Squads/Pods", "Outcomes", "Methodology", "Satisfaction", "Lessons"]),
    ("Process Improvement", "Write a process improvement proposal. Current state, target state, roadmap.", "Cognizant", ["Current analysis", "Gap identification", "Target state", "Roadmap", "Improvements"]),
    # Wipro
    ("Cloud Migration Plan", "Write a cloud migration proposal using FullStride Cloud. Phases, timeline, risks.", "Wipro", ["Migration phases", "Timeline", "Risk assessment", "Cost analysis", "Benefits"]),
    ("Weekly Team Update", "Write a weekly status update. Completed tasks, blockers, upcoming deliverables.", "Wipro", ["Tasks completed", "Blockers", "Next week", "Resources", "Timeline"]),
    # Infosys
    ("Nia AI Proposal", "Write a proposal for an AI project using Infosys Nia. Problem, approach, outcomes.", "Infosys", ["Problem definition", "Nia capabilities", "Implementation plan", "Success metrics", "Budget"]),
    ("Finacle Project Report", "Write a quarterly report on Finacle implementation. Progress, challenges, next steps.", "Infosys", ["Project status", "Milestones", "Challenges", "Next quarter", "Client feedback"]),
    # HCL
    ("MyEureka Innovation Proposal", "Write a proposal for an innovation project through MyEureka. Idea, feasibility, impact.", "HCL", ["Idea description", "Feasibility", "Expected impact", "Implementation plan", "Resources"]),
    ("Employee Engagement Report", "Write a report on employee engagement initiatives. Programs, feedback, improvements.", "HCL", ["Current programs", "Feedback", "Engagement metrics", "Improvement areas", "Action items"]),
    # Tech Mahindra
    ("5G Solution Proposal", "Write a proposal for Tech Mahindra's 5G solutions. Approach, timeline, benefits.", "Tech Mahindra", ["5G technology", "Implementation phases", "Expected benefits", "Timeline", "Risk assessment"]),
    ("Digital Transformation Presentation", "Write a presentation on Tech Mahindra's digital capabilities. Services, case studies.", "Tech Mahindra", ["Service overview", "Case studies", "Differentiators", "Pricing model", "Next steps"]),
    # Capgemini
    ("Connected Platform Proposal", "Write a digital transformation proposal using Connected Platform. Tech stack, timeline, governance.", "Capgemini", ["Technology stack", "Implementation phases", "Timeline", "Governance", "Expected outcomes"]),
    ("Altran Integration Report", "Write a report on Altran integration progress. Milestones, challenges, synergies.", "Capgemini", ["Milestones", "Challenges", "Synergies", "Timeline", "Next steps"]),
]

# ============================================================================
# SPEAKING: 3 general + 2 per company
# ============================================================================
ALL_SPEAKING = [
    # (prompt, task_type, company, reference_text)
    ("Describe your favorite hobby and why you enjoy it.", "personal", "", "Introduction → How started → Why enjoy → Benefits → Conclusion"),
    ("Talk about a memorable childhood experience.", "personal", "", "Setting → Event → Feelings → Why memorable → What learned"),
    ("Describe a place you'd like to visit and why.", "opinion", "", "Name place → Why chosen → What to do → Cultural significance"),
    # Accenture
    ("Describe Accenture's Innovation Architecture.", "professional", "Accenture", "Hubs → Labs → Studios → Capabilities"),
    ("Explain Accenture Cloud First benefits.", "professional", "Accenture", "Cloud migration → Optimization → Management"),
    # TCS
    ("Describe your TCS ILP training experience.", "professional", "TCS", "Technical training → Soft skills → Mentorship → Career growth"),
    ("Explain how TCS iON helps enterprises.", "professional", "TCS", "Cloud features → Education → Manufacturing apps"),
    # Cognizant
    ("Describe Cognizant's Squads and Pods model.", "professional", "Cognizant", "Agile methodology → Team structure → Delivery benefits"),
    ("Explain Cognizant's digital transformation approach.", "professional", "Cognizant", "Digital services → Consulting → Implementation"),
    # Wipro
    ("Describe Wipro's FullStride Cloud Services.", "professional", "Wipro", "Cloud migration approach → Tools → Success stories"),
    ("Explain Wipro's 'Applying Thought' strategy.", "professional", "Wipro", "Core services → Products → Ecosystem partnerships"),
    # Infosys
    ("Describe the Infosys Mysore campus.", "professional", "Infosys", "Campus size → Facilities → Training → Culture"),
    ("Explain Infosys Nia AI platform.", "professional", "Infosys", "AI capabilities → Automation → Business benefits"),
    # HCL
    ("Describe HCL's MyEureka platform.", "professional", "HCL", "Idea submission → Evaluation → Implementation"),
    ("Explain HCL's Mode 1-2-3 strategy.", "professional", "HCL", "Core IT services → Products → Platform business"),
    # Tech Mahindra
    ("Describe Tech Mahindra's 5G role.", "professional", "Tech Mahindra", "5G capabilities → Telecom expertise → Digital solutions"),
    ("Explain Tech Mahindra's digital approach.", "professional", "Tech Mahindra", "Cloud → AI/ML → IoT → Cybersecurity → Consulting"),
    # Capgemini
    ("Describe Capgemini's Connected Platform.", "professional", "Capgemini", "Cloud → Data → AI → Cybersecurity integration"),
    ("Explain Capgemini Invent's role.", "professional", "Capgemini", "Innovation projects → Consulting → Creative solutions"),
]


async def main():
    MONGO = "mongodb://localhost:27017"
    DB = "CommunicationIQ"
    print(f"Connecting to {MONGO}/{DB} ...")
    client = AsyncIOMotorClient(MONGO, serverSelectionTimeoutMS=5000)
    try:
        await client.admin.command("ping")
        print("✅ MongoDB connected!")
    except Exception as e:
        print(f"❌ Cannot connect: {e}")
        print("   Start MongoDB locally on port 27017")
        return

    await init_beanie(database=client[DB], document_models=MODELS)
    counts = {"quiz": 0, "reading": 0, "reading_q": 0, "listening": 0, "listening_q": 0, "writing": 0, "speaking": 0}

    # ── Quiz questions ─────────────────────────────────────────────────────
    for stem, options, correct, explanation in GENERAL_GRAMMAR + GENERAL_VOCABULARY:
        if await QuizItem.find_one(QuizItem.stem == stem):
            continue
        await QuizItem(id=uid(), category="grammar", stem=stem, options=options,
                       correct_index=correct, explanation=explanation, company="",
                       seconds_allowed=30, status="published").create()
        counts["quiz"] += 1

    for company, questions in COMPANY_QUIZ.items():
        for stem, options, correct, explanation in questions:
            if await QuizItem.find_one(QuizItem.stem == stem):
                continue
            await QuizItem(id=uid(), category="company_info", stem=stem, options=options,
                           correct_index=correct, explanation=explanation, company=company,
                           seconds_allowed=30, status="published").create()
            counts["quiz"] += 1

    # ── Reading passages + QuizItem questions ──────────────────────────────
    for title, body, company, questions in ALL_READING:
        existing = await ReadingPassage.find_one(ReadingPassage.title == title)
        if existing:
            passage_id = existing.id
        else:
            passage_id = uid()
            word_count = len(body.split())
            await ReadingPassage(id=passage_id, title=title, body=body,
                                 kind=company or "general", company=company,
                                 word_count=word_count, status="published").create()
            counts["reading"] += 1

        # Create QuizItem records for reading comprehension questions
        for stem, options, correct, explanation in questions:
            existing_q = await QuizItem.find_one(
                QuizItem.stem == stem, QuizItem.passage_id == passage_id)
            if existing_q:
                continue
            await QuizItem(id=uid(), category="reading_comprehension", stem=stem,
                           options=options, correct_index=correct,
                           explanation=explanation, company=company,
                           passage_id=passage_id, seconds_allowed=60,
                           status="published").create()
            counts["reading_q"] += 1

    # ── Listening passages + QuizItem questions ────────────────────────────
    for title, transcript, company, questions in ALL_LISTENING:
        existing = await ListeningPassage.find_one(ListeningPassage.title == title)
        if existing:
            passage_id = existing.id
        else:
            passage_id = uid()
            await ListeningPassage(id=passage_id, title=title, transcript=transcript,
                                   kind=company, company=company,
                                   status="published").create()
            counts["listening"] += 1

        # Create QuizItem records for audio comprehension questions
        for stem, options, correct, explanation in questions:
            existing_q = await QuizItem.find_one(
                QuizItem.stem == stem, QuizItem.passage_id == passage_id)
            if existing_q:
                continue
            await QuizItem(id=uid(), category="audio_comprehension", stem=stem,
                           options=options, correct_index=correct,
                           explanation=explanation, company=company,
                           passage_id=passage_id, seconds_allowed=60,
                           status="published").create()
            counts["listening_q"] += 1

    # ── Writing prompts ────────────────────────────────────────────────────
    for title, prompt, company, key_points in ALL_WRITING:
        if await WritingPrompt.find_one(WritingPrompt.title == title):
            continue
        await WritingPrompt(id=uid(), title=title, prompt=prompt,
                            kind=company or "general", company=company,
                            key_points=key_points, status="published").create()
        counts["writing"] += 1

    # ── Speaking items ─────────────────────────────────────────────────────
    for prompt, task_type, company, reference_text in ALL_SPEAKING:
        if await TaskItem.find_one(TaskItem.prompt_text == prompt):
            continue
        await TaskItem(id=uid(), task_type=task_type, prompt_text=prompt,
                       company=company, reference_text=reference_text,
                       status="published").create()
        counts["speaking"] += 1

    # ── Summary ────────────────────────────────────────────────────────────
    total_new = sum(counts.values())
    print(f"\n{'='*60}")
    print(f"SEEDING COMPLETE — {total_new} new items added")
    print(f"{'='*60}")

    total_q = await QuizItem.count()
    total_r = await ReadingPassage.count()
    total_l = await ListeningPassage.count()
    total_w = await WritingPrompt.count()
    total_s = await TaskItem.count()

    print(f"\nNew items added:")
    print(f"  Quiz questions:      {counts['quiz']}")
    print(f"  Reading passages:    {counts['reading']} (+ {counts['reading_q']} questions)")
    print(f"  Listening passages:  {counts['listening']} (+ {counts['listening_q']} questions)")
    print(f"  Writing prompts:     {counts['writing']}")
    print(f"  Speaking items:      {counts['speaking']}")

    print(f"\nTotal in database:")
    print(f"  Quiz Items:          {total_q}")
    print(f"  Reading Passages:    {total_r}")
    print(f"  Listening Passages:  {total_l}")
    print(f"  Writing Prompts:     {total_w}")
    print(f"  Speaking Items:      {total_s}")

    # Per-company breakdown
    print(f"\n{'='*60}")
    print("Per-company breakdown:")
    gen_q = await QuizItem.find(QuizItem.company == "").count()
    print(f"  General: {gen_q} quiz")
    for c in COMPANIES:
        nq = await QuizItem.find(QuizItem.company == c).count()
        nr = await ReadingPassage.find(ReadingPassage.company == c).count()
        nl = await ListeningPassage.find(ListeningPassage.company == c).count()
        nw = await WritingPrompt.find(WritingPrompt.company == c).count()
        ns = await TaskItem.find(TaskItem.company == c).count()
        print(f"  {c:15s}: {nq:2d} quiz, {nr} reading, {nl} listening, {nw} writing, {ns} speaking")
    print(f"{'='*60}")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
