"""Question bank seeder - adds questions without deleting existing data.

Targets per skill:
- General: ~200 questions (grammar, vocabulary, reading, listening, writing, speaking)
- Company-specific: ~50 per company (TCS, Infosys, Wipro, Accenture, Cognizant, HCL, Capgemini)

Run: cd backend && python -m app.seed_questions
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.models.tenant import (
    QuizItem,
    ReadingPassage,
    ListeningPassage,
    WritingPrompt,
    TaskItem,
)

MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "CommunicationIQ"

def uid() -> str:
    return str(uuid.uuid4())


# =========================================================================
# GENERAL QUIZ QUESTIONS (Grammar & Vocabulary) - 100 total
# =========================================================================

GENERAL_GRAMMAR_QUESTIONS = [
    {"stem": "Choose the correct sentence:", "options": ["He don't like coffee.", "He doesn't likes coffee.", "He doesn't like coffee.", "He not like coffee."], "correct_index": 2, "explanation": "The correct form uses 'doesn't' + base verb 'like'."},
    {"stem": "Which sentence is grammatically correct?", "options": ["She have been working here since 2020.", "She has been working here since 2020.", "She has been work here since 2020.", "She have been work here since 2020."], "correct_index": 1, "explanation": "Present perfect continuous: has/have + been + verb-ing."},
    {"stem": "Identify the error: 'The team are working hard to meets the deadline.'", "options": ["are working", "to meets", "the deadline", "No error"], "correct_index": 1, "explanation": "After 'to', use the base form: 'to meet', not 'to meets'."},
    {"stem": "Choose the correct preposition: 'She is interested ___ learning French.'", "options": ["in", "on", "at", "for"], "correct_index": 0, "explanation": "The correct collocation is 'interested in'."},
    {"stem": "Which is the passive voice of: 'The manager approved the proposal.'", "options": ["The proposal approved the manager.", "The proposal was approved by the manager.", "The proposal has approved by the manager.", "The proposal is approving by the manager."], "correct_index": 1, "explanation": "Passive voice: object + was/were + past participle + by + subject."},
    {"stem": "Choose the correct word: 'The company ___ its new office last month.'", "options": ["opened", "opens", "opening", "open"], "correct_index": 0, "explanation": "Past tense 'opened' is correct with 'last month'."},
    {"stem": "Which sentence uses a semicolon correctly?", "options": ["I like coffee; and tea.", "I like coffee; however, I don't drink tea.", "I like coffee; tea is also nice.", "I like coffee; because it tastes good."], "correct_index": 1, "explanation": "A semicolon connects two independent clauses."},
    {"stem": "Choose the correct form: 'Neither the manager ___ the team was available.'", "options": ["or", "nor", "and", "but"], "correct_index": 1, "explanation": "'Neither' pairs with 'nor'."},
    {"stem": "Which is the comparative form of 'good'?", "options": ["gooder", "more good", "better", "best"], "correct_index": 2, "explanation": "'Better' is the comparative form of 'good' (irregular)."},
    {"stem": "Identify the correct sentence:", "options": ["Everyone have their own opinion.", "Everyone has their own opinion.", "Everyone are having their own opinion.", "Everyone having their own opinion."], "correct_index": 1, "explanation": "'Everyone' is singular and takes 'has'."},
    {"stem": "Choose the correct article: 'She is ___ honest person.'", "options": ["a", "an", "the", "no article"], "correct_index": 1, "explanation": "Use 'an' before words starting with a vowel sound."},
    {"stem": "Which is correct: 'The data ___ been analyzed.'", "options": ["has", "have", "is", "are"], "correct_index": 0, "explanation": "Data is typically treated as singular in modern usage."},
    {"stem": "Identify the error: 'Him and me went to the store.'", "options": ["Him", "me", "went", "to the store"], "correct_index": 0, "explanation": "Use 'He and I' as subject pronouns."},
    {"stem": "Choose the correct tense: 'By next year, I ___ here for five years.'", "options": ["work", "will work", "will have worked", "am working"], "correct_index": 2, "explanation": "Future perfect: will have + past participle."},
    {"stem": "Which sentence is correct?", "options": ["Each of the students have a book.", "Each of the students has a book.", "Each of the students are having a book.", "Each of the students were having a book."], "correct_index": 1, "explanation": "'Each' is singular and takes 'has'."},
    {"stem": "Choose the correct form: 'The information ___ very useful.'", "options": ["are", "is", "were", "have been"], "correct_index": 1, "explanation": "'Information' is an uncountable noun and takes singular verb."},
    {"stem": "Which is the correct tag question: 'She is a doctor, ___?'", "options": ["is she", "isn't she", "doesn't she", "does she"], "correct_index": 1, "explanation": "Positive statement gets negative tag: isn't she?"},
    {"stem": "Choose the correct word: 'The teacher asked us to ___ quiet.'", "options": ["be", "being", "is", "are"], "correct_index": 0, "explanation": "After 'to', use the base form: 'to be'."},
    {"stem": "Identify the correct sentence:", "options": ["Me and him are friends.", "Him and me are friends.", "He and I are friends.", "I and he are friends."], "correct_index": 2, "explanation": "Subject pronouns: 'He and I' (others go last)."},
    {"stem": "Which is correct: 'The news ___ shocking.'", "options": ["are", "is", "were", "have been"], "correct_index": 1, "explanation": "'News' is uncountable and takes singular verb."},
    {"stem": "Choose the correct form: 'She enjoys ___ books.'", "options": ["read", "reading", "to read", "reads"], "correct_index": 1, "explanation": "'Enjoy' is followed by gerund (-ing form)."},
    {"stem": "Which sentence uses 'who' correctly?", "options": ["Who did you meet?", "Whom did you meet?", "Who you met?", "Whom met you?"], "correct_index": 1, "explanation": "'Whom' is the object form used after verbs."},
    {"stem": "Choose the correct preposition: 'She arrived ___ Monday.'", "options": ["in", "on", "at", "by"], "correct_index": 1, "explanation": "Use 'on' with specific days."},
    {"stem": "Which is correct: 'The team ___ playing well.'", "options": ["is", "are", "were", "have been"], "correct_index": 0, "explanation": "Collective nouns take singular verb in American English."},
    {"stem": "Identify the error: 'I haven't went to the store yet.'", "options": ["haven't", "went", "to the store", "yet"], "correct_index": 1, "explanation": "Past participle is 'gone', not 'went'."},
    {"stem": "Choose the correct form: 'There ___ many reasons to celebrate.'", "options": ["is", "are", "was", "has been"], "correct_index": 1, "explanation": "'Reasons' is plural, so use 'are'."},
    {"stem": "Which is correct: 'She is one of the students who ___ here.'", "options": ["is", "are", "was", "has been"], "correct_index": 1, "explanation": "The relative pronoun refers to 'students' (plural)."},
    {"stem": "Choose the correct word: 'The book is ___ the table.'", "options": ["in", "on", "at", "by"], "correct_index": 1, "explanation": "Use 'on' for surfaces."},
    {"stem": "Which sentence is correct?", "options": ["I and my friend went.", "My friend and I went.", "Me and my friend went.", "My friend and me went."], "correct_index": 1, "explanation": "Subject pronouns: 'My friend and I'."},
    {"stem": "Choose the correct form: 'She has ___ finished her work.'", "options": ["already", "yet", "since", "for"], "correct_index": 0, "explanation": "'Already' is used in affirmative sentences with present perfect."},
    {"stem": "Which is the correct plural of 'child'?", "options": ["childs", "childes", "children", "childrens"], "correct_index": 2, "explanation": "'Children' is the irregular plural of 'child'."},
    {"stem": "Choose the correct preposition: 'The meeting is ___ 3 PM.'", "options": ["in", "on", "at", "by"], "correct_index": 2, "explanation": "Use 'at' with specific times."},
    {"stem": "Which sentence uses a comma correctly?", "options": ["I bought eggs, milk, and bread.", "I bought eggs milk and bread.", "I, bought eggs milk and bread.", "I bought eggs, milk and, bread."], "correct_index": 0, "explanation": "Use commas to separate items in a list."},
    {"stem": "Identify the correct sentence:", "options": ["The number of students are increasing.", "The number of students is increasing.", "A number of students is increasing.", "A number of students were increasing."], "correct_index": 1, "explanation": "'The number of' takes singular verb; 'a number of' takes plural."},
    {"stem": "Choose the correct form: 'I wish I ___ fly.'", "options": ["can", "could", "will", "may"], "correct_index": 1, "explanation": "After 'wish', use past tense for present wishes."},
    {"stem": "Which is correct: 'She asked me where ___?'", "options": ["I was going", "was I going", "I am going", "am I going"], "correct_index": 0, "explanation": "In reported questions, use statement word order."},
    {"stem": "Choose the correct word: 'He is ___ tallest in the class.'", "options": ["a", "an", "the", "no article"], "correct_index": 2, "explanation": "Use 'the' with superlatives."},
    {"stem": "Which sentence is grammatically correct?", "options": ["Neither of the answers is correct.", "Neither of the answers are correct.", "Neither of the answers were correct.", "Neither of the answers have been correct."], "correct_index": 0, "explanation": "'Neither of' takes singular verb."},
    {"stem": "Choose the correct form: 'She suggested that he ___ early.'", "options": ["comes", "come", "came", "coming"], "correct_index": 1, "explanation": "After 'suggested that', use subjunctive: base form."},
    {"stem": "Identify the error: 'The weather is too hot for wearing a jacket.'", "options": ["is too", "hot for", "wearing", "a jacket"], "correct_index": 2, "explanation": "Use infinitive: 'to wear', not 'wearing'."},
    {"stem": "Choose the correct preposition: 'She is afraid ___ spiders.'", "options": ["with", "of", "from", "about"], "correct_index": 1, "explanation": "The correct collocation is 'afraid of'."},
    {"stem": "Which is correct: 'He has been working here ___ 2019.'", "options": ["for", "since", "from", "in"], "correct_index": 1, "explanation": "Use 'since' with a specific point in time."},
    {"stem": "Choose the correct form: 'The committee ___ decided.'", "options": ["have", "has", "are", "were"], "correct_index": 1, "explanation": "Collective noun 'committee' takes singular verb."},
    {"stem": "Which sentence uses 'less' correctly?", "options": ["Less people attended.", "Fewer people attended.", "Less people was there.", "Fewer people was there."], "correct_index": 1, "explanation": "'Fewer' is used with countable nouns."},
    {"stem": "Choose the correct word: 'She looked at ___ in the mirror.'", "options": ["she", "her", "hers", "herself"], "correct_index": 3, "explanation": "Reflexive pronoun 'herself' is correct after 'looked at'."},
    {"stem": "Identify the correct sentence:", "options": ["If I was you, I would go.", "If I were you, I would go.", "If I am you, I would go.", "If I be you, I would go."], "correct_index": 1, "explanation": "Subjunctive mood: 'If I were you'."},
    {"stem": "Choose the correct form: 'She is ___ than her sister.'", "options": ["more taller", "taller", "most tall", "tallest"], "correct_index": 1, "explanation": "One-syllable adjectives use '-er' for comparative."},
    {"stem": "Which is correct: 'The book belongs to ___.'", "options": ["my", "mine", "me", "I"], "correct_index": 1, "explanation": "'Mine' is the possessive pronoun used alone."},
    {"stem": "Choose the correct preposition: 'He is interested ___ music.'", "options": ["at", "on", "in", "for"], "correct_index": 2, "explanation": "The correct collocation is 'interested in'."},
    {"stem": "Which sentence is correct?", "options": ["I seen him yesterday.", "I saw him yesterday.", "I see him yesterday.", "I have saw him yesterday."], "correct_index": 1, "explanation": "Past tense: 'saw' (not 'seen' which needs 'have')."},
    {"stem": "Choose the correct form: 'She asked me ___ I liked coffee.'", "options": ["that", "if", "what", "which"], "correct_index": 1, "explanation": "Use 'if' for yes/no questions in reported speech."},
    {"stem": "Identify the error: 'Each students must submit their assignment.'", "options": ["Each", "students", "must", "submit"], "correct_index": 1, "explanation": "'Each' is singular: 'Each student'."},
    {"stem": "Choose the correct word: 'The sun rises ___ the east.'", "options": ["in", "on", "at", "from"], "correct_index": 0, "explanation": "Use 'in' with directions."},
    {"stem": "Which is correct: 'She is ___ only person who knows.'", "options": ["a", "an", "the", "no article"], "correct_index": 2, "explanation": "Use 'the' with 'only'."},
]

GENERAL_VOCABULARY_QUESTIONS = [
    {"stem": "What does 'ubiquitous' mean?", "options": ["Rare and unique", "Found everywhere", "Extremely expensive", "Very old"], "correct_index": 1, "explanation": "Ubiquitous means present everywhere."},
    {"stem": "Choose the word that best completes: 'The manager was very ___ about the new policy.'", "options": ["ambiguous", "explicit", "reluctant", "indifferent"], "correct_index": 1, "explanation": "Explicit means clear and detailed."},
    {"stem": "What is the meaning of 'procurement'?", "options": ["Selling products", "Buying or obtaining goods/services", "Manufacturing items", "Storing inventory"], "correct_index": 1, "explanation": "Procurement is acquiring goods or services."},
    {"stem": "Choose the synonym for 'mandatory':", "options": ["Optional", "Required", "Suggested", "Voluntary"], "correct_index": 1, "explanation": "Mandatory means required or compulsory."},
    {"stem": "What does 'leverage' mean in a business context?", "options": ["To lose something", "To use something to maximum advantage", "To borrow money", "To avoid responsibility"], "correct_index": 1, "explanation": "Leverage means using something to maximum advantage."},
    {"stem": "Choose the antonym of 'transparent':", "options": ["Clear", "Opaque", "Visible", "Bright"], "correct_index": 1, "explanation": "Opaque is the opposite of transparent."},
    {"stem": "What does 'ROI' stand for?", "options": ["Rate of Interest", "Return on Investment", "Range of Income", "Risk of Inflation"], "correct_index": 1, "explanation": "ROI stands for Return on Investment."},
    {"stem": "Choose the word that best fits: 'The project was completed ___ schedule.'", "options": ["in", "on", "at", "by"], "correct_index": 1, "explanation": "The correct preposition is 'on schedule'."},
    {"stem": "What does 'stakeholder' mean?", "options": ["Someone who holds a stick", "Someone with an interest in a project", "A company shareholder only", "A project manager"], "correct_index": 1, "explanation": "A stakeholder is anyone with an interest in a project."},
    {"stem": "Choose the correct word: 'The team needs to ___ the deadline.'", "options": ["meet", "do", "make", "take"], "correct_index": 0, "explanation": "The correct collocation is 'meet the deadline'."},
    {"stem": "What does 'endeavor' mean?", "options": ["To give up", "To try or attempt", "To rest", "To ignore"], "correct_index": 1, "explanation": "Endeavor means to try or attempt."},
    {"stem": "Choose the synonym for 'commence':", "options": ["End", "Begin", "Pause", "Continue"], "correct_index": 1, "explanation": "Commence means to begin or start."},
    {"stem": "What is the meaning of 'liaison'?", "options": ["A type of food", "Communication between groups", "A musical term", "A medical device"], "correct_index": 1, "explanation": "Liaison is communication between groups or organizations."},
    {"stem": "Choose the word that means 'a large amount':", "options": ["Scanty", "Copious", "Sparse", "Minimal"], "correct_index": 1, "explanation": "Copious means abundant or in large amounts."},
    {"stem": "What does 'acquiesce' mean?", "options": ["To argue", "To accept something reluctantly", "To celebrate", "To refuse"], "correct_index": 1, "explanation": "Acquiesce means to accept something reluctantly."},
    {"stem": "Choose the antonym of 'benevolent':", "options": ["Kind", "Malevolent", "Generous", "Charitable"], "correct_index": 1, "explanation": "Malevolent is the opposite of benevolent."},
    {"stem": "What does 'paradigm' mean?", "options": ["A type of question", "A model or pattern", "A mathematical formula", "A type of plant"], "correct_index": 1, "explanation": "Paradigm means a model or pattern of something."},
    {"stem": "Choose the word that means 'to make something less severe':", "options": ["Aggravate", "Mitigate", "Accelerate", "Accentuate"], "correct_index": 1, "explanation": "Mitigate means to make less severe or serious."},
    {"stem": "What is the meaning of 'pragmatic'?", "options": ["Idealistic", "Dealing with things practically", "Emotional", "Theoretical"], "correct_index": 1, "explanation": "Pragmatic means dealing with things practically."},
    {"stem": "Choose the synonym for 'eloquent':", "options": ["Silent", "Articulate", "Confused", "Rude"], "correct_index": 1, "explanation": "Eloquent means fluent or persuasive in speaking."},
    {"stem": "What does 'meticulous' mean?", "options": ["Careless", "Showing great attention to detail", "Lazy", "Fast"], "correct_index": 1, "explanation": "Meticulous means showing great attention to detail."},
    {"stem": "Choose the word that means 'to predict':", "options": ["Retrospect", "Forecast", "Inspect", "Neglect"], "correct_index": 1, "explanation": "Forecast means to predict or estimate."},
    {"stem": "What is the meaning of 'conundrum'?", "options": ["A simple answer", "A difficult problem or question", "A type of puzzle piece", "A mathematical equation"], "correct_index": 1, "explanation": "A conundrum is a difficult problem or question."},
    {"stem": "Choose the antonym of 'ephemeral':", "options": ["Temporary", "Permanent", "Brief", "Fleeting"], "correct_index": 1, "explanation": "Permanent is the opposite of ephemeral (short-lived)."},
    {"stem": "What does 'resilient' mean?", "options": ["Fragile", "Able to recover quickly", "Weak", "Stiff"], "correct_index": 1, "explanation": "Resilient means able to recover quickly from difficulties."},
    {"stem": "Choose the word that means 'to give up':", "options": ["Persist", "Surrender", "Advance", "Continue"], "correct_index": 1, "explanation": "Surrender means to give up or yield."},
    {"stem": "What is the meaning of 'ambiguous'?", "options": ["Clear", "Open to more than one interpretation", "Certain", "Definite"], "correct_index": 1, "explanation": "Ambiguous means open to more than one interpretation."},
    {"stem": "Choose the synonym for 'diligent':", "options": ["Lazy", "Hardworking", "Careless", "Slow"], "correct_index": 1, "explanation": "Diligent means showing care and effort."},
    {"stem": "What does 'advocate' mean?", "options": ["To oppose", "To publicly recommend or support", "To ignore", "To destroy"], "correct_index": 1, "explanation": "Advocate means to publicly recommend or support."},
    {"stem": "Choose the word that means 'a short journey':", "options": ["Voyage", "Excursion", "Expedition", "Migration"], "correct_index": 1, "explanation": "An excursion is a short journey or trip."},
    {"stem": "What is the meaning of 'coherent'?", "options": ["Confused", "Logical and consistent", "Random", "Broken"], "correct_index": 1, "explanation": "Coherent means logical and consistent."},
    {"stem": "Choose the antonym of 'enormous':", "options": ["Huge", "Tiny", "Massive", "Gigantic"], "correct_index": 1, "explanation": "Tiny is the opposite of enormous."},
    {"stem": "What does 'feasible' mean?", "options": ["Impossible", "Possible and practical", "Difficult", "Illegal"], "correct_index": 1, "explanation": "Feasible means possible and practical to do."},
    {"stem": "Choose the synonym for 'relinquish':", "options": ["Keep", "Give up", "Take", "Hold"], "correct_index": 1, "explanation": "Relinquish means to voluntarily give up."},
    {"stem": "What is the meaning of 'candid'?", "options": ["Secretive", "Truthful and straightforward", "Polite", "Formal"], "correct_index": 1, "explanation": "Candid means truthful and straightforward."},
    {"stem": "Choose the word that means 'to make smaller':", "options": ["Expand", "Diminish", "Increase", "Amplify"], "correct_index": 1, "explanation": "Diminish means to make smaller or less."},
    {"stem": "What does 'nuance' mean?", "options": ["A big difference", "A subtle difference or distinction", "A loud noise", "A type of color"], "correct_index": 1, "explanation": "Nuance is a subtle difference or distinction."},
    {"stem": "Choose the synonym for 'prolific':", "options": ["Unproductive", "Productive and creative", "Lazy", "Quiet"], "correct_index": 1, "explanation": "Prolific means producing much fruit or many offspring."},
    {"stem": "What is the meaning of 'tenacious'?", "options": ["Weak", "Holding firmly to something", "Loose", "Flexible"], "correct_index": 1, "explanation": "Tenacious means holding firmly to something."},
    {"stem": "Choose the antonym of 'optimistic':", "options": ["Hopeful", "Pessimistic", "Positive", "Cheerful"], "correct_index": 1, "explanation": "Pessimistic is the opposite of optimistic."},
    {"stem": "What does 'profound' mean?", "options": ["Shallow", "Very deep or intense", "Simple", "Surface-level"], "correct_index": 1, "explanation": "Profound means very deep or intense."},
    {"stem": "Choose the word that means 'to confirm':", "options": ["Deny", "Validate", "Reject", "Question"], "correct_index": 1, "explanation": "Validate means to confirm or prove true."},
    {"stem": "What is the meaning of 'vindicate'?", "options": ["To blame", "To clear of blame", "To punish", "To accuse"], "correct_index": 1, "explanation": "Vindicate means to clear someone of blame."},
    {"stem": "Choose the synonym for 'scrutinize':", "options": ["Ignore", "Examine closely", "Skip", "Gloss over"], "correct_index": 1, "explanation": "Scrutinize means to examine closely."},
    {"stem": "What does 'obsolete' mean?", "options": ["Modern", "No longer in use", "Popular", "New"], "correct_index": 1, "explanation": "Obsolete means no longer produced or used."},
    {"stem": "Choose the word that means 'to continue':", "options": ["Cease", "Persist", "Stop", "Abandon"], "correct_index": 1, "explanation": "Persist means to continue firmly."},
    {"stem": "What is the meaning of 'austere'?", "options": ["Luxurious", "Severe or strict in manner", "Colorful", "Soft"], "correct_index": 1, "explanation": "Austere means severe or strict in manner."},
    {"stem": "Choose the antonym of 'abundant':", "options": ["Plentiful", "Scarce", "Ample", "Copious"], "correct_index": 1, "explanation": "Scarce is the opposite of abundant."},
    {"stem": "What does 'regimen' mean?", "options": ["A type of medicine", "A systematic plan or routine", "A government official", "A type of exercise"], "correct_index": 1, "explanation": "Regimen is a systematic plan or routine."},
    {"stem": "Choose the synonym for 'deteriorate':", "options": ["Improve", "Worsen", "Maintain", "Stabilize"], "correct_index": 1, "explanation": "Deteriorate means to become progressively worse."},
]


# =========================================================================
# COMPANY QUIZ QUESTIONS
# =========================================================================

TCS_QUESTIONS = [
    {"stem": "TCS stands for:", "options": ["Tata Computer Services", "Tata Consultancy Services", "Tata Computing Solutions", "Tata Communication Services"], "correct_index": 1, "explanation": "TCS stands for Tata Consultancy Services."},
    {"stem": "In TCS, what does 'iON' refer to?", "options": ["A type of software", "A cloud-based platform", "A hardware product", "A programming language"], "correct_index": 1, "explanation": "TCS iON is a cloud-based platform."},
    {"stem": "Which of the following is a core value of TCS?", "options": ["Speed above all", "Leading change", "Individual achievement", "Short-term results"], "correct_index": 1, "explanation": "Leading Change is one of TCS's core values."},
    {"stem": "TCS's hiring process typically includes which round?", "options": ["Only technical interview", "Aptitude, Technical, and HR rounds", "Only HR interview", "Group discussion only"], "correct_index": 1, "explanation": "TCS recruitment typically includes Aptitude, Technical, and HR rounds."},
    {"stem": "In a TCS aptitude test, which section typically comes first?", "options": ["Quantitative Aptitude", "Verbal Ability", "Logical Reasoning", "Programming Questions"], "correct_index": 0, "explanation": "TCS aptitude tests usually start with Quantitative Aptitude."},
    {"stem": "TCS was founded in which year?", "options": ["1968", "1975", "1985", "1990"], "correct_index": 0, "explanation": "TCS was founded in 1968."},
    {"stem": "Which programming language is most commonly asked in TCS interviews?", "options": ["Python", "Java", "C++", "All of the above"], "correct_index": 3, "explanation": "TCS interviews may ask about multiple programming languages."},
    {"stem": "What is the typical duration of TCS training program?", "options": ["1 month", "2-3 months", "6 months", "1 year"], "correct_index": 1, "explanation": "TCS training typically lasts 2-3 months."},
    {"stem": "TCS operates in how many countries approximately?", "options": ["20", "46", "60", "80"], "correct_index": 1, "explanation": "TCS operates in approximately 46 countries."},
    {"stem": "What is TCS's flagship banking platform?", "options": ["iON", "BaNCS", "Finacle", "EdgeVerve"], "correct_index": 1, "explanation": "TCS BaNCS is TCS's banking platform."},
]

INFOSYS_QUESTIONS = [
    {"stem": "Infosys was founded by:", "options": ["N. R. Narayana Murthy", "Azim Premji", "Kumar Mangalam Birla", "Ratan Tata"], "correct_index": 0, "explanation": "Infosys was founded by N. R. Narayana Murthy in 1981."},
    {"stem": "Infosys is headquartered in:", "options": ["Mumbai", "Bangalore", "Hyderabad", "Chennai"], "correct_index": 1, "explanation": "Infosys is headquartered in Bangalore, Karnataka."},
    {"stem": "What is Infosys's famous training center called?", "options": ["Mysore Campus", "Bangalore Academy", "Hyderabad Center", "Chennai Institute"], "correct_index": 0, "explanation": "Infosys's famous training center is the Mysore Campus."},
    {"stem": "Which of these is an Infosys product?", "options": ["iON", "Infosys Nia", "Wingspan", "EdgeVerve"], "correct_index": 1, "explanation": "Infosys Nia is an AI platform by Infosys."},
    {"stem": "Infosys was incorporated in which year?", "options": ["1975", "1981", "1990", "1995"], "correct_index": 1, "explanation": "Infosys was incorporated in 1981."},
    {"stem": "What is the first Indian company listed on NASDAQ?", "options": ["TCS", "Wipro", "Infosys", "HCL"], "correct_index": 2, "explanation": "Infosys was the first Indian company to be listed on NASDAQ."},
    {"stem": "Infosys has a platform called 'EdgeVerve'. What does it do?", "options": ["Cloud computing", "Enterprise software solutions", "Hardware manufacturing", "Social media"], "correct_index": 1, "explanation": "EdgeVerve provides enterprise software solutions."},
    {"stem": "Infosys Foundation focuses on:", "options": ["Only education", "Education, healthcare, rural development", "Only healthcare", "Only technology"], "correct_index": 1, "explanation": "Infosys Foundation focuses on education, healthcare, and rural development."},
    {"stem": "Infosys employs approximately how many people?", "options": ["50,000", "100,000", "250,000", "500,000"], "correct_index": 2, "explanation": "Infosys employs approximately 250,000+ people worldwide."},
    {"stem": "What is Infosys's learning platform called?", "options": ["Ultimatix", "Lex", "iLearn", "MyEureka"], "correct_index": 1, "explanation": "Lex is Infosys's continuous learning platform."},
]

WIPRO_QUESTIONS = [
    {"stem": "Wipro was founded by:", "options": ["N. R. Narayana Murthy", "Azim Premji", "Kumar Mangalam Birla", "Ratan Tata"], "correct_index": 1, "explanation": "Wipro was founded by Azim Premji."},
    {"stem": "Wipro's headquarters is in:", "options": ["Mumbai", "Bangalore", "Hyderabad", "Chennai"], "correct_index": 1, "explanation": "Wipro is headquartered in Bangalore, Karnataka."},
    {"stem": "Wipro is known for which sector?", "options": ["Only IT services", "IT, consulting, and business process services", "Only manufacturing", "Only healthcare"], "correct_index": 1, "explanation": "Wipro operates in IT, consulting, and business process services."},
    {"stem": "Wipro was originally a company making:", "options": ["Software", "Vegetable oil", "Computers", "Mobile phones"], "correct_index": 1, "explanation": "Wipro originally started as a vegetable oil company."},
    {"stem": "Wipro's tagline is:", "options": ["Think Big, Think Fast", "Applying Thought", "Innovation for All", "Building the Future"], "correct_index": 1, "explanation": "Wipro's tagline is 'Applying Thought'."},
    {"stem": "Wipro operates in approximately how many countries?", "options": ["20", "35", "50", "70"], "correct_index": 1, "explanation": "Wipro operates in approximately 35+ countries."},
    {"stem": "Wipro's annual revenue is approximately:", "options": ["$5 billion", "$10 billion", "$20 billion", "$50 billion"], "correct_index": 1, "explanation": "Wipro's annual revenue is approximately $10+ billion."},
    {"stem": "Wipro's main competitors include:", "options": ["Only TCS", "TCS, Infosys, HCL", "Only Google", "Only Microsoft"], "correct_index": 1, "explanation": "Wipro's main competitors include TCS, Infosys, and HCL."},
    {"stem": "Wipro's full name is:", "options": ["Western India Palm Refined Oils", "Worldwide Integrated Products", "Wipro Products Limited", "Wipro International"], "correct_index": 0, "explanation": "Wipro stands for Western India Palm Refined Oils."},
    {"stem": "What is Wipro's AI platform called?", "options": ["BaNCS", "HOLMES", "Nia", "Cloud First"], "correct_index": 1, "explanation": "Wipro HOLMES is Wipro's AI platform."},
]

ACCENTURE_QUESTIONS = [
    {"stem": "Accenture is headquartered in:", "options": ["New York", "Dublin, Ireland", "London", "Bangalore"], "correct_index": 1, "explanation": "Accenture is headquartered in Dublin, Ireland."},
    {"stem": "Accenture was originally part of which company?", "options": ["IBM", "Andersen Consulting", "Deloitte", "KPMG"], "correct_index": 1, "explanation": "Accenture was formerly known as Andersen Consulting."},
    {"stem": "Accenture's stock ticker symbol is:", "options": ["ACN", "ACC", "ACNT", "ASC"], "correct_index": 0, "explanation": "Accenture trades on NYSE under the ticker ACN."},
    {"stem": "Accenture operates in approximately how many countries?", "options": ["50", "100", "120+", "200"], "correct_index": 2, "explanation": "Accenture operates in more than 120 countries."},
    {"stem": "Accenture's consulting services include:", "options": ["Only IT consulting", "Strategy, Consulting, Digital, Technology, Operations", "Only management consulting", "Only outsourcing"], "correct_index": 1, "explanation": "Accenture offers Strategy, Consulting, Digital, Technology, and Operations services."},
    {"stem": "Accenture was renamed from Andersen Consulting in which year?", "options": ["1995", "2000", "2001", "2005"], "correct_index": 2, "explanation": "Andersen Consulting was renamed to Accenture in 2001."},
    {"stem": "Accenture's hiring process typically includes:", "options": ["Only interview", "Online test, interview rounds, and HR", "Only aptitude test", "Group discussion only"], "correct_index": 1, "explanation": "Accenture recruitment typically includes online test, interview rounds, and HR."},
    {"stem": "Accenture employs approximately how many people?", "options": ["200,000", "400,000", "600,000+", "800,000"], "correct_index": 2, "explanation": "Accenture employs approximately 600,000+ people worldwide."},
    {"stem": "What is Accenture's approach to innovation called?", "options": ["Innovation Hub", "Accenture Innovation Architecture", "Tech Lab", "Digital Factory"], "correct_index": 1, "explanation": "Accenture's innovation approach is called the Innovation Architecture."},
    {"stem": "What is Accenture Cloud First?", "options": ["A cloud platform", "Cloud adoption service", "A training program", "A consulting method"], "correct_index": 1, "explanation": "Cloud First helps enterprises accelerate cloud adoption."},
]

COGNIZANT_QUESTIONS = [
    {"stem": "Cognizant is headquartered in:", "options": ["Mumbai", "Teaneck, New Jersey, USA", "Chennai", "Hyderabad"], "correct_index": 1, "explanation": "Cognizant is headquartered in Teaneck, New Jersey, USA."},
    {"stem": "Cognizant was founded in which year?", "options": ["1990", "1994", "2000", "2005"], "correct_index": 1, "explanation": "Cognizant was founded in 1994."},
    {"stem": "Cognizant's primary focus is on:", "options": ["Hardware manufacturing", "IT services and consulting", "Software products", "Telecom services"], "correct_index": 1, "explanation": "Cognizant focuses on IT services and consulting."},
    {"stem": "Cognizant was originally a subsidiary of:", "options": ["TCS", "Dun & Bradstreet", "Infosys", "Wipro"], "correct_index": 1, "explanation": "Cognizant was originally a subsidiary of Dun & Bradstreet."},
    {"stem": "Cognizant operates in approximately how many countries?", "options": ["20", "35", "50+", "80"], "correct_index": 2, "explanation": "Cognizant operates in more than 50 countries."},
    {"stem": "Cognizant's stock trades on which exchange?", "options": ["NYSE", "NASDAQ", "BSE", "LSE"], "correct_index": 1, "explanation": "Cognizant trades on NASDAQ under the ticker CTSH."},
    {"stem": "Cognizant employs approximately how many people?", "options": ["100,000", "200,000", "300,000+", "500,000"], "correct_index": 2, "explanation": "Cognizant employs approximately 300,000+ people worldwide."},
    {"stem": "Cognizant's main service areas include:", "options": ["Only IT support", "Digital, Technology, Consulting, Operations", "Only software development", "Only BPO"], "correct_index": 1, "explanation": "Cognizant offers Digital, Technology, Consulting, and Operations services."},
    {"stem": "What is Cognizant's approach to digital transformation?", "options": ["Traditional IT only", "Edge Concentration strategy", "Outsourcing only", "Hardware focus"], "correct_index": 1, "explanation": "Cognizant uses an Edge Concentration strategy."},
    {"stem": "What is Cognizant's delivery model called?", "options": ["Traditional waterfall", "Squads and Pods", "Remote only", "Fixed teams"], "correct_index": 1, "explanation": "Cognizant uses the Squads and Pods model."},
]

HCL_QUESTIONS = [
    {"stem": "HCL Technologies was founded in:", "options": ["1970", "1976", "1985", "1990"], "correct_index": 1, "explanation": "HCL was founded in 1976."},
    {"stem": "HCL Technologies is headquartered in:", "options": ["Bangalore", "Noida, India", "Mumbai", "Chennai"], "correct_index": 1, "explanation": "HCL is headquartered in Noida, India."},
    {"stem": "HCL's strategy is called:", "options": ["Mode 1-2-3", "Digital First", "Cloud Ready", "Innovation Hub"], "correct_index": 0, "explanation": "HCL uses the 'Mode 1-2-3' strategy."},
    {"stem": "HCL operates in approximately how many countries?", "options": ["30", "40", "52", "65"], "correct_index": 2, "explanation": "HCL operates in 52 countries."},
    {"stem": "HCL employs approximately how many people?", "options": ["150,000", "175,000", "225,000+", "300,000"], "correct_index": 2, "explanation": "HCL has 225,000+ employees."},
    {"stem": "What is HCL's innovation platform called?", "options": ["Innovation Hub", "MyEureka", "IdeaStream", "ThinkTank"], "correct_index": 1, "explanation": "MyEureka is HCL's innovation platform."},
    {"stem": "HCL's Digital Foundation platform enables:", "options": ["Only cloud computing", "Cloud-native transformation", "Only data analytics", "Only cybersecurity"], "correct_index": 1, "explanation": "Digital Foundation enables cloud-native transformation."},
    {"stem": "HCL is known for its:", "options": ["Hardware products", "Employee-first culture", "Only software", "Only consulting"], "correct_index": 1, "explanation": "HCL is known for its employee-first culture."},
    {"stem": "What was HCL's approximate annual revenue?", "options": ["$5 billion", "$8 billion", "$12 billion+", "$20 billion"], "correct_index": 2, "explanation": "HCL's revenue exceeded $12 billion."},
    {"stem": "HCL's core areas include:", "options": ["Only IT services", "IT services, engineering, and R&D", "Only manufacturing", "Only consulting"], "correct_index": 1, "explanation": "HCL covers IT services, engineering, and R&D."},
]

CAPGEMINI_QUESTIONS = [
    {"stem": "Capgemini was founded in:", "options": ["1960", "1967", "1975", "1980"], "correct_index": 1, "explanation": "Capgemini was founded in 1967."},
    {"stem": "Capgemini is headquartered in:", "options": ["London", "Paris, France", "New York", "Berlin"], "correct_index": 1, "explanation": "Capgemini is headquartered in Paris, France."},
    {"stem": "Capgemini operates in approximately how many countries?", "options": ["30", "40", "50+", "70"], "correct_index": 2, "explanation": "Capgemini operates in 50+ countries."},
    {"stem": "Capgemini employs approximately how many people?", "options": ["200,000", "275,000", "350,000", "500,000"], "correct_index": 2, "explanation": "Capgemini has 350,000 employees."},
    {"stem": "What company did Capgemini acquire in 2020?", "options": ["Accenture", "Altran", "Deloitte", "McKinsey"], "correct_index": 1, "explanation": "Capgemini acquired Altran in 2020."},
    {"stem": "Capgemini's strategy is called:", "options": ["Cloud First", "Connected Platform", "Digital Hub", "Innovation Path"], "correct_index": 1, "explanation": "Capgemini uses the Connected Platform strategy."},
    {"stem": "Capgemini's innovation division is called:", "options": ["Labs", "Invent", "Studio", "Hub"], "correct_index": 1, "explanation": "Capgemini Invent focuses on innovation and consulting."},
    {"stem": "Capgemini's annual revenue exceeds:", "options": ["€10 billion", "€15 billion", "€22 billion", "€30 billion"], "correct_index": 2, "explanation": "Revenue exceeds €22 billion."},
    {"stem": "Capgemini's core service areas include:", "options": ["Only consulting", "Consulting, technology, and digital transformation", "Only technology", "Only outsourcing"], "correct_index": 1, "explanation": "Capgemini covers consulting, technology, and digital transformation."},
    {"stem": "Capgemini's Connected Platform integrates:", "options": ["Only cloud", "Cloud, data, AI, and cybersecurity", "Only AI", "Only security"], "correct_index": 1, "explanation": "Connected Platform integrates cloud, data, AI, and cybersecurity."},
]


# =========================================================================
# GENERAL READING PASSAGES
# =========================================================================

GENERAL_READING_PASSAGES = [
    {"title": "The History of Coffee", "body": "Coffee is one of the world's most popular beverages. It originated in Ethiopia, where legend has it that a goat herder named Kaldi noticed his goats became energetic after eating berries from a certain bush. He brought these berries to a monastery, where the abbot made a drink that kept him awake during long hours of prayer. Coffee spread to the Arab world, where coffee houses became centers of social activity and intellectual exchange. By the 17th century, coffee had reached Europe, where it quickly became popular. Today, coffee is grown in over 70 countries and is a major global commodity.", "kind": "general", "questions": [
        {"stem": "Where did coffee originate?", "options": ["Arabia", "Ethiopia", "Europe", "Colombia"], "correct_index": 1, "explanation": "The passage states coffee originated in Ethiopia."},
        {"stem": "What did Kaldi notice about his goats?", "options": ["They became sleepy", "They became energetic", "They stopped eating", "They ran away"], "correct_index": 1, "explanation": "Kaldi noticed his goats became energetic."},
        {"stem": "What did the abbot do with the berries?", "options": ["Planted them", "Made a drink", "Sold them", "Threw them away"], "correct_index": 1, "explanation": "The abbot made a drink from the berries."},
        {"stem": "When did coffee reach Europe?", "options": ["15th century", "16th century", "17th century", "18th century"], "correct_index": 2, "explanation": "Coffee reached Europe by the 17th century."},
        {"stem": "How many countries grow coffee today?", "options": ["Over 50", "Over 70", "Over 100", "Over 120"], "correct_index": 1, "explanation": "Coffee is grown in over 70 countries."},
    ]},
    {"title": "Climate Change and Agriculture", "body": "Climate change poses significant threats to global agriculture. Rising temperatures, changing precipitation patterns, and increased frequency of extreme weather events all affect crop yields. Scientists predict that by 2050, global crop yields could decline by 25% due to climate change. However, new technologies and farming practices offer hope. Precision agriculture, drought-resistant crops, and sustainable farming methods can help farmers adapt. International cooperation and investment in agricultural research are essential for ensuring food security in a changing climate.", "kind": "general", "questions": [
        {"stem": "What threatens global agriculture?", "options": ["New technologies", "Climate change", "Government policies", "Population growth"], "correct_index": 1, "explanation": "Climate change poses significant threats."},
        {"stem": "By how much could crop yields decline by 2050?", "options": ["10%", "15%", "25%", "50%"], "correct_index": 2, "explanation": "Scientists predict a 25% decline."},
        {"stem": "Which is mentioned as a solution?", "options": ["More pesticides", "Precision agriculture", "Less farming", "Importing food"], "correct_index": 1, "explanation": "Precision agriculture is mentioned as a solution."},
        {"stem": "What is essential for food security?", "options": ["More land", "International cooperation", "Higher prices", "Fewer farmers"], "correct_index": 1, "explanation": "International cooperation is essential."},
        {"stem": "What affects crop yields?", "options": ["Only temperature", "Only rainfall", "Rising temperatures, precipitation changes, and extreme weather", "Only soil quality"], "correct_index": 2, "explanation": "Multiple factors affect crop yields."},
    ]},
    {"title": "The Benefits of Reading", "body": "Reading is one of the most beneficial activities for the human brain. Studies show that reading regularly improves cognitive function, reduces stress, and increases empathy. Children who read for pleasure perform better academically than those who don't. Reading also helps preserve mental function as we age, potentially reducing the risk of Alzheimer's disease. Furthermore, reading exposes us to new ideas, cultures, and perspectives, broadening our understanding of the world. In an age of digital distractions, cultivating a reading habit has never been more important.", "kind": "general", "questions": [
        {"stem": "What does regular reading improve?", "options": ["Only memory", "Cognitive function, reduces stress, and increases empathy", "Only physical health", "Only social skills"], "correct_index": 1, "explanation": "Reading improves cognitive function, reduces stress, and increases empathy."},
        {"stem": "How do children who read for pleasure perform?", "options": ["Worse academically", "Better academically", "Same as others", "They don't perform well"], "correct_index": 1, "explanation": "Children who read perform better academically."},
        {"stem": "What disease might reading help reduce the risk of?", "options": ["Cancer", "Alzheimer's disease", "Diabetes", "Heart disease"], "correct_index": 1, "explanation": "Reading may reduce the risk of Alzheimer's."},
        {"stem": "What does reading expose us to?", "options": ["Only fiction", "New ideas, cultures, and perspectives", "Only history", "Only science"], "correct_index": 1, "explanation": "Reading exposes us to new ideas and perspectives."},
        {"stem": "Why is reading more important now?", "options": ["Books are cheaper", "Digital distractions make it harder to focus", "There are more libraries", "Reading is required by law"], "correct_index": 1, "explanation": "Digital distractions make reading more important."},
    ]},
    {"title": "Artificial Intelligence in Healthcare", "body": "Artificial intelligence is transforming healthcare in remarkable ways. AI algorithms can now analyze medical images with accuracy comparable to experienced radiologists. Machine learning models help predict patient outcomes and identify those at risk of developing certain conditions. AI-powered chatbots provide 24/7 health information and triage. Drug discovery has been accelerated by AI, reducing the time to identify promising compounds. However, challenges remain, including data privacy concerns, algorithmic bias, and the need for human oversight. The future of healthcare will likely involve a partnership between human clinicians and AI systems.", "kind": "general", "questions": [
        {"stem": "How does AI perform in analyzing medical images?", "options": ["Worse than radiologists", "Comparable to experienced radiologists", "Better than all doctors", "Cannot analyze images yet"], "correct_index": 1, "explanation": "AI can analyze images with accuracy comparable to radiologists."},
        {"stem": "What do AI-powered chatbots provide?", "options": ["Surgery", "24/7 health information and triage", "Medication", "Physical therapy"], "correct_index": 1, "explanation": "AI chatbots provide 24/7 health information."},
        {"stem": "What challenge does AI face in healthcare?", "options": ["Too fast processing", "Data privacy concerns", "Not enough data", "Too cheap to implement"], "correct_index": 1, "explanation": "Data privacy is a key challenge."},
        {"stem": "How has AI affected drug discovery?", "options": ["Slowed it down", "Accelerated it", "Had no effect", "Made it more expensive"], "correct_index": 1, "explanation": "AI has accelerated drug discovery."},
        {"stem": "What does the future of healthcare involve?", "options": ["Only AI", "Only human doctors", "Partnership between clinicians and AI", "No technology"], "correct_index": 2, "explanation": "The future involves partnership between clinicians and AI."},
    ]},
    {"title": "Space Exploration", "body": "Space exploration has captivated humanity for centuries. From the first satellites in the 1950s to the moon landings and beyond, our quest to understand the cosmos continues to push boundaries. Today, private companies like SpaceX and Blue Origin are making space more accessible. The International Space Station serves as a laboratory for scientific research. Mars colonization is being actively planned. Space technology has also led to numerous everyday innovations, from memory foam to water purification systems. As we look to the stars, space exploration inspires innovation and expands our understanding of our place in the universe.", "kind": "general", "questions": [
        {"stem": "When were the first satellites launched?", "options": ["1940s", "1950s", "1960s", "1970s"], "correct_index": 1, "explanation": "First satellites were in the 1950s."},
        {"stem": "Which private companies are mentioned?", "options": ["Google and Apple", "SpaceX and Blue Origin", "Tesla and Amazon", "Microsoft and Facebook"], "correct_index": 1, "explanation": "SpaceX and Blue Origin are mentioned."},
        {"stem": "What serves as a space laboratory?", "options": ["Space Shuttle", "International Space Station", "Mars", "Moon"], "correct_index": 1, "explanation": "The ISS serves as a laboratory."},
        {"stem": "What is being planned for Mars?", "options": ["Mining", "Colonization", "Tourism only", "Nothing"], "correct_index": 1, "explanation": "Mars colonization is being planned."},
        {"stem": "Name an everyday innovation from space:", "options": ["Smartphones", "Memory foam", "Social media", "Electric cars"], "correct_index": 1, "explanation": "Memory foam came from space technology."},
    ]},
    {"title": "The Importance of Water Conservation", "body": "Water is essential for life, yet it is a finite resource. Only 3% of Earth's water is freshwater, and less than 1% is easily accessible. With growing populations and industrial demand, water scarcity is becoming a global crisis. Agriculture accounts for 70% of freshwater use worldwide. Simple conservation measures like fixing leaks, using efficient irrigation, and recycling water can make a significant difference. Governments and communities must work together to protect this precious resource for future generations.", "kind": "general", "questions": [
        {"stem": "What percentage of Earth's water is freshwater?", "options": ["1%", "3%", "10%", "30%"], "correct_index": 1, "explanation": "Only 3% is freshwater."},
        {"stem": "What uses the most freshwater?", "options": ["Industry", "Agriculture", "Households", "Transportation"], "correct_index": 1, "explanation": "Agriculture accounts for 70%."},
        {"stem": "How much freshwater is easily accessible?", "options": ["Less than 1%", "About 10%", "About 50%", "About 90%"], "correct_index": 0, "explanation": "Less than 1% is easily accessible."},
        {"stem": "Which is NOT mentioned as a conservation measure?", "options": ["Fixing leaks", "Building dams", "Efficient irrigation", "Recycling water"], "correct_index": 1, "explanation": "Building dams is not mentioned."},
        {"stem": "Why is water conservation important?", "options": ["It's free", "Water is a finite resource", "It tastes good", "It's fun"], "correct_index": 1, "explanation": "Water is a finite resource."},
    ]},
    {"title": "The Digital Revolution", "body": "The digital revolution has transformed every aspect of modern life. From communication to commerce, education to entertainment, digital technology has created new opportunities and challenges. The internet connects billions of people worldwide. Social media has changed how we interact. Online shopping has revolutionized retail. E-learning has made education more accessible. However, the digital divide remains a concern, with many communities lacking access to technology. Cybersecurity threats are also increasing. As we navigate this digital age, balancing innovation with responsibility is crucial.", "kind": "general", "questions": [
        {"stem": "What has the digital revolution transformed?", "options": ["Only communication", "Every aspect of modern life", "Only commerce", "Only entertainment"], "correct_index": 1, "explanation": "It has transformed every aspect of modern life."},
        {"stem": "What connects billions of people?", "options": ["Television", "The internet", "Radio", "Newspapers"], "correct_index": 1, "explanation": "The internet connects billions."},
        {"stem": "What is the 'digital divide'?", "options": ["Different screen sizes", "Lack of access to technology", "Too much technology", "Old technology"], "correct_index": 1, "explanation": "It refers to lack of access to technology."},
        {"stem": "How has e-learning affected education?", "options": ["Made it harder", "Made it more accessible", "Made it more expensive", "No effect"], "correct_index": 1, "explanation": "E-learning has made education more accessible."},
        {"stem": "What is crucial in the digital age?", "options": ["Using more technology", "Balancing innovation with responsibility", "Ignoring technology", "Copying others"], "correct_index": 1, "explanation": "Balancing innovation with responsibility is crucial."},
    ]},
    {"title": "Renewable Energy Sources", "body": "Renewable energy is key to a sustainable future. Solar, wind, and hydroelectric power are leading the transition away from fossil fuels. Solar energy has become increasingly affordable, with costs dropping 90% since 2010. Wind farms generate electricity without emissions. Geothermal energy taps into the Earth's heat. Battery storage technology is improving, solving the intermittency problem. Governments worldwide are setting ambitious renewable energy targets. While challenges remain, the transition to clean energy is accelerating rapidly.", "kind": "general", "questions": [
        {"stem": "How much have solar costs dropped since 2010?", "options": ["10%", "50%", "90%", "99%"], "correct_index": 2, "explanation": "Solar costs have dropped 90%."},
        {"stem": "What is a benefit of wind farms?", "options": ["They're cheap", "They generate electricity without emissions", "They work everywhere", "They're silent"], "correct_index": 1, "explanation": "Wind farms generate electricity without emissions."},
        {"stem": "What does geothermal energy tap into?", "options": ["Wind", "The Earth's heat", "Solar radiation", "Ocean waves"], "correct_index": 1, "explanation": "Geothermal energy uses the Earth's heat."},
        {"stem": "What solves the intermittency problem?", "options": ["More solar panels", "Battery storage technology", "More wind farms", "Government subsidies"], "correct_index": 1, "explanation": "Battery storage solves intermittency."},
        {"stem": "What is the transition to clean energy doing?", "options": ["Slowing down", "Accelerating rapidly", "Stopping", "Hasn't started"], "correct_index": 1, "explanation": "The transition is accelerating rapidly."},
    ]},
    {"title": "Mental Health in the Workplace", "body": "Workplace mental health is increasingly recognized as essential for employee wellbeing and organizational success. Stress, burnout, and anxiety are common challenges faced by workers. Companies that invest in mental health programs see reduced absenteeism, higher productivity, and lower turnover. Flexible work arrangements, employee assistance programs, and open conversations about mental health are effective strategies. Leaders play a crucial role in creating supportive cultures. Addressing mental health is not just the right thing to do—it's also good business.", "kind": "general", "questions": [
        {"stem": "What are common workplace mental health challenges?", "options": ["Only stress", "Stress, burnout, and anxiety", "Only depression", "Only loneliness"], "correct_index": 1, "explanation": "Stress, burnout, and anxiety are common."},
        {"stem": "What do companies with mental health programs see?", "options": ["Higher costs", "Reduced absenteeism and higher productivity", "More sick days", "Lower productivity"], "correct_index": 1, "explanation": "They see reduced absenteeism and higher productivity."},
        {"stem": "What is an effective strategy?", "options": ["Longer hours", "Flexible work arrangements", "Less pay", "More meetings"], "correct_index": 1, "explanation": "Flexible work arrangements are effective."},
        {"stem": "What role do leaders play?", "options": ["No role", "Creating supportive cultures", "Only making rules", "Only hiring"], "correct_index": 1, "explanation": "Leaders create supportive cultures."},
        {"stem": "Why address mental health?", "options": ["Only because required", "It's good business and the right thing to do", "Only to avoid lawsuits", "No reason"], "correct_index": 1, "explanation": "It's both good business and the right thing."},
    ]},
    {"title": "Ocean Biodiversity", "body": "The world's oceans are home to an incredible diversity of life. From microscopic plankton to massive blue whales, marine ecosystems support millions of species. Coral reefs, often called the 'rainforests of the sea,' support 25% of all marine life. However, ocean biodiversity is under threat from pollution, overfishing, and climate change. Rising ocean temperatures are causing coral bleaching. Plastic pollution affects marine animals at every level. Protecting ocean biodiversity requires international cooperation and sustainable practices. Healthy oceans are essential for regulating climate, producing oxygen, and providing food for billions of people.", "kind": "general", "questions": [
        {"stem": "What do coral reefs support?", "options": ["10% of marine life", "25% of marine life", "50% of marine life", "75% of marine life"], "correct_index": 1, "explanation": "Coral reefs support 25% of marine life."},
        {"stem": "What are coral reefs called?", "options": ["Gardens of the sea", "Rainforests of the sea", "Libraries of the sea", "Museums of the sea"], "correct_index": 1, "explanation": "They're called the rainforests of the sea."},
        {"stem": "What causes coral bleaching?", "options": ["Pollution only", "Rising ocean temperatures", "Overfishing only", "Plastic only"], "correct_index": 1, "explanation": "Rising temperatures cause coral bleaching."},
        {"stem": "What do healthy oceans help regulate?", "options": ["Only weather", "Climate, produce oxygen, and provide food", "Only tides", "Only currents"], "correct_index": 1, "explanation": "Healthy oceans regulate climate, produce oxygen, and provide food."},
        {"stem": "What is needed to protect ocean biodiversity?", "options": ["More fishing", "International cooperation and sustainable practices", "More boats", "More research only"], "correct_index": 1, "explanation": "International cooperation and sustainable practices are needed."},
    ]},
]


# =========================================================================
# COMPANY READING PASSAGES
# =========================================================================

COMPANY_READING_PASSAGES = {
    "TCS": [{"title": "TCS Digital Transformation", "body": "Tata Consultancy Services (TCS) has been at the forefront of digital transformation. Their digitalQuotient framework helps enterprises accelerate digital adoption. TCS invested $2 billion in R&D through TCS Research and Innovation labs. Their platform, TCS BaNCS, serves over 500 million customers globally. TCS iON provides cloud-based solutions for education and manufacturing. With over 600,000 employees, TCS is one of the largest IT services companies in the world.", "kind": "TCS", "questions": [
        {"stem": "How much did TCS invest in R&D?", "options": ["$1 billion", "$1.5 billion", "$2 billion", "$3 billion"], "correct_index": 2, "explanation": "TCS invested $2 billion in R&D."},
        {"stem": "What is TCS BaNCS?", "options": ["A software product", "A banking platform", "A training center", "A research lab"], "correct_index": 1, "explanation": "TCS BaNCS is a banking platform."},
        {"stem": "How many customers does TCS BaNCS serve?", "options": ["100 million", "300 million", "500 million", "1 billion"], "correct_index": 2, "explanation": "It serves over 500 million customers."},
        {"stem": "What is TCS iON?", "options": ["A cloud platform", "A mobile app", "A hardware product", "A consulting service"], "correct_index": 0, "explanation": "TCS iON is a cloud-based platform."},
        {"stem": "How many employees does TCS have?", "options": ["400,000", "500,000", "600,000+", "800,000"], "correct_index": 2, "explanation": "TCS has over 600,000 employees."},
    ]}],
    "Infosys": [{"title": "Infosys Innovation", "body": "Infosys has established itself as a leader in technology innovation. Their flagship product, Infosys Nia, is an AI platform that helps enterprises automate processes. Infosys has 23 innovation hubs worldwide. Their Lex platform provides continuous learning opportunities for employees. Infosys Finacle is a leading banking software used by banks in over 100 countries. The company's revenue exceeded $18 billion in recent years.", "kind": "Infosys", "questions": [
        {"stem": "What is Infosys Nia?", "options": ["A cloud platform", "An AI platform", "A mobile app", "A database"], "correct_index": 1, "explanation": "Infosys Nia is an AI platform."},
        {"stem": "How many innovation hubs does Infosys have?", "options": ["10", "15", "23", "30"], "correct_index": 2, "explanation": "Infosys has 23 innovation hubs."},
        {"stem": "What is Infosys Lex?", "options": ["A training platform", "Banking software", "A cloud service", "A hardware product"], "correct_index": 0, "explanation": "Lex is a continuous learning platform."},
        {"stem": "What is Infosys Finacle?", "options": ["An AI tool", "Banking software", "A mobile app", "A database"], "correct_index": 1, "explanation": "Finacle is banking software."},
        {"stem": "In how many countries is Finacle used?", "options": ["50", "75", "100+", "150"], "correct_index": 2, "explanation": "Finacle is used in over 100 countries."},
    ]}],
    "Wipro": [{"title": "Wipro's Digital Strategy", "body": "Wipro has transformed from a vegetable oil company to a global IT leader. Their Wipro HOLMES AI platform powers automation across industries. Wipro's FullStride Cloud Services help enterprises migrate to the cloud. The company operates in 66 countries with 250,000+ employees. Wipro's focus on sustainability includes their 'Spirit of Wipro' values. Their annual revenue is approximately $11 billion.", "kind": "Wipro", "questions": [
        {"stem": "What was Wipro originally?", "options": ["A tech company", "A vegetable oil company", "A bank", "A hospital"], "correct_index": 1, "explanation": "Wipro started as a vegetable oil company."},
        {"stem": "What is Wipro HOLMES?", "options": ["A cloud platform", "An AI platform", "A database", "A mobile app"], "correct_index": 1, "explanation": "Wipro HOLMES is an AI platform."},
        {"stem": "How many countries does Wipro operate in?", "options": ["30", "45", "66", "80"], "correct_index": 2, "explanation": "Wipro operates in 66 countries."},
        {"stem": "What is Wipro's annual revenue?", "options": ["$5 billion", "$8 billion", "$11 billion", "$15 billion"], "correct_index": 2, "explanation": "Wipro's annual revenue is approximately $11 billion."},
        {"stem": "How many employees does Wipro have?", "options": ["100,000", "150,000", "250,000+", "350,000"], "correct_index": 2, "explanation": "Wipro has 250,000+ employees."},
    ]}],
    "Accenture": [{"title": "Accenture's Innovation Architecture", "body": "Accenture's Innovation Architecture consists of a network of innovation hubs, labs, and studios worldwide. They have invested over $3 billion in acquisitions to boost digital capabilities. Accenture Cloud First helps enterprises accelerate cloud adoption. Their Cloudadium platform manages over $2 billion in cloud spend. Accenture operates in 120+ countries with 738,000 employees. Revenue exceeded $64 billion, with digital, cloud, and security services growing fastest.", "kind": "Accenture", "questions": [
        {"stem": "How much has Accenture invested in acquisitions?", "options": ["$1 billion", "$2 billion", "$3 billion", "$5 billion"], "correct_index": 2, "explanation": "Accenture invested over $3 billion."},
        {"stem": "What is Accenture Cloud First?", "options": ["A cloud platform", "Cloud adoption service", "A training program", "A consulting method"], "correct_index": 1, "explanation": "Cloud First helps enterprises accelerate cloud adoption."},
        {"stem": "How much cloud spend does Cloudadium manage?", "options": ["$500 million", "$1 billion", "$2 billion", "$5 billion"], "correct_index": 2, "explanation": "Cloudadium manages over $2 billion in cloud spend."},
        {"stem": "How many employees does Accenture have?", "options": ["500,000", "600,000", "738,000", "900,000"], "correct_index": 2, "explanation": "Accenture has 738,000 employees."},
        {"stem": "What was Accenture's revenue?", "options": ["$40 billion", "$50 billion", "$64 billion+", "$80 billion"], "correct_index": 2, "explanation": "Revenue exceeded $64 billion."},
    ]}],
    "Cognizant": [{"title": "Cognizant's Digital Growth", "body": "Cognizant has grown rapidly through its focus on digital transformation. Their Squads and Pods model provides agile delivery teams. Cognizant acquired six companies in 2023 to strengthen digital capabilities. They operate in 40+ countries with 350,000+ employees. Revenue reached $19.4 billion. Their core areas include digital engineering, cloud, data and AI, and cybersecurity.", "kind": "Cognizant", "questions": [
        {"stem": "What is Cognizant's delivery model?", "options": ["Traditional waterfall", "Squads and Pods", "Remote only", "Fixed teams"], "correct_index": 1, "explanation": "Cognizant uses the Squads and Pods model."},
        {"stem": "How many companies did Cognizant acquire in 2023?", "options": ["2", "4", "6", "8"], "correct_index": 2, "explanation": "Cognizant acquired 6 companies."},
        {"stem": "In how many countries does Cognizant operate?", "options": ["20", "30", "40+", "60"], "correct_index": 2, "explanation": "Cognizant operates in 40+ countries."},
        {"stem": "What was Cognizant's revenue?", "options": ["$10 billion", "$15 billion", "$19.4 billion", "$25 billion"], "correct_index": 2, "explanation": "Revenue reached $19.4 billion."},
        {"stem": "How many employees does Cognizant have?", "options": ["200,000", "280,000", "350,000+", "500,000"], "correct_index": 2, "explanation": "Cognizant has 350,000+ employees."},
    ]}],
    "HCL": [{"title": "HCL Technologies Overview", "body": "HCL Technologies is a leading global IT services company headquartered in Noida, India. Founded in 1976, HCL has grown to operate in 52 countries with 225,000+ employees. Their 'Mode 1-2-3' strategy focuses on core services, products and platforms, and ecosystem partnerships. HCL's Digital Foundation platform enables cloud-native transformation. Revenue exceeded $12 billion. HCL is known for its employee-first culture and innovative 'MyEureka' ideas platform.", "kind": "HCL", "questions": [
        {"stem": "When was HCL founded?", "options": ["1970", "1976", "1985", "1990"], "correct_index": 1, "explanation": "HCL was founded in 1976."},
        {"stem": "In how many countries does HCL operate?", "options": ["30", "40", "52", "65"], "correct_index": 2, "explanation": "HCL operates in 52 countries."},
        {"stem": "How many employees does HCL have?", "options": ["150,000", "175,000", "225,000+", "300,000"], "correct_index": 2, "explanation": "HCL has 225,000+ employees."},
        {"stem": "What is HCL's strategy called?", "options": ["Mode 1-2-3", "Digital First", "Cloud Ready", "Innovation Hub"], "correct_index": 0, "explanation": "HCL uses the 'Mode 1-2-3' strategy."},
        {"stem": "What was HCL's revenue?", "options": ["$8 billion", "$10 billion", "$12 billion+", "$15 billion"], "correct_index": 2, "explanation": "Revenue exceeded $12 billion."},
    ]}],
    "Capgemini": [{"title": "Capgemini's Consulting Excellence", "body": "Capgemini is a global leader in consulting, technology services, and digital transformation. Founded in 1967, they operate in 50+ countries with 350,000 employees. Their annual revenue exceeds €22 billion. Capgemini's 'Connected Platform' strategy integrates cloud, data, AI, and cybersecurity. They acquired Altran in 2020 for engineering services. Capgemini is known for its Invent division that focuses on innovation and creative solutions.", "kind": "Capgemini", "questions": [
        {"stem": "When was Capgemini founded?", "options": ["1960", "1967", "1975", "1980"], "correct_index": 1, "explanation": "Capgemini was founded in 1967."},
        {"stem": "In how many countries does Capgemini operate?", "options": ["30", "40", "50+", "70"], "correct_index": 2, "explanation": "Capgemini operates in 50+ countries."},
        {"stem": "How many employees does Capgemini have?", "options": ["200,000", "275,000", "350,000", "500,000"], "correct_index": 2, "explanation": "Capgemini has 350,000 employees."},
        {"stem": "What was Capgemini's revenue?", "options": ["€15 billion", "€18 billion", "€22 billion+", "€30 billion"], "correct_index": 2, "explanation": "Revenue exceeds €22 billion."},
        {"stem": "What company did Capgemini acquire in 2020?", "options": ["Accenture", "Altran", "Deloitte", "McKinsey"], "correct_index": 1, "explanation": "Capgemini acquired Altran in 2020."},
    ]}],
}


# =========================================================================
# GENERAL LISTENING PASSAGES
# =========================================================================

GENERAL_LISTENING_PASSAGES = [
    {"title": "Daily Commute Conversation", "transcript": "A: Good morning! How was your commute today?\nB: It was terrible. The train was delayed by 20 minutes.\nA: Oh no, that's frustrating. Was there a specific reason?\nB: There was a signal failure at the central station. They said it was being fixed.\nA: I usually take the bus. It's slower but more reliable.\nB: Maybe I should try the bus too. How long does it take?\nA: About 45 minutes, but it runs every 10 minutes.\nB: That's not bad. I'll try it tomorrow.\nA: Great! We could even share a ride if you want.", "kind": "general", "questions": [
        {"stem": "Why was the train delayed?", "options": ["Weather", "Signal failure", "Accident", "Strike"], "correct_index": 1, "explanation": "There was a signal failure."},
        {"stem": "How long does the bus take?", "options": ["30 minutes", "45 minutes", "60 minutes", "20 minutes"], "correct_index": 1, "explanation": "The bus takes about 45 minutes."},
        {"stem": "How often does the bus run?", "options": ["Every 5 minutes", "Every 10 minutes", "Every 20 minutes", "Every 30 minutes"], "correct_index": 1, "explanation": "The bus runs every 10 minutes."},
        {"stem": "What does Person A suggest?", "options": ["Taking a taxi", "Sharing a ride", "Walking", "Cycling"], "correct_index": 1, "explanation": "Person A suggests sharing a ride."},
        {"stem": "What is Person B's decision?", "options": ["Keep taking the train", "Try the bus tomorrow", "Quit their job", "Move closer to work"], "correct_index": 1, "explanation": "Person B decides to try the bus."},
    ]},
    {"title": "Office Meeting Discussion", "transcript": "Manager: Thank you all for joining. Let's discuss the Q3 results.\nSarah: Revenue is up 15% compared to last quarter.\nManager: That's excellent. What about customer satisfaction?\nDavid: Our NPS score improved from 72 to 78.\nManager: Good. Any areas of concern?\nSarah: We're seeing some delays in product development.\nManager: What's causing the delays?\nDavid: We need two more developers to meet the timeline.\nManager: I'll speak to HR about fast-tracking the hiring.\nSarah: That would help. We also need to review the project scope.\nManager: Let's schedule a follow-up meeting for Thursday.", "kind": "general", "questions": [
        {"stem": "What is the revenue increase?", "options": ["5%", "10%", "15%", "20%"], "correct_index": 2, "explanation": "Revenue is up 15%."},
        {"stem": "What is the new NPS score?", "options": ["72", "75", "78", "80"], "correct_index": 2, "explanation": "The NPS score improved to 78."},
        {"stem": "What is causing delays?", "options": ["Lack of budget", "Need more developers", "Bad weather", "Client issues"], "correct_index": 1, "explanation": "They need two more developers."},
        {"stem": "What will the manager do?", "options": ["Hire himself", "Speak to HR about hiring", "Cancel the project", "Do nothing"], "correct_index": 1, "explanation": "The manager will speak to HR."},
        {"stem": "When is the follow-up meeting?", "options": ["Monday", "Wednesday", "Thursday", "Friday"], "correct_index": 2, "explanation": "The follow-up is scheduled for Thursday."},
    ]},
    {"title": "Restaurant Reservation Call", "transcript": "Host: Good evening, Bella Vista Restaurant. How can I help you?\nCustomer: Hi, I'd like to make a reservation for Saturday.\nHost: Certainly. How many people?\nCustomer: There will be four of us.\nHost: And what time would you prefer?\nCustomer: Around 7:30 PM, if possible.\nHost: Let me check... I have a table at 7:15 or 8:00.\nCustomer: 7:15 would be perfect.\nHost: May I have your name, please?\nCustomer: It's Johnson. J-O-H-N-S-O-N.\nHost: Thank you, Mr. Johnson. A table for four at 7:15 on Saturday.\nCustomer: Do you have any dietary options? One of us is vegetarian.\nHost: Absolutely. We have a full vegetarian menu.\nCustomer: Great, thank you!", "kind": "general", "questions": [
        {"stem": "How many people will be dining?", "options": ["Two", "Three", "Four", "Five"], "correct_index": 2, "explanation": "There will be four people."},
        {"stem": "What time was the reservation made for?", "options": ["7:00 PM", "7:15 PM", "7:30 PM", "8:00 PM"], "correct_index": 1, "explanation": "The reservation is at 7:15 PM."},
        {"stem": "What day is the reservation?", "options": ["Friday", "Saturday", "Sunday", "Monday"], "correct_index": 1, "explanation": "The reservation is for Saturday."},
        {"stem": "What dietary requirement is mentioned?", "options": ["Vegan", "Gluten-free", "Vegetarian", "Halal"], "correct_index": 2, "explanation": "One person is vegetarian."},
        {"stem": "What is the customer's name?", "options": ["Smith", "Johnson", "Williams", "Brown"], "correct_index": 1, "explanation": "The customer's name is Johnson."},
    ]},
    {"title": "Weather Forecast", "transcript": "Good morning! Here's your weather update for today. We're expecting a mild start with temperatures around 15 degrees Celsius. However, by midday, cloud cover will increase significantly. There's a 70% chance of rain this afternoon, so do carry an umbrella. Winds will pick up from the west, reaching speeds of 30 kilometers per hour. The temperature will drop to around 12 degrees by evening. Tomorrow looks much better—sunny skies with temperatures reaching 22 degrees. The weekend forecast shows continued good weather, perfect for outdoor activities.", "kind": "general", "questions": [
        {"stem": "What is the morning temperature?", "options": ["10 degrees", "15 degrees", "20 degrees", "25 degrees"], "correct_index": 1, "explanation": "Morning temperatures are around 15°C."},
        {"stem": "What is the chance of afternoon rain?", "options": ["30%", "50%", "70%", "90%"], "correct_index": 2, "explanation": "There's a 70% chance of rain."},
        {"stem": "What will winds reach?", "options": ["20 km/h", "30 km/h", "40 km/h", "50 km/h"], "correct_index": 1, "explanation": "Winds will reach 30 km/h."},
        {"stem": "What will tomorrow's weather be like?", "options": ["Rainy", "Cloudy", "Sunny", "Snowy"], "correct_index": 2, "explanation": "Tomorrow will be sunny."},
        {"stem": "What is the evening temperature?", "options": ["10 degrees", "12 degrees", "15 degrees", "18 degrees"], "correct_index": 1, "explanation": "Evening temperature will drop to around 12 degrees."},
    ]},
    {"title": "Job Interview", "transcript": "Interviewer: Tell me about yourself.\nCandidate: I'm a software engineer with five years of experience. I specialize in web development.\nInterviewer: What programming languages do you know?\nCandidate: I'm proficient in JavaScript, Python, and TypeScript. I've also worked with React and Node.js.\nInterviewer: Why are you interested in this position?\nCandidate: I'm drawn to your company's innovative approach to AI. I want to work on projects that make a real impact.\nInterviewer: Where do you see yourself in five years?\nCandidate: I'd like to grow into a technical leadership role, mentoring other developers.\nInterviewer: Do you have any questions for me?\nCandidate: Yes, what does a typical day look like for this role?\nInterviewer: Great question. Let me explain...", "kind": "general", "questions": [
        {"stem": "How many years of experience does the candidate have?", "options": ["3 years", "5 years", "7 years", "10 years"], "correct_index": 1, "explanation": "The candidate has 5 years of experience."},
        {"stem": "What languages is the candidate proficient in?", "options": ["Java, C++, Ruby", "JavaScript, Python, TypeScript", "Python, C#, Go", "Swift, Kotlin, Java"], "correct_index": 1, "explanation": "JavaScript, Python, and TypeScript."},
        {"stem": "Why is the candidate interested?", "options": ["High salary", "Company's AI approach", "Close to home", "Good benefits"], "correct_index": 1, "explanation": "The candidate is drawn to the company's AI approach."},
        {"stem": "Where does the candidate see themselves in 5 years?", "options": ["Retired", "Technical leadership role", "Starting a company", "Changing careers"], "correct_index": 1, "explanation": "The candidate wants to grow into leadership."},
        {"stem": "What question does the candidate ask?", "options": ["What is the salary?", "What does a typical day look like?", "How many vacation days?", "Is there parking?"], "correct_index": 1, "explanation": "The candidate asks about a typical day."},
    ]},
    {"title": "Shopping Mall Conversation", "transcript": "A: Have you been to the new electronics store on the second floor?\nB: No, not yet. Is it any good?\nA: They have a great selection. I just bought new headphones there.\nB: How much did you pay?\nA: They were on sale for $50, originally $80.\nB: That's a good deal. I've been looking for new earbuds.\nA: They have a buy-one-get-one-half-off promotion this weekend.\nB: I might check it out. Do they accept credit cards?\nA: Yes, they take all major cards. They also have a store loyalty program.\nB: Thanks for the tip! I'll go this afternoon.", "kind": "general", "questions": [
        {"stem": "Where is the new electronics store?", "options": ["First floor", "Second floor", "Third floor", "Ground floor"], "correct_index": 1, "explanation": "The store is on the second floor."},
        {"stem": "How much did the headphones cost on sale?", "options": ["$30", "$50", "$80", "$100"], "correct_index": 1, "explanation": "The headphones were $50 on sale."},
        {"stem": "What promotion is running?", "options": ["Free shipping", "Buy one get one half off", "20% off everything", "Free gift"], "correct_index": 1, "explanation": "There's a buy-one-get-one-half-off promotion."},
        {"stem": "What is Person B looking for?", "options": ["Headphones", "Earbuds", "Speakers", "A phone"], "correct_index": 1, "explanation": "Person B is looking for earbuds."},
        {"stem": "When does Person B plan to go?", "options": ["Tomorrow", "This afternoon", "Next week", "They don't say"], "correct_index": 1, "explanation": "Person B plans to go this afternoon."},
    ]},
    {"title": "Doctor's Appointment", "transcript": "Doctor: Good morning. What brings you in today?\nPatient: I've been having headaches almost every day for the past two weeks.\nDoctor: I see. Can you describe the headaches?\nPatient: They're usually on one side of my head, and they throb.\nDoctor: Do you notice any triggers? Stress, certain foods, screen time?\nPatient: Actually, I've been working longer hours and staring at my computer.\nDoctor: That could be a factor. Let me do a quick examination.\n[Examination]\nDoctor: Everything looks normal. I recommend taking breaks every 20 minutes from screens.\nPatient: Should I take any medication?\nDoctor: Try over-the-counter pain relief for now. If it persists, come back.\nPatient: Thank you, doctor.", "kind": "general", "questions": [
        {"stem": "How long has the patient had headaches?", "options": ["One week", "Two weeks", "One month", "Three months"], "correct_index": 1, "explanation": "The patient has had headaches for two weeks."},
        {"stem": "Where are the headaches located?", "options": ["Both sides", "One side of the head", "Back of the head", "Forehead only"], "correct_index": 1, "explanation": "The headaches are on one side."},
        {"stem": "What does the doctor recommend?", "options": ["More medication", "Taking screen breaks every 20 minutes", "Surgery", "Complete rest"], "correct_index": 1, "explanation": "The doctor recommends screen breaks."},
        {"stem": "What was the examination result?", "options": ["Abnormal", "Normal", "Concerning", "Inconclusive"], "correct_index": 1, "explanation": "Everything looked normal."},
        {"stem": "What should the patient do if headaches persist?", "options": ["Ignore it", "Come back to the doctor", "Go to the ER", "Stop working"], "correct_index": 1, "explanation": "The patient should come back."},
    ]},
    {"title": "Travel Planning", "transcript": "A: So, have you decided where to go for vacation?\nB: We're thinking about Japan. The cherry blossom season is in April.\nA: That sounds amazing! How long are you planning to stay?\nB: About 10 days. We want to visit Tokyo, Kyoto, and Osaka.\nA: Have you booked flights yet?\nB: Not yet. We're comparing prices. Round trip is about $1,200 per person.\nA: That's reasonable. What about accommodation?\nB: We're looking at a mix of hotels and traditional ryokans.\nA: Don't forget to get a Japan Rail Pass. It saves a lot on train travel.\nB: Good idea! We'll factor that into the budget.\nA: You'll love it. Japan is incredible.", "kind": "general", "questions": [
        {"stem": "Where are they planning to go?", "options": ["China", "Japan", "Korea", "Thailand"], "correct_index": 1, "explanation": "They're planning to go to Japan."},
        {"stem": "How long is the trip?", "options": ["One week", "10 days", "Two weeks", "Three weeks"], "correct_index": 1, "explanation": "The trip is about 10 days."},
        {"stem": "How much are flights per person?", "options": ["$800", "$1,000", "$1,200", "$1,500"], "correct_index": 2, "explanation": "Flights are about $1,200 per person."},
        {"stem": "What cities do they want to visit?", "options": ["Beijing, Shanghai, Hong Kong", "Tokyo, Kyoto, Osaka", "Seoul, Busan, Incheon", "Bangkok, Chiang Mai, Phuket"], "correct_index": 1, "explanation": "Tokyo, Kyoto, and Osaka."},
        {"stem": "What does Person A recommend?", "options": ["A travel guide", "Japan Rail Pass", "Travel insurance", "A credit card"], "correct_index": 1, "explanation": "Person A recommends the Japan Rail Pass."},
    ]},
    {"title": "Fitness Class Instructions", "transcript": "Welcome to today's cardio class! We'll start with a five-minute warm-up. March in place, get those arms moving. Now, let's move to jumping jacks. Remember to land softly on your feet. Great job! Next, we'll do high knees. Bring those knees up to waist height. Keep your core engaged. Take a water break if you need one. Now, let's move to mountain climbers. Place your hands shoulder-width apart. Drive your knees toward your chest. We'll do 30 seconds of intense movement followed by 15 seconds of rest. Almost there! Last exercise: burpees. Drop down, push up, jump up. Five more! And cool down. Great work today!", "kind": "general", "questions": [
        {"stem": "How long is the warm-up?", "options": ["3 minutes", "5 minutes", "10 minutes", "15 minutes"], "correct_index": 1, "explanation": "The warm-up is 5 minutes."},
        {"stem": "What exercise comes after jumping jacks?", "options": ["Push-ups", "High knees", "Squats", "Lunges"], "correct_index": 1, "explanation": "High knees come after jumping jacks."},
        {"stem": "How long is the intense movement period?", "options": ["15 seconds", "30 seconds", "45 seconds", "60 seconds"], "correct_index": 1, "explanation": "Intense movement is 30 seconds."},
        {"stem": "What is the rest period?", "options": ["10 seconds", "15 seconds", "20 seconds", "30 seconds"], "correct_index": 1, "explanation": "Rest period is 15 seconds."},
        {"stem": "What is the last exercise?", "options": ["Jumping jacks", "Burpees", "Mountain climbers", "Squats"], "correct_index": 1, "explanation": "Burpees are the last exercise."},
    ]},
    {"title": "News Broadcast", "transcript": "Good evening. In today's news, the government has announced a new education reform policy. The policy aims to modernize the curriculum and integrate technology into classrooms. Under the new plan, all schools will receive tablets for students by next year. The education minister stated this will bridge the digital divide. However, teachers' unions have raised concerns about implementation timelines. In other news, the stock market closed at a record high today, with the Sensex gaining 500 points. Analysts attribute this to strong quarterly earnings. And finally, a new study shows that regular exercise can reduce the risk of heart disease by 30%. That's all for tonight. Good night.", "kind": "general", "questions": [
        {"stem": "What has the government announced?", "options": ["New tax policy", "Education reform policy", "Health policy", "Defense policy"], "correct_index": 1, "explanation": "The government announced education reform."},
        {"stem": "What will all schools receive?", "options": ["Computers", "Tablets", "Books", "Phones"], "correct_index": 1, "explanation": "All schools will receive tablets."},
        {"stem": "What concern did teachers' unions raise?", "options": ["Salary", "Implementation timelines", "Working hours", "Class sizes"], "correct_index": 1, "explanation": "Unions raised concerns about implementation timelines."},
        {"stem": "How much did the Sensex gain?", "options": ["100 points", "300 points", "500 points", "700 points"], "correct_index": 2, "explanation": "The Sensex gained 500 points."},
        {"stem": "How much can exercise reduce heart disease risk?", "options": ["10%", "20%", "30%", "50%"], "correct_index": 2, "explanation": "Exercise can reduce risk by 30%."},
    ]},
]


# =========================================================================
# COMPANY LISTENING PASSAGES
# =========================================================================

COMPANY_LISTENING_PASSAGES = {
    "TCS": [{"title": "TCS Employee Onboarding", "transcript": "Welcome to TCS! During your first week, you'll complete the ILP—Initial Learning Program. This includes technical training, soft skills workshops, and team-building activities. You'll be assigned a mentor who will guide you through your first project. TCS uses an internal platform called Ultimatix for all HR and learning needs. Please make sure your Ultimatix account is activated by end of day. Your reporting manager will share your project allocation within two weeks.", "kind": "TCS", "questions": [
        {"stem": "What is the first week at TCS called?", "options": ["Training period", "ILP—Initial Learning Program", "Induction", "Orientation"], "correct_index": 1, "explanation": "The first week is the ILP."},
        {"stem": "What platform does TCS use for HR?", "options": ["Workday", "Ultimatix", "SAP", "Oracle"], "correct_index": 1, "explanation": "TCS uses Ultimatix."},
        {"stem": "When will project allocation be shared?", "options": ["Immediately", "Within one week", "Within two weeks", "After one month"], "correct_index": 2, "explanation": "Project allocation is within two weeks."},
        {"stem": "What does the ILP include?", "options": ["Only technical training", "Technical, soft skills, and team-building", "Only soft skills", "Only team-building"], "correct_index": 1, "explanation": "ILP includes technical training, soft skills, and team-building."},
        {"stem": "Who guides new employees?", "options": ["HR manager", "A mentor", "CEO", "No one"], "correct_index": 1, "explanation": "New employees are assigned a mentor."},
    ]}],
    "Infosys": [{"title": "Infosys Campus Tour", "transcript": "Welcome to the Infosys Mysore campus, one of the largest corporate training centers in the world. The campus spans 337 acres and includes 15 training buildings, 800 classrooms, and accommodation for over 14,000 trainees. You'll find state-of-the-art labs, a swimming pool, tennis courts, and a golf course. The food court offers cuisines from around the world. Your training schedule is available on the Lex platform. Please download the Infosys mobile app for real-time updates.", "kind": "Infosys", "questions": [
        {"stem": "How big is the Mysore campus?", "options": ["100 acres", "200 acres", "337 acres", "500 acres"], "correct_index": 2, "explanation": "The campus spans 337 acres."},
        {"stem": "How many trainees can the campus accommodate?", "options": ["5,000", "10,000", "14,000", "20,000"], "correct_index": 2, "explanation": "It can accommodate over 14,000 trainees."},
        {"stem": "Where is the training schedule available?", "options": ["Email", "Lex platform", "Intranet", "Notice board"], "correct_index": 1, "explanation": "The schedule is on the Lex platform."},
        {"stem": "What facilities are mentioned?", "options": ["Only classrooms", "Labs, pool, tennis, golf", "Only labs", "Only sports"], "correct_index": 1, "explanation": "The campus has labs, pool, tennis courts, and golf."},
        {"stem": "What app should trainees download?", "options": ["Google Maps", "Infosys mobile app", "WhatsApp", "LinkedIn"], "correct_index": 1, "explanation": "Trainees should download the Infosys mobile app."},
    ]}],
    "Wipro": [{"title": "Wipro Project Discussion", "transcript": "Team, let's discuss the Q3 deliverables. Our primary focus is the migration of the legacy system to Wipro's FullStride Cloud platform. Raj, you'll lead the data migration team. Priya, handle the API integrations. We have a deadline of March 31st. The client wants a phased approach—Phase 1 goes live in February. Any blockers? Raj, we might need additional AWS certifications. Priya, ensure backward compatibility with the old APIs. Let's sync daily at 10 AM.", "kind": "Wipro", "questions": [
        {"stem": "What platform is the system migrating to?", "options": ["AWS", "FullStride Cloud", "Azure", "Google Cloud"], "correct_index": 1, "explanation": "The system is migrating to FullStride Cloud."},
        {"stem": "What is Raj's role?", "options": ["API integration", "Data migration lead", "Project manager", "Client liaison"], "correct_index": 1, "explanation": "Raj leads the data migration team."},
        {"stem": "What is the project deadline?", "options": ["January 31", "February 28", "March 31", "April 30"], "correct_index": 2, "explanation": "The deadline is March 31st."},
        {"stem": "When does Phase 1 go live?", "options": ["January", "February", "March", "April"], "correct_index": 1, "explanation": "Phase 1 goes live in February."},
        {"stem": "What is the daily sync time?", "options": ["9 AM", "10 AM", "11 AM", "2 PM"], "correct_index": 1, "explanation": "Daily sync is at 10 AM."},
    ]}],
    "Accenture": [{"title": "Accenture Client Meeting", "transcript": "Good morning everyone. Today we're presenting the digital transformation roadmap to our client. Our proposal includes three phases. Phase 1 focuses on cloud migration using Accenture Cloud First. Phase 2 implements AI-driven analytics through our proprietary tools. Phase 3 establishes a digital operations center. The total investment is $15 million over 18 months. Expected ROI is 40% within two years. Let's make sure our Innovation Architecture capabilities are clearly communicated.", "kind": "Accenture", "questions": [
        {"stem": "How many phases are in the roadmap?", "options": ["2", "3", "4", "5"], "correct_index": 1, "explanation": "There are three phases."},
        {"stem": "What does Phase 1 focus on?", "options": ["AI analytics", "Cloud migration", "Digital operations", "Training"], "correct_index": 1, "explanation": "Phase 1 focuses on cloud migration."},
        {"stem": "What is the total investment?", "options": ["$10 million", "$15 million", "$20 million", "$25 million"], "correct_index": 1, "explanation": "The total investment is $15 million."},
        {"stem": "What is the expected ROI?", "options": ["20%", "30%", "40%", "50%"], "correct_index": 2, "explanation": "Expected ROI is 40%."},
        {"stem": "What is the timeline?", "options": ["12 months", "18 months", "24 months", "36 months"], "correct_index": 1, "explanation": "The timeline is 18 months."},
    ]}],
    "Cognizant": [{"title": "Cognizant Team Standup", "transcript": "Good morning team. Quick standup. What did everyone accomplish yesterday? Mike: I completed the user authentication module. Sarah: Working on the dashboard API. Tom: Resolved the database connection issue. Great progress. What's planned for today? Mike: Starting the payment integration. Sarah: Completing the API and writing tests. Tom: Optimizing query performance. Any blockers? Sarah needs access to the staging environment. Tom: I'll set that up today. Sprint ends Friday. Let's make sure we demo on time.", "kind": "Cognizant", "questions": [
        {"stem": "What did Mike complete yesterday?", "options": ["Payment module", "User authentication module", "Dashboard", "Database optimization"], "correct_index": 1, "explanation": "Mike completed the user authentication module."},
        {"stem": "What is Sarah working on?", "options": ["Authentication", "Dashboard API", "Payment integration", "Testing"], "correct_index": 1, "explanation": "Sarah is working on the dashboard API."},
        {"stem": "What issue did Tom resolve?", "options": ["Payment bug", "Authentication error", "Database connection", "API timeout"], "correct_index": 2, "explanation": "Tom resolved the database connection issue."},
        {"stem": "What is Mike's plan for today?", "options": ["Finish dashboard", "Start payment integration", "Write tests", "Optimize queries"], "correct_index": 1, "explanation": "Mike will start payment integration."},
        {"stem": "When is the sprint demo?", "options": ["Today", "Tomorrow", "Friday", "Next week"], "correct_index": 2, "explanation": "The sprint ends Friday with a demo."},
    ]}],
    "HCL": [{"title": "HCL Innovation Session", "transcript": "Welcome to the monthly innovation review. Last month, we received 200 ideas through the MyEureka platform. The top three ideas have been selected for prototyping. First, an AI-powered chatbot for internal support. Second, a predictive maintenance system for manufacturing clients. Third, a blockchain-based document verification tool. Each team will receive $50,000 for development. We expect prototypes in six weeks. Remember, HCL's employee-first culture means your ideas matter. Keep them coming.", "kind": "HCL", "questions": [
        {"stem": "How many ideas were submitted?", "options": ["100", "150", "200", "300"], "correct_index": 2, "explanation": "200 ideas were submitted."},
        {"stem": "What platform was used?", "options": ["Innovation Hub", "MyEureka", "IdeaStream", "ThinkTank"], "correct_index": 1, "explanation": "The MyEureka platform was used."},
        {"stem": "What is the first idea?", "options": ["AI chatbot", "Predictive maintenance", "Blockchain tool", "Cloud migration"], "correct_index": 0, "explanation": "The first idea is an AI chatbot."},
        {"stem": "How much funding does each team get?", "options": ["$25,000", "$50,000", "$100,000", "$200,000"], "correct_index": 1, "explanation": "Each team receives $50,000."},
        {"stem": "When are prototypes expected?", "options": ["Two weeks", "Four weeks", "Six weeks", "Eight weeks"], "correct_index": 2, "explanation": "Prototypes are expected in six weeks."},
    ]}],
    "Capgemini": [{"title": "Capgemini Strategy Meeting", "transcript": "Today's agenda is the Connected Platform strategy review. Our focus areas are cloud, data, AI, and cybersecurity. In Q3, we acquired three digital agencies to strengthen our creative capabilities. The Invent division has launched 15 new innovation projects. Client satisfaction scores are up 12% this quarter. Our consulting revenue grew by 18%. We need to maintain this momentum. Action items: Complete the Altran integration by year-end. Launch two new digital products in Q1. Hire 5,000 cloud engineers globally.", "kind": "Capgemini", "questions": [
        {"stem": "What is the focus of the Connected Platform?", "options": ["Only cloud", "Cloud, data, AI, and cybersecurity", "Only AI", "Only security"], "correct_index": 1, "explanation": "The focus is cloud, data, AI, and cybersecurity."},
        {"stem": "How many digital agencies were acquired?", "options": ["1", "2", "3", "5"], "correct_index": 2, "explanation": "Three digital agencies were acquired."},
        {"stem": "How many innovation projects has Invent launched?", "options": ["5", "10", "15", "20"], "correct_index": 2, "explanation": "Invent has launched 15 innovation projects."},
        {"stem": "How much did consulting revenue grow?", "options": ["10%", "15%", "18%", "25%"], "correct_index": 2, "explanation": "Consulting revenue grew by 18%."},
        {"stem": "How many cloud engineers need to be hired?", "options": ["1,000", "3,000", "5,000", "10,000"], "correct_index": 2, "explanation": "5,000 cloud engineers need to be hired globally."},
    ]}],
}


# =========================================================================
# GENERAL WRITING PROMPTS
# =========================================================================

GENERAL_WRITING_PROMPTS = [
    {"title": "Write an Email to Your Manager", "prompt": "Write a professional email to your manager requesting a day off next Friday. Include the reason, offer to complete pending work, and suggest a colleague who can cover your tasks.", "kind": "general", "key_points": ["Professional tone", "Clear request", "Reason for leave", "Work handover plan", "Contact availability"]},
    {"title": "Write a Report on Team Performance", "prompt": "Write a quarterly team performance report. Include achievements, areas for improvement, and recommendations for the next quarter. Use data and specific examples.", "kind": "general", "key_points": ["Clear structure", "Data-driven", "Achievements listed", "Areas identified", "Actionable recommendations"]},
    {"title": "Write a Customer Apology Letter", "prompt": "Write an apology letter to a customer who received a defective product. Acknowledge the issue, explain the resolution, and offer compensation.", "kind": "general", "key_points": ["Empathy", "Clear resolution", "Compensation offered", "Future prevention", "Contact information"]},
    {"title": "Write a Meeting Agenda", "prompt": "Prepare an agenda for a 1-hour project status meeting. Include time allocations, topics, and expected outcomes for each item.", "kind": "general", "key_points": ["Time allocation", "Clear topics", "Expected outcomes", "Priority ordering", "Buffer time"]},
    {"title": "Write a Project Proposal", "prompt": "Write a brief project proposal for implementing a new CRM system. Include objectives, timeline, budget estimate, and expected benefits.", "kind": "general", "key_points": ["Clear objectives", "Realistic timeline", "Budget breakdown", "Expected ROI", "Risk assessment"]},
    {"title": "Write a Feedback Email", "prompt": "Write constructive feedback email to a team member who has been consistently missing deadlines. Be professional, specific, and solution-oriented.", "kind": "general", "key_points": ["Specific examples", "Constructive tone", "Solutions suggested", "Support offered", "Follow-up plan"]},
    {"title": "Write a Business Proposal", "prompt": "Write a proposal to introduce flexible working hours in your department. Include benefits, potential challenges, and implementation plan.", "kind": "general", "key_points": ["Benefits outlined", "Challenges addressed", "Implementation steps", "Success metrics", "Trial period"]},
    {"title": "Write a Resignation Letter", "prompt": "Write a professional resignation letter giving two weeks notice. Express gratitude, offer to help with transition, and maintain positive relationships.", "kind": "general", "key_points": ["Clear intent", "Gratitude expressed", "Transition plan", "Last working day", "Professional tone"]},
    {"title": "Write a Progress Report", "prompt": "Write a weekly progress report for your project. Include completed tasks, pending items, blockers, and next week's plan.", "kind": "general", "key_points": ["Tasks completed", "Pending items", "Blockers identified", "Next steps", "Timeline updates"]},
    {"title": "Write an Interview Thank You Note", "prompt": "Write a thank you email after a job interview. Reference specific discussion points, reiterate interest, and ask about next steps.", "kind": "general", "key_points": ["Timely sending", "Specific references", "Enthusiasm shown", "Questions asked", "Professional closing"]},
    {"title": "Write a Complaint Letter", "prompt": "Write a formal complaint letter about poor service at a restaurant. Describe the experience, state what you expected, and request a resolution.", "kind": "general", "key_points": ["Date and details", "Clear complaint", "Expected service", "Resolution requested", "Professional tone"]},
    {"title": "Write a Training Request", "prompt": "Write a request to your supervisor for approval to attend a professional development training. Include the training details, benefits to the company, and cost breakdown.", "kind": "general", "key_points": ["Training details", "Benefits to company", "Cost breakdown", "Time commitment", "Knowledge transfer plan"]},
    {"title": "Write a Product Review", "prompt": "Write a detailed review of a software tool your team uses. Cover features, usability, pros and cons, and your overall recommendation.", "kind": "general", "key_points": ["Feature coverage", "Usability assessment", "Pros and cons", "Use cases", "Rating"]},
    {"title": "Write a Collaboration Request", "prompt": "Write an email to another department requesting collaboration on a cross-functional project. Explain the project, benefits, and what you need from them.", "kind": "general", "key_points": ["Project explanation", "Mutual benefits", "Specific needs", "Timeline", "Contact person"]},
    {"title": "Write a Follow-up Email", "prompt": "Write a follow-up email after a networking event. Reference your conversation, propose next steps, and attach your business card digitally.", "kind": "general", "key_points": ["Event reference", "Conversation recalled", "Next steps proposed", "Value offered", "Professional closing"]},
    {"title": "Write a Performance Self-Assessment", "prompt": "Write a self-assessment for your annual review. Highlight achievements, areas for growth, and goals for the next year.", "kind": "general", "key_points": ["Achievements listed", "Metrics included", "Growth areas", "Goals defined", "Alignment with company"]},
    {"title": "Write a Safety Notice", "prompt": "Write a safety notice for employees about new COVID-19 protocols in the office. Include mask requirements, social distancing, and reporting procedures.", "kind": "general", "key_points": ["Clear protocols", "Mask policy", "Distancing rules", "Reporting process", "Effective date"]},
    {"title": "Write a Thank You Note to Client", "prompt": "Write a thank you email to a client after closing a major deal. Express appreciation, confirm next steps, and reinforce the partnership.", "kind": "general", "key_points": ["Gratitude expressed", "Deal acknowledged", "Next steps confirmed", "Partnership emphasized", "Contact availability"]},
    {"title": "Write a Memo on New Policy", "prompt": "Write a memo announcing a new remote work policy. Include eligibility, guidelines, expectations, and support available.", "kind": "general", "key_points": ["Clear policy", "Eligibility defined", "Guidelines stated", "Expectations set", "Support resources"]},
    {"title": "Write an Event Invitation", "prompt": "Write an invitation email for a company's annual team-building event. Include date, time, location, activities, and RSVP instructions.", "kind": "general", "key_points": ["Event details", "Activities listed", "RSVP process", "Contact information", "Enthusiasm"]},
]


# =========================================================================
# COMPANY WRITING PROMPTS
# =========================================================================

COMPANY_WRITING_PROMPTS = {
    "TCS": [
        {"title": "TCS Project Proposal", "prompt": "Write a proposal for implementing TCS BaNCS for a mid-sized bank. Include benefits, implementation timeline, and cost estimate.", "kind": "TCS", "key_points": ["TCS BaNCS features", "Implementation phases", "Cost breakdown", "Expected ROI", "Risk mitigation"]},
        {"title": "TCS Training Feedback", "prompt": "Write feedback on your ILP (Initial Learning Program) experience at TCS. Cover technical training, soft skills, and overall experience.", "kind": "TCS", "key_points": ["Technical skills learned", "Soft skills improved", "Mentor feedback", "Suggestions for improvement", "Career impact"]},
    ],
    "Infosys": [
        {"title": "Infosys Innovation Proposal", "prompt": "Write a proposal for a new AI project using Infosys Nia. Include the problem statement, approach, and expected outcomes.", "kind": "Infosys", "key_points": ["Problem definition", "Nia capabilities", "Implementation plan", "Success metrics", "Budget estimate"]},
        {"title": "Infosys Project Report", "prompt": "Write a quarterly report on an Infosys Finacle implementation project. Cover progress, challenges, and next steps.", "kind": "Infosys", "key_points": ["Project status", "Milestones achieved", "Challenges faced", "Next quarter plan", "Client feedback"]},
    ],
    "Wipro": [
        {"title": "Wipro Migration Plan", "prompt": "Write a cloud migration proposal using Wipro FullStride Cloud. Include phases, timeline, and risk assessment.", "kind": "Wipro", "key_points": ["Migration phases", "Timeline", "Risk assessment", "Cost analysis", "Expected benefits"]},
        {"title": "Wipro Team Update", "prompt": "Write a weekly team status update for a Wipro project. Cover completed tasks, blockers, and upcoming deliverables.", "kind": "Wipro", "key_points": ["Tasks completed", "Blockers identified", "Next week plan", "Resource needs", "Timeline updates"]},
    ],
    "Accenture": [
        {"title": "Accenture Strategy Document", "prompt": "Write a strategy document for Accenture Cloud First implementation. Include business case, technical approach, and governance model.", "kind": "Accenture", "key_points": ["Business case", "Technical architecture", "Governance", "Migration approach", "Success criteria"]},
        {"title": "Accenture Client Presentation", "prompt": "Write a presentation outline for Accenture Innovation Architecture capabilities. Include service offerings and case studies.", "kind": "Accenture", "key_points": ["Service overview", "Case studies", "Differentiators", "Pricing model", "Implementation timeline"]},
    ],
    "Cognizant": [
        {"title": "Cognizant Digital Report", "prompt": "Write a report on Cognizant's digital transformation project using the Squads and Pods model. Include methodology and results.", "kind": "Cognizant", "key_points": ["Squads and Pods explained", "Project outcomes", "Methodology", "Client satisfaction", "Lessons learned"]},
        {"title": "Cognizant Process Improvement", "prompt": "Write a proposal for process improvement using Cognizant's consulting services. Include current state, target state, and roadmap.", "kind": "Cognizant", "key_points": ["Current state analysis", "Gap identification", "Target state", "Implementation roadmap", "Expected improvements"]},
    ],
    "HCL": [
        {"title": "HCL Innovation Proposal", "prompt": "Write a proposal for an innovation project through HCL's MyEureka platform. Include idea description, feasibility, and expected impact.", "kind": "HCL", "key_points": ["Idea description", "Feasibility analysis", "Expected impact", "Implementation plan", "Resource requirements"]},
        {"title": "HCL Employee Engagement Report", "prompt": "Write a report on employee engagement initiatives at HCL. Cover current programs, feedback, and improvement suggestions.", "kind": "HCL", "key_points": ["Current programs", "Employee feedback", "Engagement metrics", "Improvement areas", "Action items"]},
    ],
    "Capgemini": [
        {"title": "Capgemini Digital Proposal", "prompt": "Write a digital transformation proposal using Capgemini's Connected Platform. Include technology stack, timeline, and governance.", "kind": "Capgemini", "key_points": ["Technology stack", "Implementation phases", "Timeline", "Governance model", "Expected outcomes"]},
        {"title": "Capgemini Integration Report", "prompt": "Write a report on the Altran integration progress at Capgemini. Cover milestones, challenges, and synergies achieved.", "kind": "Capgemini", "key_points": ["Integration milestones", "Challenges", "Synergies", "Timeline", "Next steps"]},
    ],
}


# =========================================================================
# SEED FUNCTIONS
# =========================================================================

async def seed_quiz_items():
    """Seed quiz items - general and company questions."""
    count = 0
    for q in GENERAL_GRAMMAR_QUESTIONS:
        existing = await QuizItem.find(QuizItem.stem == q["stem"]).first()
        if existing:
            continue
        item = QuizItem(
            id=uid(), category="grammar", stem=q["stem"], options=q["options"],
            correct_index=q["correct_index"], explanation=q["explanation"],
            company="", seconds_allowed=30, difficulty=_rand_difficulty(), status="published",
        )
        await item.create()
        count += 1
    for q in GENERAL_VOCABULARY_QUESTIONS:
        existing = await QuizItem.find(QuizItem.stem == q["stem"]).first()
        if existing:
            continue
        item = QuizItem(
            id=uid(), category="vocabulary", stem=q["stem"], options=q["options"],
            correct_index=q["correct_index"], explanation=q["explanation"],
            company="", seconds_allowed=30, difficulty=_rand_difficulty(), status="published",
        )
        await item.create()
        count += 1
    all_company_quiz = {
        "TCS": TCS_QUESTIONS, "Infosys": INFOSYS_QUESTIONS, "Wipro": WIPRO_QUESTIONS,
        "Accenture": ACCENTURE_QUESTIONS, "Cognizant": COGNIZANT_QUESTIONS,
        "HCL": HCL_QUESTIONS, "Capgemini": CAPGEMINI_QUESTIONS,
    }
    for company, questions in all_company_quiz.items():
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
    return count


async def seed_reading_passages():
    """Seed reading passages - general and company."""
    count = 0
    for p in GENERAL_READING_PASSAGES:
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
    for company, passages in COMPANY_READING_PASSAGES.items():
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
    return count


async def seed_listening_passages():
    """Seed listening passages - general and company."""
    count = 0
    for p in GENERAL_LISTENING_PASSAGES:
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
    for company, passages in COMPANY_LISTENING_PASSAGES.items():
        for p in passages:
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
    return count


async def seed_writing_prompts():
    """Seed writing prompts - general and company."""
    count = 0
    for p in GENERAL_WRITING_PROMPTS:
        existing = await WritingPrompt.find(WritingPrompt.title == p["title"]).first()
        if existing:
            continue
        wp = WritingPrompt(
            id=uid(), title=p["title"], prompt=p["prompt"], kind=p["kind"],
            status="published", key_points=p["key_points"],
        )
        await wp.create()
        count += 1
    for company, prompts in COMPANY_WRITING_PROMPTS.items():
        for p in prompts:
            existing = await WritingPrompt.find(WritingPrompt.title == p["title"]).first()
            if existing:
                continue
            wp = WritingPrompt(
                id=uid(), title=p["title"], prompt=p["prompt"], kind=p["kind"],
                status="published", key_points=p["key_points"],
            )
            await wp.create()
            count += 1
    return count


async def seed_speaking_items():
    """Seed speaking/task items using TaskItem model."""
    count = 0
    general_speaking = [
        {"prompt": "Describe your favorite hobby and explain why you enjoy it. Speak for 1-2 minutes.", "task_type": "personal", "reference_text": "Sample: Introduction → How you started → Why you enjoy it → Benefits → Conclusion"},
        {"prompt": "Talk about a memorable experience from your childhood.", "task_type": "personal", "reference_text": "Sample: Setting the scene → The event → Your feelings → Why it's memorable → What you learned"},
        {"prompt": "Describe a place you would like to visit and explain why.", "task_type": "opinion", "reference_text": "Sample: Name the place → Why you chose it → What you'd do → Cultural significance"},
        {"prompt": "Explain a concept or skill you recently learned.", "task_type": "professional", "reference_text": "Sample: The concept → Why you learned it → Learning process → Challenges → Results"},
        {"prompt": "Describe your ideal work environment.", "task_type": "professional", "reference_text": "Sample: Physical environment → Work culture → Tools needed → Team dynamics"},
        {"prompt": "Talk about a book or movie that influenced you.", "task_type": "opinion", "reference_text": "Sample: Title and creator → Main plot/theme → Key message → Personal impact"},
        {"prompt": "Describe a challenge you faced at work and how you overcame it.", "task_type": "professional", "reference_text": "Sample: The challenge → Context → Your approach → Solution → Lessons learned"},
        {"prompt": "Explain the importance of communication skills in the workplace.", "task_type": "opinion", "reference_text": "Sample: Thesis → Types of communication → Examples → Benefits → Conclusion"},
        {"prompt": "Describe a technology that has changed your life.", "task_type": "opinion", "reference_text": "Sample: The technology → How you discovered it → Daily usage → Impact → Future potential"},
        {"prompt": "Talk about your career goals for the next five years.", "task_type": "professional", "reference_text": "Sample: Current role → Short-term goals → Long-term vision → Action plan"},
        {"prompt": "Describe a team project you worked on.", "task_type": "professional", "reference_text": "Sample: Project overview → Your role → Team dynamics → Results → What you learned"},
        {"prompt": "Explain what leadership means to you.", "task_type": "opinion", "reference_text": "Sample: Definition → Qualities of good leaders → Example → Why you admire them"},
        {"prompt": "Describe your hometown. What makes it special?", "task_type": "personal", "reference_text": "Sample: Location and size → Special features → Culture → Things to change"},
        {"prompt": "Talk about a time you received constructive feedback.", "task_type": "professional", "reference_text": "Sample: The feedback → Your reaction → How you processed it → Actions taken → Outcome"},
        {"prompt": "Explain the concept of work-life balance.", "task_type": "opinion", "reference_text": "Sample: Definition → Importance → Your strategies → Challenges → Tips"},
        {"prompt": "Describe an achievement you're proud of.", "task_type": "personal", "reference_text": "Sample: The achievement → Context → Your effort → Why it matters → What you learned"},
        {"prompt": "Explain how artificial intelligence is changing the workplace.", "task_type": "professional", "reference_text": "Sample: Introduction to AI → Applications → Benefits → Concerns → Future outlook"},
        {"prompt": "Talk about an essential skill for professionals today.", "task_type": "opinion", "reference_text": "Sample: The skill → Why it's important → How to develop it → Resources"},
        {"prompt": "Describe a memorable trip or journey.", "task_type": "personal", "reference_text": "Sample: Destination → Purpose → Experiences → Highlights → What you brought back"},
        {"prompt": "Explain the importance of networking in career development.", "task_type": "professional", "reference_text": "Sample: Why networking matters → Your approach → Events → Follow-up → Benefits"},
    ]
    for item_data in general_speaking:
        existing = await TaskItem.find(TaskItem.prompt_text == item_data["prompt"]).first()
        if existing:
            continue
        item = TaskItem(
            id=uid(), task_type=item_data["task_type"], prompt_text=item_data["prompt"],
            company="", reference_text=item_data["reference_text"], status="published",
        )
        await item.create()
        count += 1
    company_speaking = {
        "TCS": [
            {"prompt": "Describe your experience with TCS's Initial Learning Program (ILP).", "task_type": "professional", "reference_text": "Cover technical training, soft skills, mentorship, and career growth"},
            {"prompt": "Explain how TCS iON platform helps enterprises.", "task_type": "professional", "reference_text": "Cover cloud features, education solutions, and manufacturing applications"},
        ],
        "Infosys": [
            {"prompt": "Describe the Infosys Mysore campus and its training facilities.", "task_type": "professional", "reference_text": "Cover campus size, facilities, training programs, and culture"},
            {"prompt": "Explain the features of Infosys Nia AI platform.", "task_type": "professional", "reference_text": "Cover AI capabilities, automation features, and business benefits"},
        ],
        "Wipro": [
            {"prompt": "Describe Wipro's FullStride Cloud Services.", "task_type": "professional", "reference_text": "Cover cloud migration approach, tools, and success stories"},
            {"prompt": "Explain Wipro's 'Mode 1-2-3' strategy.", "task_type": "professional", "reference_text": "Cover core services, products, and ecosystem partnerships"},
        ],
        "Accenture": [
            {"prompt": "Describe Accenture's Innovation Architecture.", "task_type": "professional", "reference_text": "Cover innovation hubs, labs, studios, and capabilities"},
            {"prompt": "Explain Accenture Cloud First and its benefits.", "task_type": "professional", "reference_text": "Cover cloud migration, optimization, and management services"},
        ],
        "Cognizant": [
            {"prompt": "Describe Cognizant's Squads and Pods model.", "task_type": "professional", "reference_text": "Cover agile methodology, team structure, and delivery benefits"},
            {"prompt": "Explain Cognizant's approach to digital transformation.", "task_type": "professional", "reference_text": "Cover digital services, consulting, and implementation approach"},
        ],
        "HCL": [
            {"prompt": "Describe HCL's MyEureka innovation platform.", "task_type": "professional", "reference_text": "Cover idea submission, evaluation, and implementation process"},
            {"prompt": "Explain HCL's 'Mode 1-2-3' strategy and its impact.", "task_type": "professional", "reference_text": "Cover core IT services, products, and platform business"},
        ],
        "Capgemini": [
            {"prompt": "Describe Capgemini's Connected Platform strategy.", "task_type": "professional", "reference_text": "Cover cloud, data, AI, and cybersecurity integration"},
            {"prompt": "Explain Capgemini's Invent division and its role.", "task_type": "professional", "reference_text": "Cover innovation projects, consulting, and creative solutions"},
        ],
    }
    for company, items in company_speaking.items():
        for item_data in items:
            existing = await TaskItem.find(TaskItem.prompt_text == item_data["prompt"]).first()
            if existing:
                continue
            item = TaskItem(
                id=uid(), task_type=item_data["task_type"], prompt_text=item_data["prompt"],
                company=company, reference_text=item_data["reference_text"], status="published",
            )
            await item.create()
            count += 1
    return count


# =========================================================================
# MAIN
# =========================================================================

async def main():
    """Main seed function."""
    client = AsyncIOMotorClient(MONGO_URL)
    await init_beanie(
        database=client[DB_NAME],
        document_models=[QuizItem, ReadingPassage, ListeningPassage, WritingPrompt, TaskItem],
    )

    print("=" * 60)
    print("QUESTION BANK SEEDER")
    print("=" * 60)

    quiz_count = await seed_quiz_items()
    reading_count = await seed_reading_passages()
    listening_count = await seed_listening_passages()
    writing_count = await seed_writing_prompts()
    speaking_count = await seed_speaking_items()

    total_quiz = await QuizItem.find_all().count()
    total_reading = await ReadingPassage.find_all().count()
    total_listening = await ListeningPassage.find_all().count()
    total_writing = await WritingPrompt.find_all().count()
    total_speaking = await TaskItem.find_all().count()

    quiz_general = await QuizItem.find(QuizItem.company == "").count()
    quiz_company = await QuizItem.find(QuizItem.company != "").count()

    print(f"\n{'=' * 60}")
    print(f"SEEDING COMPLETE - Added {quiz_count + reading_count + listening_count + writing_count + speaking_count} new questions")
    print(f"{'=' * 60}")
    print(f"\nQuiz Items: {total_quiz} (General: {quiz_general}, Company: {quiz_company})")
    print(f"Reading Passages: {total_reading}")
    print(f"Listening Passages: {total_listening}")
    print(f"Writing Prompts: {total_writing}")
    print(f"Speaking Items: {total_speaking}")
    print(f"\nTotal: {total_quiz + total_reading + total_listening + total_writing + total_speaking}")
    print(f"{'=' * 60}")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
