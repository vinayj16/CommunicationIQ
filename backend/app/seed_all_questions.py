"""Master seeder - seeds ALL company questions using the same DB config as the backend.

Run: cd backend && python -m app.seed_all_questions
"""
from __future__ import annotations
import asyncio
import uuid
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
from app.models.tenant import (
    QuizItem, ReadingPassage, ListeningPassage, WritingPrompt, TaskItem,
)

def uid() -> str:
    return str(uuid.uuid4())

def _rand_difficulty() -> float:
    """Random difficulty: ~30% easy, ~40% medium, ~30% hard."""
    import random as _r
    r = _r.random()
    if r < 0.30:
        return round(_r.uniform(0.1, 0.33), 2)
    elif r < 0.70:
        return round(_r.uniform(0.34, 0.66), 2)
    else:
        return round(_r.uniform(0.67, 0.95), 2)

# ============================================================================
# ALL COMPANY QUIZ QUESTIONS - 10 per company = 80 total
# ============================================================================

ALL_COMPANY_QUIZ = {
    "Accenture": [
        {"stem": "Accenture is headquartered in:", "options": ["New York", "Dublin, Ireland", "London", "Bangalore"], "correct_index": 1, "explanation": "Accenture is headquartered in Dublin, Ireland."},
        {"stem": "Accenture was originally part of which company?", "options": ["IBM", "Andersen Consulting", "Deloitte", "KPMG"], "correct_index": 1, "explanation": "Accenture was formerly Andersen Consulting."},
        {"stem": "Accenture's stock ticker symbol is:", "options": ["ACN", "ACC", "ACNT", "ASC"], "correct_index": 0, "explanation": "Accenture trades on NYSE as ACN."},
        {"stem": "Accenture operates in approximately how many countries?", "options": ["50", "100", "120+", "200"], "correct_index": 2, "explanation": "Accenture operates in 120+ countries."},
        {"stem": "Accenture's consulting services include:", "options": ["Only IT consulting", "Strategy, Consulting, Digital, Technology, Operations", "Only management consulting", "Only outsourcing"], "correct_index": 1, "explanation": "Full range of consulting services."},
        {"stem": "Accenture was renamed in which year?", "options": ["1995", "2000", "2001", "2005"], "correct_index": 2, "explanation": "Renamed to Accenture in 2001."},
        {"stem": "Accenture's hiring process typically includes:", "options": ["Only interview", "Online test, interview rounds, and HR", "Only aptitude test", "Group discussion only"], "correct_index": 1, "explanation": "Complete hiring process."},
        {"stem": "Accenture employs approximately how many people?", "options": ["200,000", "400,000", "600,000+", "800,000"], "correct_index": 2, "explanation": "Over 600,000 employees."},
        {"stem": "What is Accenture's innovation approach called?", "options": ["Innovation Hub", "Innovation Architecture", "Tech Lab", "Digital Factory"], "correct_index": 1, "explanation": "Innovation Architecture."},
        {"stem": "What is Accenture Cloud First?", "options": ["A cloud platform", "Cloud adoption service", "A training program", "A consulting method"], "correct_index": 1, "explanation": "Cloud adoption service."},
    ],
    "TCS": [
        {"stem": "TCS stands for:", "options": ["Tata Computer Services", "Tata Consultancy Services", "Tata Computing Solutions", "Tata Communication Services"], "correct_index": 1, "explanation": "Tata Consultancy Services."},
        {"stem": "TCS iON refers to:", "options": ["A type of software", "A cloud-based platform", "A hardware product", "A programming language"], "correct_index": 1, "explanation": "Cloud-based platform."},
        {"stem": "Which is a core value of TCS?", "options": ["Speed above all", "Leading change", "Individual achievement", "Short-term results"], "correct_index": 1, "explanation": "Leading Change."},
        {"stem": "TCS hiring includes which rounds?", "options": ["Only technical", "Aptitude, Technical, and HR", "Only HR", "Group discussion only"], "correct_index": 1, "explanation": "Multiple rounds."},
        {"stem": "TCS was founded in:", "options": ["1968", "1975", "1985", "1990"], "correct_index": 0, "explanation": "Founded in 1968."},
        {"stem": "TCS's flagship banking platform is:", "options": ["iON", "BaNCS", "Finacle", "EdgeVerve"], "correct_index": 1, "explanation": "TCS BaNCS."},
        {"stem": "TCS training typically lasts:", "options": ["1 month", "2-3 months", "6 months", "1 year"], "correct_index": 1, "explanation": "2-3 months."},
        {"stem": "TCS operates in approximately how many countries?", "options": ["20", "46", "60", "80"], "correct_index": 1, "explanation": "46 countries."},
        {"stem": "TCS employs approximately:", "options": ["400,000", "500,000", "600,000+", "800,000"], "correct_index": 2, "explanation": "600,000+ employees."},
        {"stem": "TCS is part of which group?", "options": ["Reliance", "Tata Group", "Adani", "Birla"], "correct_index": 1, "explanation": "Tata Group."},
    ],
    "Cognizant": [
        {"stem": "Cognizant is headquartered in:", "options": ["Mumbai", "Teaneck, New Jersey", "Chennai", "Hyderabad"], "correct_index": 1, "explanation": "Teaneck, New Jersey."},
        {"stem": "Cognizant was founded in:", "options": ["1990", "1994", "2000", "2005"], "correct_index": 1, "explanation": "Founded in 1994."},
        {"stem": "Cognizant's primary focus is:", "options": ["Hardware", "IT services and consulting", "Software products", "Telecom"], "correct_index": 1, "explanation": "IT services and consulting."},
        {"stem": "Cognizant was originally a subsidiary of:", "options": ["TCS", "Dun & Bradstreet", "Infosys", "Wipro"], "correct_index": 1, "explanation": "Dun & Bradstreet."},
        {"stem": "Cognizant operates in how many countries?", "options": ["20", "35", "50+", "80"], "correct_index": 2, "explanation": "50+ countries."},
        {"stem": "Cognizant's stock trades on:", "options": ["NYSE", "NASDAQ", "BSE", "LSE"], "correct_index": 1, "explanation": "NASDAQ as CTSH."},
        {"stem": "Cognizant employs approximately:", "options": ["100,000", "200,000", "300,000+", "500,000"], "correct_index": 2, "explanation": "300,000+ employees."},
        {"stem": "Cognizant's service areas include:", "options": ["Only IT support", "Digital, Technology, Consulting, Operations", "Only software", "Only BPO"], "correct_index": 1, "explanation": "Full service range."},
        {"stem": "Cognizant's digital strategy is called:", "options": ["Traditional IT only", "Edge Concentration", "Outsourcing only", "Hardware focus"], "correct_index": 1, "explanation": "Edge Concentration."},
        {"stem": "Cognizant's delivery model is:", "options": ["Waterfall", "Squads and Pods", "Remote only", "Fixed teams"], "correct_index": 1, "explanation": "Squads and Pods."},
    ],
    "Wipro": [
        {"stem": "Wipro was founded by:", "options": ["N. R. Narayana Murthy", "Azim Premji", "Kumar Mangalam Birla", "Ratan Tata"], "correct_index": 1, "explanation": "Azim Premji."},
        {"stem": "Wipro's headquarters is in:", "options": ["Mumbai", "Bangalore", "Hyderabad", "Chennai"], "correct_index": 1, "explanation": "Bangalore."},
        {"stem": "Wipro is known for:", "options": ["Only IT services", "IT, consulting, and business process services", "Only manufacturing", "Only healthcare"], "correct_index": 1, "explanation": "Multiple service areas."},
        {"stem": "Wipro was originally a company making:", "options": ["Software", "Vegetable oil", "Computers", "Mobile phones"], "correct_index": 1, "explanation": "Vegetable oil company."},
        {"stem": "Wipro's tagline is:", "options": ["Think Big", "Applying Thought", "Innovation for All", "Building the Future"], "correct_index": 1, "explanation": "Applying Thought."},
        {"stem": "Wipro operates in how many countries?", "options": ["20", "35", "50", "70"], "correct_index": 1, "explanation": "35+ countries."},
        {"stem": "Wipro's annual revenue is approximately:", "options": ["$5 billion", "$10 billion", "$20 billion", "$50 billion"], "correct_index": 1, "explanation": "$10+ billion."},
        {"stem": "Wipro's competitors include:", "options": ["Only TCS", "TCS, Infosys, HCL", "Only Google", "Only Microsoft"], "correct_index": 1, "explanation": "Multiple competitors."},
        {"stem": "Wipro's full name is:", "options": ["Western India Palm Refined Oils", "Worldwide Integrated Products", "Wipro Products Limited", "Wipro International"], "correct_index": 0, "explanation": "Western India Palm Refined Oils."},
        {"stem": "Wipro's AI platform is called:", "options": ["BaNCS", "HOLMES", "Nia", "Cloud First"], "correct_index": 1, "explanation": "Wipro HOLMES."},
    ],
    "Infosys": [
        {"stem": "Infosys was founded by:", "options": ["N. R. Narayana Murthy", "Azim Premji", "Kumar Mangalam Birla", "Ratan Tata"], "correct_index": 0, "explanation": "N. R. Narayana Murthy."},
        {"stem": "Infosys is headquartered in:", "options": ["Mumbai", "Bangalore", "Hyderabad", "Chennai"], "correct_index": 1, "explanation": "Bangalore."},
        {"stem": "Infosys's famous training center is:", "options": ["Mysore Campus", "Bangalore Academy", "Hyderabad Center", "Chennai Institute"], "correct_index": 0, "explanation": "Mysore Campus."},
        {"stem": "Infosys's AI platform is:", "options": ["iON", "Infosys Nia", "Wingspan", "EdgeVerve"], "correct_index": 1, "explanation": "Infosys Nia."},
        {"stem": "Infosys was incorporated in:", "options": ["1975", "1981", "1990", "1995"], "correct_index": 1, "explanation": "1981."},
        {"stem": "First Indian company on NASDAQ:", "options": ["TCS", "Wipro", "Infosys", "HCL"], "correct_index": 2, "explanation": "Infosys."},
        {"stem": "EdgeVerve provides:", "options": ["Cloud computing", "Enterprise software solutions", "Hardware", "Social media"], "correct_index": 1, "explanation": "Enterprise software."},
        {"stem": "Infosys Foundation focuses on:", "options": ["Only education", "Education, healthcare, rural development", "Only healthcare", "Only technology"], "correct_index": 1, "explanation": "Multiple areas."},
        {"stem": "Infosys employs approximately:", "options": ["50,000", "100,000", "250,000", "500,000"], "correct_index": 2, "explanation": "250,000+ employees."},
        {"stem": "Infosys's learning platform is:", "options": ["Ultimatix", "Lex", "iLearn", "MyEureka"], "correct_index": 1, "explanation": "Lex."},
    ],
    "HCL": [
        {"stem": "HCL was founded in:", "options": ["1970", "1976", "1985", "1990"], "correct_index": 1, "explanation": "1976."},
        {"stem": "HCL is headquartered in:", "options": ["Bangalore", "Noida, India", "Mumbai", "Chennai"], "correct_index": 1, "explanation": "Noida, India."},
        {"stem": "HCL's strategy is called:", "options": ["Mode 1-2-3", "Digital First", "Cloud Ready", "Innovation Hub"], "correct_index": 0, "explanation": "Mode 1-2-3."},
        {"stem": "HCL operates in how many countries?", "options": ["30", "40", "52", "65"], "correct_index": 2, "explanation": "52 countries."},
        {"stem": "HCL employs approximately:", "options": ["150,000", "175,000", "225,000+", "300,000"], "correct_index": 2, "explanation": "225,000+ employees."},
        {"stem": "HCL's innovation platform is:", "options": ["Innovation Hub", "MyEureka", "IdeaStream", "ThinkTank"], "correct_index": 1, "explanation": "MyEureka."},
        {"stem": "HCL's Digital Foundation enables:", "options": ["Only cloud", "Cloud-native transformation", "Only data analytics", "Only cybersecurity"], "correct_index": 1, "explanation": "Cloud-native transformation."},
        {"stem": "HCL is known for its:", "options": ["Hardware products", "Employee-first culture", "Only software", "Only consulting"], "correct_index": 1, "explanation": "Employee-first culture."},
        {"stem": "HCL's annual revenue exceeded:", "options": ["$5 billion", "$8 billion", "$12 billion+", "$20 billion"], "correct_index": 2, "explanation": "$12 billion+."},
        {"stem": "HCL's core areas include:", "options": ["Only IT services", "IT services, engineering, and R&D", "Only manufacturing", "Only consulting"], "correct_index": 1, "explanation": "Multiple areas."},
    ],
    "Tech Mahindra": [
        {"stem": "Tech Mahindra was founded in:", "options": ["1975", "1986", "1995", "2000"], "correct_index": 1, "explanation": "1986."},
        {"stem": "Tech Mahindra is headquartered in:", "options": ["Mumbai", "Pune", "Noida", "Hyderabad"], "correct_index": 1, "explanation": "Pune, Maharashtra."},
        {"stem": "Tech Mahindra is a subsidiary of:", "options": ["Tata Group", "Mahindra Group", "Reliance", "Adani"], "correct_index": 1, "explanation": "Mahindra Group."},
        {"stem": "Tech Mahindra trades on:", "options": ["NYSE", "BSE and NSE", "NASDAQ", "LSE"], "correct_index": 1, "explanation": "BSE and NSE."},
        {"stem": "Tech Mahindra merged with:", "options": ["Wipro", "Satyam Computer Services", "HCL", "Infosys"], "correct_index": 1, "explanation": "Satyam Computer Services."},
        {"stem": "Tech Mahindra operates in:", "options": ["30", "50", "90", "120"], "correct_index": 2, "explanation": "Approximately 90 countries."},
        {"stem": "Tech Mahindra employs approximately:", "options": ["100,000", "150,000", "200,000+", "350,000"], "correct_index": 2, "explanation": "200,000+ employees."},
        {"stem": "Tech Mahindra focuses on:", "options": ["Only IT services", "IT, telecom, and digital transformation", "Only consulting", "Only manufacturing"], "correct_index": 1, "explanation": "Multiple focus areas."},
        {"stem": "Tech Mahindra's annual revenue:", "options": ["$3 billion", "$5 billion", "$7 billion", "$15 billion"], "correct_index": 2, "explanation": "$7+ billion."},
        {"stem": "Tech Mahindra's digital platform:", "options": ["Nia", "HOLMES", "TechM AirVil", "iON"], "correct_index": 2, "explanation": "TechM AirVil."},
    ],
    "Capgemini": [
        {"stem": "Capgemini was founded in:", "options": ["1960", "1967", "1975", "1980"], "correct_index": 1, "explanation": "1967."},
        {"stem": "Capgemini is headquartered in:", "options": ["London", "Paris, France", "New York", "Berlin"], "correct_index": 1, "explanation": "Paris, France."},
        {"stem": "Capgemini operates in:", "options": ["30", "40", "50+", "70"], "correct_index": 2, "explanation": "50+ countries."},
        {"stem": "Capgemini employs approximately:", "options": ["200,000", "275,000", "350,000", "500,000"], "correct_index": 2, "explanation": "350,000 employees."},
        {"stem": "Capgemini acquired in 2020:", "options": ["Accenture", "Altran", "Deloitte", "McKinsey"], "correct_index": 1, "explanation": "Altran."},
        {"stem": "Capgemini's strategy is:", "options": ["Cloud First", "Connected Platform", "Digital Hub", "Innovation Path"], "correct_index": 1, "explanation": "Connected Platform."},
        {"stem": "Capgemini's innovation division:", "options": ["Labs", "Invent", "Studio", "Hub"], "correct_index": 1, "explanation": "Invent."},
        {"stem": "Capgemini's revenue exceeds:", "options": ["€10 billion", "€15 billion", "€22 billion", "€30 billion"], "correct_index": 2, "explanation": "€22 billion."},
        {"stem": "Capgemini's services include:", "options": ["Only consulting", "Consulting, technology, and digital transformation", "Only technology", "Only outsourcing"], "correct_index": 1, "explanation": "Full service range."},
        {"stem": "Connected Platform integrates:", "options": ["Only cloud", "Cloud, data, AI, and cybersecurity", "Only AI", "Only security"], "correct_index": 1, "explanation": "Multiple technologies."},
    ],
}

# General questions
GENERAL_QUIZ = [
    {"stem": "Choose the correct sentence:", "options": ["He don't like coffee.", "He doesn't likes coffee.", "He doesn't like coffee.", "He not like coffee."], "correct_index": 2, "explanation": "Correct form uses 'doesn't' + base verb."},
    {"stem": "Which sentence is correct?", "options": ["She have been working here.", "She has been working here.", "She has been work here.", "She have been work here."], "correct_index": 1, "explanation": "Present perfect continuous."},
    {"stem": "Identify the error: 'The team are working hard to meets the deadline.'", "options": ["are working", "to meets", "the deadline", "No error"], "correct_index": 1, "explanation": "Use base form 'to meet'."},
    {"stem": "Choose the correct preposition: 'She is interested ___ learning.'", "options": ["in", "on", "at", "for"], "correct_index": 0, "explanation": "Interested in."},
    {"stem": "What is the passive voice of: 'The manager approved the proposal.'", "options": ["The proposal approved the manager.", "The proposal was approved by the manager.", "The proposal has approved.", "The proposal is approving."], "correct_index": 1, "explanation": "Object + was + past participle + by + subject."},
    {"stem": "Choose the correct word: 'The company ___ its new office.'", "options": ["opened", "opens", "opening", "open"], "correct_index": 0, "explanation": "Past tense 'opened'."},
    {"stem": "Which uses a semicolon correctly?", "options": ["I like coffee; and tea.", "I like coffee; however, I don't drink tea.", "I like coffee; tea is nice.", "I like coffee; because it tastes good."], "correct_index": 1, "explanation": "Semicolon connects independent clauses."},
    {"stem": "Choose: 'Neither the manager ___ the team was available.'", "options": ["or", "nor", "and", "but"], "correct_index": 1, "explanation": "Neither pairs with nor."},
    {"stem": "Comparative form of 'good':", "options": ["gooder", "more good", "better", "best"], "correct_index": 2, "explanation": "Irregular comparative."},
    {"stem": "Correct sentence:", "options": ["Everyone have their opinion.", "Everyone has their opinion.", "Everyone are having.", "Everyone having."], "correct_index": 1, "explanation": "Everyone is singular."},
    {"stem": "What does 'ubiquitous' mean?", "options": ["Rare", "Found everywhere", "Expensive", "Old"], "correct_index": 1, "explanation": "Present everywhere."},
    {"stem": "Choose synonym for 'mandatory':", "options": ["Optional", "Required", "Suggested", "Voluntary"], "correct_index": 1, "explanation": "Required or compulsory."},
    {"stem": "What does 'ROI' stand for?", "options": ["Rate of Interest", "Return on Investment", "Range of Income", "Risk of Inflation"], "correct_index": 1, "explanation": "Return on Investment."},
    {"stem": "What does 'stakeholder' mean?", "options": ["Holds a stick", "Someone with interest in a project", "Shareholder only", "Project manager"], "correct_index": 1, "explanation": "Anyone with interest in a project."},
    {"stem": "Choose: 'The team needs to ___ the deadline.'", "options": ["meet", "do", "make", "take"], "correct_index": 0, "explanation": "Meet the deadline."},
]

# Reading passages per company
COMPANY_READING = {
    "Accenture": [{"title": "Accenture Innovation Architecture", "body": "Accenture's Innovation Architecture consists of hubs, labs, and studios worldwide. They invested over $3 billion in acquisitions. Cloud First helps enterprises adopt cloud. Revenue exceeded $64 billion.", "kind": "Accenture", "questions": [{"stem": "How much was invested?", "options": ["$1B", "$2B", "$3B", "$5B"], "correct_index": 2, "explanation": "$3 billion."}, {"stem": "What is Cloud First?", "options": ["Platform", "Adoption service", "Training", "Consulting"], "correct_index": 1, "explanation": "Cloud adoption service."}, {"stem": "Revenue exceeded?", "options": ["$40B", "$50B", "$64B+", "$80B"], "correct_index": 2, "explanation": "$64 billion."}, {"stem": "Employees?", "options": ["500K", "600K", "738K", "900K"], "correct_index": 2, "explanation": "738,000."}, {"stem": "Countries?", "options": ["50", "100", "120+", "200"], "correct_index": 2, "explanation": "120+ countries."}]}],
    "TCS": [{"title": "TCS Digital Transformation", "body": "TCS has been at the forefront of digital transformation. They invested $2 billion in R&D. TCS BaNCS serves 500 million customers. TCS iON provides cloud solutions.", "kind": "TCS", "questions": [{"stem": "R&D investment?", "options": ["$1B", "$1.5B", "$2B", "$3B"], "correct_index": 2, "explanation": "$2 billion."}, {"stem": "BaNCS customers?", "options": ["100M", "300M", "500M", "1B"], "correct_index": 2, "explanation": "500 million."}, {"stem": "iON is?", "options": ["Software", "Cloud platform", "Hardware", "Consulting"], "correct_index": 1, "explanation": "Cloud platform."}, {"stem": "Employees?", "options": ["400K", "500K", "600K+", "800K"], "correct_index": 2, "explanation": "600,000+."}, {"stem": "Founded?", "options": ["1968", "1975", "1985", "1990"], "correct_index": 0, "explanation": "1968."}]}],
    "Cognizant": [{"title": "Cognizant Digital Growth", "body": "Cognizant focuses on digital transformation. Their Squads and Pods model provides agile teams. Revenue reached $19.4 billion. Core areas include digital engineering and cloud.", "kind": "Cognizant", "questions": [{"stem": "Delivery model?", "options": ["Waterfall", "Squads and Pods", "Remote", "Fixed"], "correct_index": 1, "explanation": "Squads and Pods."}, {"stem": "Revenue?", "options": ["$10B", "$15B", "$19.4B", "$25B"], "correct_index": 2, "explanation": "$19.4 billion."}, {"stem": "Countries?", "options": ["20", "30", "40+", "60"], "correct_index": 2, "explanation": "40+ countries."}, {"stem": "Employees?", "options": ["200K", "280K", "350K+", "500K"], "correct_index": 2, "explanation": "350,000+."}, {"stem": "Founded?", "options": ["1990", "1994", "2000", "2005"], "correct_index": 1, "explanation": "1994."}]}],
    "Wipro": [{"title": "Wipro Digital Strategy", "body": "Wipro transformed from vegetable oil to global IT leader. HOLMES AI platform powers automation. FullStride Cloud Services help migrate to cloud. Revenue approximately $11 billion.", "kind": "Wipro", "questions": [{"stem": "Originally?", "options": ["Tech company", "Vegetable oil company", "Bank", "Hospital"], "correct_index": 1, "explanation": "Vegetable oil company."}, {"stem": "AI platform?", "options": ["BaNCS", "HOLMES", "Nia", "Cloud First"], "correct_index": 1, "explanation": "HOLMES."}, {"stem": "Revenue?", "options": ["$5B", "$8B", "$11B", "$15B"], "correct_index": 2, "explanation": "$11 billion."}, {"stem": "Countries?", "options": ["30", "45", "66", "80"], "correct_index": 2, "explanation": "66 countries."}, {"stem": "Employees?", "options": ["100K", "150K", "250K+", "350K"], "correct_index": 2, "explanation": "250,000+."}]}],
    "Infosys": [{"title": "Infosys Innovation", "body": "Infosys is a leader in technology innovation. Nia AI platform automates processes. 23 innovation hubs worldwide. Lex provides continuous learning. Revenue exceeded $18 billion.", "kind": "Infosys", "questions": [{"stem": "AI platform?", "options": ["Cloud", "Nia", "Mobile app", "Database"], "correct_index": 1, "explanation": "Infosys Nia."}, {"stem": "Innovation hubs?", "options": ["10", "15", "23", "30"], "correct_index": 2, "explanation": "23 hubs."}, {"stem": "Revenue?", "options": ["$10B", "$15B", "$18B+", "$25B"], "correct_index": 2, "explanation": "$18 billion+."}, {"stem": "Founded?", "options": ["1975", "1981", "1990", "1995"], "correct_index": 1, "explanation": "1981."}, {"stem": "Headquarters?", "options": ["Mumbai", "Bangalore", "Hyderabad", "Chennai"], "correct_index": 1, "explanation": "Bangalore."}]}],
    "HCL": [{"title": "HCL Technologies Overview", "body": "HCL is a global IT services company in Noida. Mode 1-2-3 strategy focuses on core services and platforms. Digital Foundation enables cloud-native transformation. Revenue exceeded $12 billion.", "kind": "HCL", "questions": [{"stem": "Founded?", "options": ["1970", "1976", "1985", "1990"], "correct_index": 1, "explanation": "1976."}, {"stem": "Strategy?", "options": ["Mode 1-2-3", "Digital First", "Cloud Ready", "Innovation Hub"], "correct_index": 0, "explanation": "Mode 1-2-3."}, {"stem": "Revenue?", "options": ["$8B", "$10B", "$12B+", "$15B"], "correct_index": 2, "explanation": "$12 billion+."}, {"stem": "Innovation platform?", "options": ["Hub", "MyEureka", "IdeaStream", "ThinkTank"], "correct_index": 1, "explanation": "MyEureka."}, {"stem": "Employees?", "options": ["150K", "175K", "225K+", "300K"], "correct_index": 2, "explanation": "225,000+."}]}],
    "Tech Mahindra": [{"title": "Tech Mahindra Digital", "body": "Tech Mahindra provides digital transformation and consulting. Merged with Satyam in 2015. Focus on 5G, cloud, and AI. Revenue approximately $7 billion.", "kind": "Tech Mahindra", "questions": [{"stem": "Merged with?", "options": ["Wipro", "Satyam", "HCL", "Infosys"], "correct_index": 1, "explanation": "Satyam Computer Services."}, {"stem": "Revenue?", "options": ["$3B", "$5B", "$7B", "$15B"], "correct_index": 2, "explanation": "$7 billion+."}, {"stem": "Headquarters?", "options": ["Mumbai", "Pune", "Noida", "Hyderabad"], "correct_index": 1, "explanation": "Pune."}, {"stem": "Focus areas?", "options": ["Only IT", "IT, telecom, digital", "Only consulting", "Only manufacturing"], "correct_index": 1, "explanation": "Multiple areas."}, {"stem": "Employees?", "options": ["100K", "150K", "200K+", "350K"], "correct_index": 2, "explanation": "200,000+."}]}],
    "Capgemini": [{"title": "Capgemini Excellence", "body": "Capgemini is a global leader in consulting and digital transformation. Connected Platform integrates cloud, data, AI, and cybersecurity. Acquired Altran in 2020. Revenue exceeds €22 billion.", "kind": "Capgemini", "questions": [{"stem": "Founded?", "options": ["1960", "1967", "1975", "1980"], "correct_index": 1, "explanation": "1967."}, {"stem": "Strategy?", "options": ["Cloud First", "Connected Platform", "Digital Hub", "Innovation Path"], "correct_index": 1, "explanation": "Connected Platform."}, {"stem": "Acquired?", "options": ["Accenture", "Altran", "Deloitte", "McKinsey"], "correct_index": 1, "explanation": "Altran in 2020."}, {"stem": "Revenue?", "options": ["€15B", "€18B", "€22B+", "€30B"], "correct_index": 2, "explanation": "€22 billion+."}, {"stem": "Employees?", "options": ["200K", "275K", "350K", "500K"], "correct_index": 2, "explanation": "350,000."}]}],
}


async def main():
    """Seed all questions using the same DB config as the backend."""
    client = AsyncIOMotorClient(settings.mongo_uri)
    await init_beanie(
        database=client[settings.control_db_name],
        document_models=[QuizItem, ReadingPassage, ListeningPassage, WritingPrompt, TaskItem],
    )
    
    count = 0
    
    # Seed general quiz questions
    for q in GENERAL_QUIZ:
        existing = await QuizItem.find(QuizItem.stem == q["stem"]).first()
        if existing:
            continue
        item = QuizItem(
            id=uid(), category="grammar", stem=q["stem"],
            options=q["options"], correct_index=q["correct_index"],
            explanation=q["explanation"], company="",
            seconds_allowed=30, difficulty=_rand_difficulty(), status="published",
        )
        await item.create()
        count += 1
    
    # Seed company quiz questions
    for company, questions in ALL_COMPANY_QUIZ.items():
        for q in questions:
            existing = await QuizItem.find(QuizItem.stem == q["stem"]).first()
            if existing:
                continue
            item = QuizItem(
                id=uid(), category="company_info", stem=q["stem"],
                options=q["options"], correct_index=q["correct_index"],
                explanation=q["explanation"], company=company,
                seconds_allowed=30, difficulty=_rand_difficulty(), status="published",
            )
            await item.create()
            count += 1
    
    # Seed reading passages
    for company, passages in COMPANY_READING.items():
        for p in passages:
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
    
    # Count totals
    total_quiz = await QuizItem.find_all().count()
    total_reading = await ReadingPassage.find_all().count()
    quiz_general = await QuizItem.find(QuizItem.company == "").count()
    quiz_companies = await QuizItem.find(QuizItem.company != "").count()
    
    # Count per company
    print(f"\n{'='*60}")
    print(f"SEEDING COMPLETE - Added {count} new questions")
    print(f"{'='*60}")
    print(f"\nTotal Quiz Items: {total_quiz}")
    print(f"  General: {quiz_general}")
    print(f"  Company: {quiz_companies}")
    print(f"\nTotal Reading Passages: {total_reading}")
    
    for company in ALL_COMPANY_QUIZ.keys():
        c = await QuizItem.find(QuizItem.company == company).count()
        r = await ReadingPassage.find(ReadingPassage.kind == company).count()
        print(f"  {company}: {c} quiz, {r} reading")
    
    print(f"{'='*60}")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
