"""Traditional significations behind the life reading's topic sections: the personal
portrait, kinds of work, foreign links, the spouse, health and remedies.

Written in our own words from the classical significations (Brihat Jataka on livelihood,
BPHS on the houses and planets) and common practice. Health is described as tendencies
and body areas to look after, never as illness; remedies are traditional practices that
cost little or nothing, never cures.
"""

from __future__ import annotations

from typing import Literal

from jyotish_engine.astro.bodies import Body
from jyotish_engine.core.zodiac import Sign

Element = Literal["fire", "earth", "air", "water"]
ELEMENTS: tuple[Element, ...] = ("fire", "earth", "air", "water")
#: Signs run fire, earth, air, water from Aries.
ELEMENT: dict[Sign, Element] = {sign: ELEMENTS[sign % 4] for sign in Sign}
MOVABLE_SIGNS = frozenset({Sign.ARIES, Sign.CANCER, Sign.LIBRA, Sign.CAPRICORN})
WATER_SIGNS = frozenset({Sign.CANCER, Sign.SCORPIO, Sign.PISCES})

# -- the portrait ---------------------------------------------------------------------

ELEMENT_DOMINANT: dict[Element, str] = {
    "fire": "with most of your chart in fire signs, you run on enthusiasm and action, and you "
    "light up when there is something to win",
    "earth": "with most of your chart in earth signs, you are practical and patient, and you "
    "trust what you can see and build",
    "air": "with most of your chart in air signs, you live through ideas, conversation and "
    "people, and you need mental space",
    "water": "with most of your chart in water signs, you are guided by feelings and "
    "intuition, and you pick up the moods around you",
}
ELEMENT_MISSING: dict[Element, str] = {
    "fire": "With little fire in your chart, you may need a push to get started, but once "
    "you move you keep going.",
    "earth": "With little earth in your chart, routine and practical details don't come "
    "naturally; simple systems help you.",
    "air": "With little air in your chart, you learn more from experience than from theory.",
    "water": "With little water in your chart, you find it easier to act on your feelings "
    "than to put them into words.",
}
#: A planet in the first house colours the whole personality.
FIRST_HOUSE: dict[Body, str] = {
    Body.SUN: "the Sun in your first house gives you natural authority and a strong sense of "
    "who you are",
    Body.MOON: "the Moon in your first house makes you sensitive, approachable and quick to "
    "sense moods",
    Body.MARS: "Mars in your first house makes you bold and energetic, and sometimes hot-headed",
    Body.MERCURY: "Mercury in your first house gives you a youthful, witty and talkative manner",
    Body.JUPITER: "Jupiter in your first house gives you a wise, optimistic and dignified presence",
    Body.VENUS: "Venus in your first house gives you charm, good looks and a love of comfort",
    Body.SATURN: "Saturn in your first house makes you serious, patient and hard-working, "
    "older than your years",
    Body.RAHU: "Rahu in your first house gives you big ambitions and an unconventional streak",
    Body.KETU: "Ketu in your first house gives you an inward, spiritual and somewhat detached "
    "nature",
}
#: A planet sitting with the Moon colours the emotional nature.
MOON_WITH: dict[Body, str] = {
    Body.SUN: "the Moon close to the Sun makes you strong-willed and self-driven",
    Body.MARS: "the Moon with Mars makes you passionate and quick to react",
    Body.MERCURY: "the Moon with Mercury gives you a quick, analytical mind",
    Body.JUPITER: "the Moon with Jupiter gives you a generous, hopeful heart",
    Body.VENUS: "the Moon with Venus makes you affectionate and artistic",
    Body.SATURN: "the Moon with Saturn makes you serious and sometimes hard on yourself",
    Body.RAHU: "the Moon with Rahu gives you a restless, imaginative mind that calm routines "
    "settle",
    Body.KETU: "the Moon with Ketu can make you detached, even from your own feelings",
}
#: Where the Sun sits: where the person seeks recognition.
SUN_SHINES: dict[int, str] = {
    1: "in the way you carry yourself",
    2: "through your family's standing and your own earnings",
    3: "through courage, skills and your own initiative",
    4: "at home, and through property and comfort",
    5: "through creativity, intelligence and children",
    6: "by solving problems and overcoming rivals",
    7: "through partnerships and your dealings with people",
    8: "through research, and by handling a crisis well",
    9: "through learning, principles and guiding others",
    10: "through your career and public position",
    11: "through your network, gains and achievements",
    12: "quietly, behind the scenes or far from home",
}

# -- career ---------------------------------------------------------------------------

#: Kinds of work, each tagged with the planets, signs ("aries") and houses ("h10") that
#: point to it. The career section scores them against the chart.
FIELDS: dict[str, frozenset[str]] = {
    name: frozenset(tags.split())
    for name, tags in {
        "government service and administration": "sun leo h6 h10 saturn",
        "management and leadership roles": "sun leo aries capricorn h1 h10",
        "medicine and health care": "sun mars ketu scorpio h6 h8 h12",
        "politics and public life": "sun rahu leo h10 h11",
        "hospitality, food and catering": "moon venus cancer taurus h2 h4",
        "nursing, care work and social service": "moon cancer pisces h6 h12",
        "travel, shipping and import-export": "moon rahu cancer pisces h3 h9 h12",
        "agriculture, dairy and land": "moon saturn taurus cancer capricorn h4",
        "engineering and technical work": "mars saturn aries capricorn aquarius h3 h6",
        "police, defence and security": "mars aries scorpio h6",
        "real estate and construction": "mars saturn h4 capricorn",
        "sports and fitness": "mars aries h3 h5",
        "business and trade": "mercury gemini virgo h3 h7 h11",
        "banking, accounts and finance": "mercury jupiter virgo taurus h2 h11",
        "IT, software and data": "mercury rahu ketu aquarius gemini virgo",
        "writing, media and communication": "mercury gemini h3",
        "teaching and training": "jupiter mercury sagittarius h5 h9",
        "law and the judiciary": "jupiter saturn sagittarius libra h6 h9",
        "counselling and advisory work": "jupiter moon pisces sagittarius h9",
        "religion, spirituality and charity": "jupiter ketu pisces h9 h12",
        "the arts, music and design": "venus taurus libra h5",
        "fashion, beauty and jewellery": "venus taurus libra h2",
        "film, entertainment and media": "venus rahu leo h5",
        "manufacturing and industry": "saturn capricorn aquarius h6",
        "mining, oil and heavy machinery": "saturn mars scorpio capricorn h8",
        "logistics, transport and operations": "saturn rahu gemini h3 h6",
        "research and investigation": "ketu saturn scorpio h8",
        "foreign companies and work abroad": "rahu h7 h12",
        "aviation, electronics and new technology": "rahu aquarius gemini",
        "insurance, tax and auditing": "saturn scorpio h8",
    }.items()
}
#: Where the ruler of the house of career sits, and what kind of work that suits.
CAREER_LORD_IN_HOUSE: dict[int, str] = {
    1: "a career built in your own name, through your own skills and personality",
    2: "work linked to money, a family business, food or speech",
    3: "work that uses communication, travel, media or your own initiative",
    4: "work connected with property, vehicles, education or working from home",
    5: "work that uses intelligence and creativity: teaching, advising, the arts or investments",
    6: "service in a large organisation, competitive fields and roles that solve problems",
    7: "business, trade and work with clients or partners",
    8: "research, investigation, insurance or work that handles other people's money",
    9: "teaching, law, religion, higher education or work involving long journeys",
    10: "a strong, central career with positions of authority within reach",
    11: "large organisations, networks, sales and work that brings steady gains",
    12: "foreign companies, work abroad, travel or behind-the-scenes roles",
}
#: A planet in the house of career, in a few words.
CAREER_PLANET: dict[Body, str] = {
    Body.SUN: "authority and a public role",
    Body.MOON: "work with the public and some changes of job",
    Body.MARS: "drive, technical skill and leadership under pressure",
    Body.MERCURY: "business sense, communication and skill with numbers",
    Body.JUPITER: "respect, good judgement and an advisory role",
    Body.VENUS: "creativity, good taste and work in pleasant surroundings",
    Body.SATURN: "slow but lasting rise through discipline and hard work",
    Body.RAHU: "ambition, foreign links and unconventional, fast-growing fields",
    Body.KETU: "technical depth, research and work done behind the scenes",
}
#: The source of earnings (Brihat Jataka): the lord of the navamsa occupied by the ruler
#: of the tenth house.
KARMAJIVA: dict[Body, str] = {
    Body.SUN: "government, administration or medicine, often helped by people in authority",
    Body.MOON: "agriculture, food, water, travel or work with the public",
    Body.MARS: "machinery, metals, land, engineering or the forces",
    Body.MERCURY: "writing, accounts, trade, teaching or skilled speech",
    Body.JUPITER: "teaching, advice, religion, law or finance",
    Body.VENUS: "the arts, jewellery, fashion, vehicles or hospitality",
    Body.SATURN: "steady, demanding work: industry, labour, transport or long service",
}

# -- foreign travel and settlement ------------------------------------------------------

TRAVEL_LEVEL = {
    "strong": "Foreign travel is strongly marked in your chart.",
    "likely": "Foreign travel is likely in your chart.",
    "occasional": "Foreign travel comes up only now and then in your chart.",
}
SETTLE_LEVEL = {
    "strong": "Settling abroad, or far from your birthplace, is strongly indicated.",
    "possible": "Settling abroad is possible, especially through work, though your roots stay "
    "important to you.",
    "unlikely": "Your chart keeps you close to your roots: travel is more likely than settling "
    "abroad for good.",
}

# -- marriage and spouse ----------------------------------------------------------------

#: A planet in the house of marriage (or the spouse's significator) describes the spouse.
SPOUSE_PLANET: dict[Body, str] = {
    Body.SUN: "proud and dignified, with a strong personality",
    Body.MOON: "caring, emotional and attractive",
    Body.MARS: "energetic and strong-willed, at times argumentative",
    Body.MERCURY: "witty, communicative and young at heart, often with a head for business",
    Body.JUPITER: "wise, well educated and respected",
    Body.VENUS: "attractive, artistic and fond of comfort",
    Body.SATURN: "mature, serious and dependable, possibly older than you",
    Body.RAHU: "unconventional, possibly from a different background or culture",
    Body.KETU: "spiritual, private and a little detached",
}
#: What a second planet in the house of marriage adds to the spouse.
SPOUSE_ALSO: dict[Body, str] = {
    Body.SUN: "pride and a strong personality",
    Body.MOON: "tenderness",
    Body.MARS: "energy, and at times arguments",
    Body.MERCURY: "wit and a youthful manner",
    Body.JUPITER: "wisdom",
    Body.VENUS: "charm",
    Body.SATURN: "maturity",
    Body.RAHU: "an unconventional streak",
    Body.KETU: "a private, spiritual side",
}
#: Where the ruler of the house of marriage sits: where you may meet your partner.
WHERE_MEET: dict[int, str] = {
    1: "through your own efforts, as someone you choose yourself",
    2: "through your family, or as a match the family arranges",
    3: "through siblings, neighbours, short trips or messages",
    4: "through your mother's side, or among people from your home town",
    5: "through romance, studies or a creative circle",
    6: "at work or among colleagues",
    7: "through business, partnerships or social life",
    8: "suddenly or unexpectedly, sometimes through in-laws",
    9: "through travel, religion, higher studies or your father's circle",
    10: "at work or through your career",
    11: "through friends, elder siblings or social networks",
    12: "far from home, or abroad",
}

# -- health -----------------------------------------------------------------------------

#: The body areas each sign rules, by tradition.
SIGN_BODY: dict[Sign, str] = {
    Sign.ARIES: "the head and eyes",
    Sign.TAURUS: "the throat, neck and face",
    Sign.GEMINI: "the shoulders, arms and breathing",
    Sign.CANCER: "the chest and stomach",
    Sign.LEO: "the heart and upper back",
    Sign.VIRGO: "digestion",
    Sign.LIBRA: "the kidneys and lower back",
    Sign.SCORPIO: "the lower abdomen",
    Sign.SAGITTARIUS: "the hips, thighs and liver",
    Sign.CAPRICORN: "the knees, bones and joints",
    Sign.AQUARIUS: "the calves, ankles and circulation",
    Sign.PISCES: "the feet, sleep and immunity",
}
#: What a planet in a house of strain (or a weak one) asks you to look after.
PLANET_CARE: dict[Body, str] = {
    Body.SUN: "energy levels, eyes and the heart; morning sunlight and regular check-ups help",
    Body.MOON: "sleep, mood and fluid balance; rest and a calm routine help",
    Body.MARS: "heat in the body, blood pressure and minor injuries; exercise wisely",
    Body.MERCURY: "nerves, skin and stress; breaks and breathing exercises help",
    Body.JUPITER: "the liver, weight and sugar balance; go easy on rich food",
    Body.VENUS: "the kidneys, hormones and throat; drink enough water",
    Body.SATURN: "joints, bones, teeth and long-standing aches; stay active and keep warm",
    Body.RAHU: "stress and complaints that are hard to pin down; a calm routine helps",
    Body.KETU: "immunity and small puzzling complaints; rest and simple food help",
}
CONSTITUTION: dict[Element, str] = {
    "fire": "Your constitution runs warm: cooling food, enough water and not overworking keep "
    "you well.",
    "earth": "Your constitution is steady but can turn sluggish: regular exercise and light "
    "meals keep you well.",
    "air": "Your constitution is light and quick to tire: regular sleep, warm meals and calm "
    "routines keep you well.",
    "water": "Your constitution is sensitive: staying active, eating regularly and keeping "
    "good company keep you well.",
}
VITALITY = {
    "good": "Your natural vitality is good, and you recover quickly.",
    "steady": "Your vitality is steady when you keep a routine.",
    "care": "Your energy needs looking after: regular sleep, meals and exercise matter more "
    "for you than for most.",
}
HEALTH_NOTE = (
    "This describes traditional tendencies, not a diagnosis. For any health concern, please "
    "see a doctor."
)

# -- remedies ---------------------------------------------------------------------------

#: The traditional seed (beej) mantra of each planet, said 108 times.
MANTRA: dict[Body, str] = {
    Body.SUN: "Om Hraam Hreem Hraum Sah Suryaya Namah",
    Body.MOON: "Om Shraam Shreem Shraum Sah Chandramase Namah",
    Body.MARS: "Om Kraam Kreem Kraum Sah Bhaumaya Namah",
    Body.MERCURY: "Om Braam Breem Braum Sah Budhaya Namah",
    Body.JUPITER: "Om Graam Greem Graum Sah Gurave Namah",
    Body.VENUS: "Om Draam Dreem Draum Sah Shukraya Namah",
    Body.SATURN: "Om Praam Preem Praum Sah Shanaischaraya Namah",
    Body.RAHU: "Om Bhraam Bhreem Bhraum Sah Rahave Namah",
    Body.KETU: "Om Sraam Sreem Sraum Sah Ketave Namah",
}
DAY: dict[Body, str] = {
    Body.SUN: "Sunday",
    Body.MOON: "Monday",
    Body.MARS: "Tuesday",
    Body.MERCURY: "Wednesday",
    Body.JUPITER: "Thursday",
    Body.VENUS: "Friday",
    Body.SATURN: "Saturday",
    Body.RAHU: "Saturday",
    Body.KETU: "Tuesday",
}
WORSHIP: dict[Body, str] = {
    Body.SUN: "offer water to the rising Sun, or read the Aditya Hridayam",
    Body.MOON: "pray to Lord Shiva, for example with Om Namah Shivaya",
    Body.MARS: "recite the Hanuman Chalisa",
    Body.MERCURY: "pray to Lord Vishnu, for example with the Vishnu Sahasranama",
    Body.JUPITER: "pray to Lord Vishnu or your guru, and read something uplifting",
    Body.VENUS: "pray to Goddess Lakshmi",
    Body.SATURN: "recite the Hanuman Chalisa, or light a mustard-oil lamp",
    Body.RAHU: "pray to Goddess Durga",
    Body.KETU: "pray to Lord Ganesha",
}
DONATE: dict[Body, str] = {
    Body.SUN: "wheat or jaggery to people in need",
    Body.MOON: "rice, milk or white cloth to people in need",
    Body.MARS: "red lentils or jaggery to people in need",
    Body.MERCURY: "green moong or green vegetables to people in need",
    Body.JUPITER: "chana dal, turmeric or books to people in need",
    Body.VENUS: "rice, sugar or white clothes to people in need",
    Body.SATURN: "mustard oil, black sesame or warm clothes to people in need",
    Body.RAHU: "blankets or food to people in need",
    Body.KETU: "food to street dogs, or blankets to people in need",
}
CONDUCT: dict[Body, str] = {
    Body.SUN: "respect your father and seniors, and wake early",
    Body.MOON: "look after your mother, and keep your mind calm",
    Body.MARS: "exercise, and keep your temper in check",
    Body.MERCURY: "keep your word, speak kindly and keep learning",
    Body.JUPITER: "respect teachers, share what you know and live by your principles",
    Body.VENUS: "keep your relationships respectful and your surroundings clean",
    Body.SATURN: "be disciplined and honest, and help the elderly and working people",
    Body.RAHU: "avoid shortcuts, intoxicants and deals that look too good to be true",
    Body.KETU: "make time for quiet, prayer or meditation, and live simply",
}
#: What strengthening each planet helps with, for the remedies' reasons.
STRENGTHENS: dict[Body, str] = {
    Body.SUN: "confidence, health and standing at work",
    Body.MOON: "peace of mind, sleep and family harmony",
    Body.MARS: "energy, courage and property matters",
    Body.MERCURY: "clear thinking, studies and business",
    Body.JUPITER: "wisdom, children, wealth and good fortune",
    Body.VENUS: "marriage, comforts and creativity",
    Body.SATURN: "patience, steady work and long-term results",
    Body.RAHU: "focus and calm amid ambition and change",
    Body.KETU: "inner peace and clarity",
}
GEMSTONE: dict[Body, str] = {
    Body.SUN: "ruby",
    Body.MOON: "pearl",
    Body.MARS: "red coral",
    Body.MERCURY: "emerald",
    Body.JUPITER: "yellow sapphire",
    Body.VENUS: "diamond or white sapphire",
    Body.SATURN: "blue sapphire",
}
DAILY_PRACTICES = (
    "Start the day with a few quiet minutes of prayer, meditation or gratitude.",
    "Respect your parents and elders, and spend time with them.",
    "Give something every week, whether food, time or money, to someone who needs it.",
    "Keep your word and avoid shortcuts; steady, honest effort is the strongest remedy.",
)
