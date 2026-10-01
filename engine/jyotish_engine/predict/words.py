"""The words of a life reading: what signs, stars, planets and life areas mean.

Everything here is written in our own words from the classical significations (BPHS,
Brihat Jataka, Phaladeepika) and common practice, for a general reader. There are no
house numbers, no untranslated terms and nothing about death, illness or guaranteed
outcomes. Sentences are written to be spoken: "you", short clauses, everyday examples.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from jyotish_engine.astro.bodies import Body
from jyotish_engine.core.zodiac import Sign
from jyotish_engine.models import Tone
from jyotish_engine.rules.schema import Domain

#: Life stages that change how a planet's period or a house reads.
Stage = Literal["young", "adult", "senior"]
Tense = Literal["past", "now", "future"]

#: The rising sign: a short portrait for the summary, then a paragraph.
RISING: dict[Sign, tuple[str, str]] = {
    Sign.ARIES: (
        "direct, brave and quick to act",
        "With Aries rising, you meet life head-on. You like to take the first step, decide "
        "quickly and lead from the front, and you get restless when things move slowly. People "
        "see you as honest, energetic and brave, sometimes a little impatient or blunt. You do "
        "your best work with a clear goal and the freedom to chase it your own way.",
    ),
    Sign.TAURUS: (
        "steady, patient and loyal",
        "With Taurus rising, you are steady and dependable. You take your time to decide, but "
        "once you commit you rarely let go, whether it is a job, a friendship or a belief. You "
        "value security, good food, beautiful things and a peaceful home, and you work patiently "
        "to build them. People trust you because you are calm and practical, though you can dig "
        "your heels in when pushed.",
    ),
    Sign.GEMINI: (
        "curious, quick-witted and good with words",
        "With Gemini rising, your mind is always busy. You learn fast, talk easily and enjoy "
        "ideas, news, people and variety. You can juggle several things at once and adapt to new "
        "situations quickly, which suits work involving communication, trade or travel. Your "
        "challenge is staying with one thing long enough to finish it; boredom is your real "
        "enemy.",
    ),
    Sign.CANCER: (
        "caring, sensitive and devoted to family",
        "With Cancer rising, you feel things deeply and look after the people close to you. "
        "Home, family and emotional security matter to you more than almost anything, and you "
        "remember both kindness and hurt for a long time. You sense people's moods without being "
        "told, which makes you a natural protector. When you feel insecure you can turn moody or "
        "hold on too tightly.",
    ),
    Sign.LEO: (
        "confident, generous and a natural leader",
        "With Leo rising, you carry yourself with dignity and like to be in charge. You are "
        "generous, loyal and warm-hearted, and you expect respect in return. You shine when you "
        "are given responsibility or an audience, and you dislike being ignored or ordered "
        "about. Pride sometimes gets in the way, but your heart is big.",
    ),
    Sign.VIRGO: (
        "practical, careful and good with detail",
        "With Virgo rising, you are thoughtful, organised and quietly capable. You notice details "
        "others miss, like things done properly, and are often the one who fixes the problem. "
        "You think before you speak and prefer facts to drama. You can be hard on yourself and "
        "worry more than you need to, but people rely on you because you are careful and "
        "helpful.",
    ),
    Sign.LIBRA: (
        "charming, fair-minded and easy to get along with",
        "With Libra rising, you are pleasant, polite and good with people. You care about "
        "fairness and harmony and can see both sides of a story, which makes you a natural "
        "peacemaker. You enjoy beauty, style and good company, and you do well in partnership. "
        "Firm decisions can be hard, because you don't like to disappoint anyone.",
    ),
    Sign.SCORPIO: (
        "intense, determined and private",
        "With Scorpio rising, you have strong feelings and a strong will. You keep your thoughts "
        "to yourself until you trust someone, and you notice what people try to hide. When you "
        "set your mind on something, you see it through, whatever it takes. You are loyal to the "
        "people you love, but you don't easily forget being let down.",
    ),
    Sign.SAGITTARIUS: (
        "optimistic, principled and freedom-loving",
        "With Sagittarius rising, you are frank, cheerful and full of plans. You care about "
        "principles, learning and the bigger picture, and you are often drawn to teaching, "
        "travel, faith or philosophy. You need room to grow and you dislike pettiness. Sometimes "
        "you promise more than time allows, but your intentions are good.",
    ),
    Sign.CAPRICORN: (
        "hard-working, responsible and quietly ambitious",
        "With Capricorn rising, you take your goals seriously and are willing to work hard for "
        "them. You shoulder responsibility early in life, plan for the long term and earn "
        "respect through steady effort rather than show. Success may come later than for others, "
        "but it lasts. You can be reserved and anxious about the future, so remember to enjoy "
        "the present too.",
    ),
    Sign.AQUARIUS: (
        "independent, thoughtful and a little unconventional",
        "With Aquarius rising, you think for yourself and don't simply follow the crowd. You are "
        "friendly with many people, care about fairness and society, and often have ideas ahead "
        "of their time. You need space to do things your own way. People sometimes find you "
        "detached, but you are loyal to your friends and to your principles.",
    ),
    Sign.PISCES: (
        "kind, imaginative and intuitive",
        "With Pisces rising, you are gentle, compassionate and imaginative. You pick up other "
        "people's feelings easily and often put them first. Music, art, faith or a spiritual "
        "search may matter a great deal to you. You adapt to circumstances rather than fight "
        "them; your lesson is to set boundaries so that others don't take advantage of your "
        "good nature.",
    ),
}

#: The Moon sign: the emotional nature, as a short phrase and a paragraph.
MOON_SIGN: dict[Sign, tuple[str, str]] = {
    Sign.ARIES: (
        "a quick, honest heart that flares up and cools down fast",
        "Emotionally, you react quickly and honestly; what you feel shows on your face. Your "
        "moods flare up and settle fast, and you don't hold grudges for long. You need activity "
        "and a challenge to feel at your best.",
    ),
    Sign.TAURUS: (
        "a calm, steady heart that is hard to shake",
        "Emotionally, you are calm and steady, and it takes a lot to upset you. You find comfort "
        "in routine, good food, music and people you trust. Once you are attached to someone, "
        "you stay loyal for life.",
    ),
    Sign.GEMINI: (
        "a lively mind that needs conversation and variety",
        "Your feelings run through your thoughts: you like to talk things over. You need "
        "variety, conversation and something to think about, and you get restless when life is "
        "too quiet. Reading, writing or a good chat with friends lifts your mood.",
    ),
    Sign.CANCER: (
        "a tender heart that needs a secure home",
        "You feel things deeply and need a secure home and close family around you. You are "
        "nurturing and protective, and you remember how people made you feel. Your mood follows "
        "your surroundings, so a peaceful home matters a lot.",
    ),
    Sign.LEO: (
        "a warm, proud heart that needs to feel appreciated",
        "Emotionally, you are warm, proud and generous. You need to feel valued, and you give a "
        "great deal to the people who value you. When hurt, you are more likely to go quiet than "
        "to show it.",
    ),
    Sign.VIRGO: (
        "a practical heart that shows care by helping",
        "You handle feelings practically, by doing something useful. You notice small things, "
        "like order, and can be your own harshest critic. Calm routines and being of help to "
        "others keep you content.",
    ),
    Sign.LIBRA: (
        "a gentle heart that needs harmony",
        "You feel best in harmony and good company. Quarrels upset you, and you work hard to "
        "keep relationships pleasant. Beauty, art and fairness matter to you deeply.",
    ),
    Sign.SCORPIO: (
        "deep, private feelings and fierce loyalty",
        "Your feelings run deep and you keep them private. You are intensely loyal, sensitive to "
        "betrayal and slow to trust. Time alone to recharge, and a few people you trust "
        "completely, matter more to you than a large circle.",
    ),
    Sign.SAGITTARIUS: (
        "an optimistic heart that bounces back quickly",
        "Emotionally, you are optimistic and open-hearted. You need freedom, meaning and "
        "something to look forward to: travel, learning or a cause. You recover from setbacks "
        "faster than most.",
    ),
    Sign.CAPRICORN: (
        "a reserved heart that shows love through actions",
        "You keep your emotions in check and show care through actions rather than words. You "
        "feel secure when you have a plan and responsibilities you can handle. You may seem "
        "reserved, but people can count on you when it matters.",
    ),
    Sign.AQUARIUS: (
        "a friendly but independent heart",
        "You think your feelings through and like a little emotional space. Friendships and "
        "ideals matter a lot to you, and you care about people in a broad, fair-minded way. You "
        "need independence to feel at ease.",
    ),
    Sign.PISCES: (
        "a sensitive, compassionate heart with strong intuition",
        "You are sensitive and compassionate, and easily moved by other people's troubles. Your "
        "intuition is strong and your imagination rich. Quiet time, music or prayer settles your "
        "mind.",
    ),
}

#: The birth star (the Moon's nakshatra), in the order Ashwini to Revati.
NAKSHATRA_NATURE: tuple[str, ...] = (
    "Born under Ashwini, you are quick, lively and eager to start new things; you like to help "
    "people and you hate waiting.",
    "Bharani gives you a strong will and a sense of duty; you carry heavy loads without fuss and "
    "you are honest about what you want.",
    "Krittika makes you sharp, proud and principled; your words can cut, but you are fiercely "
    "protective of the people you care for.",
    "Rohini gives you charm, a love of beauty and comfort, and a creative streak; people are "
    "drawn to you easily.",
    "Mrigashira makes you curious and searching, always looking for the next idea, place or "
    "answer; you are gentle but restless.",
    "Ardra gives you a sharp, questioning mind; you grow most after difficult times, and you "
    "think things through deeply.",
    "Punarvasu makes you good-natured and resilient; whatever you lose, you tend to get back, "
    "and your optimism lifts others.",
    "Pushya gives you a caring, responsible nature; you like to support others, and you value "
    "tradition and discipline.",
    "Ashlesha gives you a clever, perceptive mind; you read people well and keep your own counsel.",
    "Magha connects you to family roots and tradition; you have a natural dignity and want to "
    "be respected for who you are.",
    "Purva Phalguni gives you warmth, creativity and a love of enjoyment; you are generous, "
    "sociable and loyal in love.",
    "Uttara Phalguni makes you dependable and helpful; you keep your promises and do well in "
    "partnership and service.",
    "Hasta gives you skilled hands and a practical, clever mind; you are good at making, fixing "
    "and crafting things.",
    "Chitra gives you an eye for design and a wish to create something impressive; you like to "
    "stand out.",
    "Swati makes you independent and adaptable; you need freedom to move, and you do well in "
    "trade and travel.",
    "Vishakha gives you strong ambition and focus; once you choose a goal, you pursue it with "
    "determination.",
    "Anuradha makes you a loyal friend and a good organiser; you succeed through cooperation, "
    "often away from your birthplace.",
    "Jyeshtha gives you seniority and a protective streak; you often end up looking after others.",
    "Mula makes you a seeker who wants to get to the root of things; you can make big changes "
    "and fresh starts.",
    "Purva Ashadha gives you confidence and persuasive power; you rarely accept defeat and you "
    "inspire others.",
    "Uttara Ashadha makes you principled, patient and steady; your victories come late, but "
    "they last.",
    "Shravana makes you a good listener and learner; you gain through knowledge, advice and "
    "connections.",
    "Dhanishta gives you rhythm, energy and ambition; you are sociable and generous, often with "
    "a musical or sporting side.",
    "Shatabhisha gives you an independent, research-minded nature; you are private, truthful "
    "and drawn to unusual knowledge.",
    "Purva Bhadrapada makes you intense and idealistic; you can be very practical and very "
    "spiritual by turns.",
    "Uttara Bhadrapada gives you depth, patience and self-control; you are quietly wise and "
    "good in a crisis.",
    "Revati makes you gentle, kind and protective; you are a natural guide who wants everyone "
    "to arrive safely.",
)

#: What a planet's period usually feels like, by life stage (a general statement).
PERIOD_FEEL: dict[Body, dict[Stage, str]] = {
    Body.SUN: {
        "young": "A Sun period in childhood brings out a confident, independent streak, and the "
        "father, or a father figure, is at the centre of family life.",
        "adult": "Sun periods put you in the spotlight: you want independence and recognition, "
        "and your dealings with bosses, government and your father matter more than usual.",
        "senior": "A Sun period later in life brings respect for your experience and a strong "
        "wish to keep your independence.",
    },
    Body.MOON: {
        "young": "A Moon period in childhood makes for a sensitive, imaginative child, close to "
        "the mother and easily touched by the mood at home.",
        "adult": "Moon periods are emotional and people-centred: home, mother and family come "
        "first, your mood rises and falls with events, and dealings with the public and travel "
        "increase.",
        "senior": "A Moon period later in life centres on family, home and peace of mind.",
    },
    Body.MARS: {
        "young": "A Mars period in childhood makes for an active, competitive child: sports, "
        "games and the odd quarrel with siblings or friends.",
        "adult": "Mars periods are fast and energetic: you push hard, take risks and get things "
        "done. Land, property and siblings often come into focus, and patience is the lesson.",
        "senior": "A Mars period later in life keeps you active and decisive; property and "
        "family matters may need a firm hand.",
    },
    Body.MERCURY: {
        "young": "A Mercury period in childhood brings curiosity, quick learning and a "
        "talkative, playful side; school, friends and games matter most.",
        "adult": "Mercury periods are busy and mental: learning, communication, business, "
        "paperwork and networking move to the centre.",
        "senior": "A Mercury period later in life keeps the mind lively: reading, writing, "
        "advising others and staying in touch.",
    },
    Body.JUPITER: {
        "young": "A Jupiter period in childhood usually means good guidance, a protected "
        "upbringing and teachers who notice you.",
        "adult": "Jupiter periods are periods of growth: good advice, wiser decisions, a growing "
        "family and a sense that things fall into place.",
        "senior": "A Jupiter period later in life brings wisdom, respect, joy through children "
        "and grandchildren, and a deeper interest in faith.",
    },
    Body.VENUS: {
        "young": "A Venus period in childhood often means a comfortable, affectionate "
        "upbringing, with art, music or creativity drawing you in.",
        "adult": "Venus periods bring comfort and pleasure: love and marriage, beauty, art, "
        "vehicles and the good things of life.",
        "senior": "A Venus period later in life brings comfort, family gatherings and time for "
        "the things you enjoy.",
    },
    Body.SATURN: {
        "young": "A Saturn period in childhood can make you serious beyond your years, with "
        "more responsibility, discipline or some hardship at home.",
        "adult": "Saturn periods are slow but solid: responsibility, hard work and patience, "
        "with rewards that come late but last.",
        "senior": "A Saturn period later in life favours simplicity, routine and letting go of "
        "what no longer matters.",
    },
    Body.RAHU: {
        "young": "A Rahu period in childhood is often unsettled: changes of home or school, "
        "restlessness, or an unusual environment.",
        "adult": "Rahu periods are restless and ambitious: sudden opportunities, unconventional "
        "choices, technology or foreign links, and at times some confusion about what you "
        "really want.",
        "senior": "A Rahu period later in life can bring unexpected changes and new interests; "
        "staying grounded helps.",
    },
    Body.KETU: {
        "young": "A Ketu period in childhood often makes for a quiet, inward child, with sudden "
        "changes around home or school.",
        "adult": "Ketu periods turn you inward: detachment, sudden breaks and a search for "
        "meaning; material goals may matter less than before.",
        "senior": "A Ketu period later in life deepens spiritual interests and detachment from "
        "worldly worries.",
    },
}

#: What a planet's period feels like in the teenage years (13 to 17).
TEEN_FEEL: dict[Body, str] = {
    Body.SUN: "A Sun period in the teenage years builds confidence and a wish for independence; "
    "how you get on with your father and teachers matters a lot.",
    Body.MOON: "A Moon period in the teenage years makes feelings run high; friendships, family "
    "and moods matter a great deal.",
    Body.MARS: "A Mars period in the teenage years brings energy, competitiveness and some "
    "impatience; sport and challenges help to channel it.",
    Body.MERCURY: "A Mercury period in the teenage years sharpens the mind; studies, friends, "
    "talking and new skills take centre stage.",
    Body.JUPITER: "A Jupiter period in the teenage years brings good guidance, growing maturity "
    "and support from teachers.",
    Body.VENUS: "A Venus period in the teenage years brings friendships, creativity, music and "
    "a love of nice things.",
    Body.SATURN: "A Saturn period in the teenage years asks for discipline early; results come "
    "through steady study rather than shortcuts.",
    Body.RAHU: "A Rahu period in the teenage years brings big ambitions and restlessness; it "
    "helps to stay grounded and to choose friends well.",
    Body.KETU: "A Ketu period in the teenage years can make you inward and unsure of your "
    "direction for a while, with sudden changes along the way.",
}

#: Adult period words that a reader under 18 should not get: no marriage or children.
MINOR_FEEL: dict[Body, str] = {
    Body.VENUS: "Venus periods bring comfort and pleasure: friendships, beauty, art, vehicles "
    "and the good things of life.",
    Body.JUPITER: "Jupiter periods are periods of growth: good advice, wiser decisions and a "
    "sense that things fall into place.",
}
#: House words for houses 5 and 7 for a reader under 18, at any age read.
MINOR_AREAS = {5: "studies and creativity", 7: "friendships and partnerships"}
#: A theme that comes back in a later year, told briefly.
AGAIN: dict[Tone, str] = {
    "good": "{When}: another good stretch for {area}.",
    "mixed": "{When}: another busy stretch for {area}.",
    "hard": "{When}: go carefully again with {area}.",
}
#: A closing line for a year that is mostly about effort.
STEADY = (
    "Keep routines steady and plans simple; this kind of year rewards patience.",
    "Small, steady steps work better than big moves this year.",
    "Lean on people you trust, and avoid rushing big decisions this year.",
)
#: Ways to name the year's brightest area.
BRIGHTEST = (
    "The year's brightest area is {area}.",
    "{Area} is where this year shines most.",
    "On the brighter side, {area} looks well supported this year.",
)

#: A planet's sub-period in a few words, for the years ahead.
SUB_PERIOD_FEEL: dict[Body, str] = {
    Body.SUN: "a time to step forward, take charge and be noticed",
    Body.MOON: "a more emotional, family-centred stretch",
    Body.MARS: "an energetic, fast-moving stretch, good for bold action but short on patience",
    Body.MERCURY: "a busy stretch of learning, paperwork, trade and new contacts",
    Body.JUPITER: "a hopeful stretch of growth, good advice and support",
    Body.VENUS: "a lighter, more pleasant stretch for relationships, comforts and enjoyment",
    Body.SATURN: "a stretch of hard work and responsibility, where patience pays",
    Body.RAHU: "a restless, ambitious stretch with sudden openings",
    Body.KETU: "a quieter, more inward stretch, good for reflection and finishing old business",
}

#: A planet's period in a few words, for the summary and the present.
PERIOD_GIST: dict[Body, str] = {
    Body.SUN: "a time of independence, authority and recognition",
    Body.MOON: "a time centred on feelings, family and home",
    Body.MARS: "a time of energy, drive and bold moves",
    Body.MERCURY: "a time of learning, business and communication",
    Body.JUPITER: "a time of growth, wisdom and good fortune",
    Body.VENUS: "a time of comfort, relationships and enjoyment",
    Body.SATURN: "a time of hard work, patience and lasting results",
    Body.RAHU: "a time of ambition, change and unconventional paths",
    Body.KETU: "a time of detachment, reflection and inner search",
}

#: The areas of life each house stands for, by life stage, in a few words.
HOUSE_AREAS: dict[int, dict[Stage, str]] = {
    1: {"young": "confidence", "adult": "your confidence and direction",
        "senior": "your well-being"},
    2: {"young": "family life", "adult": "money and family", "senior": "family and savings"},
    3: {"young": "siblings and friends", "adult": "courage and siblings",
        "senior": "siblings and hobbies"},
    4: {"young": "home and schooling", "adult": "home and property", "senior": "home and comforts"},
    5: {"young": "studies and creativity", "adult": "children and creativity",
        "senior": "children and grandchildren"},
    6: {"young": "discipline and competition", "adult": "work and competition",
        "senior": "daily routine"},
    7: {"young": "friendships", "adult": "marriage and partnerships", "senior": "your spouse"},
    8: {"young": "unexpected changes", "adult": "sudden changes", "senior": "unexpected changes"},
    9: {"young": "luck and teachers", "adult": "luck and higher learning",
        "senior": "faith and blessings"},
    10: {"young": "achievements", "adult": "career and status", "senior": "reputation"},
    11: {"young": "friends and rewards", "adult": "income and friends",
        "senior": "gains and friends"},
    12: {"young": "rest and time away", "adult": "expenses and time abroad",
        "senior": "spiritual life"},
}  # fmt: skip
#: Houses 5 and 7 between childhood and adulthood: no children or marriage yet.
STUDENT_AREAS = {
    5: "studies and romance",
    7: "close relationships",
}

#: Where the ruler of the rising sign sits, and what it says about the person.
CHART_RULER_IN_HOUSE: dict[int, str] = {
    1: "you are self-made: your own personality and choices drive your life",
    2: "family and financial security matter a lot to you, and you speak with conviction",
    3: "courage and initiative define you; you like to make your own way",
    4: "home, your mother and peace of mind are at the centre of your life",
    5: "you are creative and intelligent, with a real love of learning",
    6: "you thrive on challenge and service, and you don't back away from a hard task",
    7: "the people around you shape your life, and you do well working with others",
    8: "your life has some sudden turns, and you have a deep, research-minded side",
    9: "you are fortunate and principled, guided by faith, a teacher or your father",
    10: "achievement and reputation are central to who you are",
    11: "you are ambitious and well connected, with friends who help you",
    12: "you have a generous, private, spiritual side, and you may one day live far from home",
}


@dataclass(frozen=True, slots=True)
class Moment:
    """How an active stretch in one life area reads at a range of ages."""

    #: From this age (inclusive) until the next band's ``from_age``.
    from_age: float
    until_age: float | None
    good: str
    mixed: str | None
    hard: str | None

    def covers(self, age: float) -> bool:
        return age >= self.from_age and (self.until_age is None or age < self.until_age)

    def words(self, tone: Tone) -> str | None:
        return {"good": self.good, "mixed": self.mixed, "hard": self.hard}[tone]


#: What an active stretch in each life area means at each age, by its tenor. Health is
#: never read here; a parent's mixed or difficult stretches are not singled out.
MOMENTS: dict[Domain, tuple[Moment, ...]] = {
    Domain.CAREER: (
        Moment(
            18,
            21,
            "early steps towards a career: training, a first job or a clear sense of direction",
            "uncertainty about which career to choose",
            "a slow start: setbacks in finding the right course or first job",
        ),
        Moment(
            21,
            25,
            "a strong start to working life: a first job, an internship or a lucky break",
            "first steps at work, with some false starts",
            "a slow start at work: job hunting, or a first job that disappoints",
        ),
        Moment(
            25,
            45,
            "progress at work: a promotion, a better offer or recognition from seniors",
            "important changes at work: a new role, a transfer or a change of direction",
            "pressure at work: heavy responsibility, a difficult boss or a change you didn't "
            "choose",
        ),
        Moment(
            45,
            60,
            "authority and recognition at work: a senior role or a reward for years of effort",
            "changes in your position at work or in how your business is run",
            "a demanding stretch at work, with responsibility and office politics to handle",
        ),
        Moment(
            60,
            None,
            "respect for your experience: advisory roles or meaningful work",
            "a shift in your working life: retirement plans or a new kind of role",
            "work matters that need patience, or a slower pace than you'd like",
        ),
    ),
    Domain.MARRIAGE: (
        Moment(
            21,
            24,
            "a serious relationship, or the first marriage proposals and family talks",
            "relationship questions, and family talk about marriage",
            "relationship hurdles or disappointments",
        ),
        Moment(
            24,
            35,
            "marriage or a serious commitment, one of the chart's natural times to settle down",
            "relationship and marriage matters coming to a head, with some hesitation or family "
            "discussion",
            "relationship hurdles: delays, objections or second thoughts about commitment",
        ),
        Moment(
            35,
            None,
            "warmth and closeness with your spouse or partner",
            "changes that involve your partner: new shared plans or responsibilities",
            "a time when your relationship needs more patience and honest talking",
        ),
    ),
    Domain.CHILDREN: (
        Moment(
            25,
            45,
            "the family growing: a child's birth or happy news about children",
            "children and family plans in focus",
            "worries or extra effort around children and family plans",
        ),
        Moment(
            45,
            None,
            "pride in your children: their studies, jobs or weddings",
            "your children's lives going through changes that involve you",
            "your children needing more of your time and support",
        ),
    ),
    Domain.WEALTH: (
        Moment(
            21,
            25,
            "your first real earnings and a taste of financial independence",
            "money coming and going as you find your feet",
            "tight finances that call for careful budgeting",
        ),
        Moment(
            25,
            None,
            "better income and savings: a raise, a profitable deal or a sound investment",
            "money moving in and out: gains, with matching expenses",
            "high expenses or money held up somewhere; not a time for risky investments or lending",
        ),
    ),
    Domain.PROPERTY: (
        Moment(
            0,
            18,
            "a happy, comfortable home life, perhaps a move to a better house",
            "changes at home: a house move or a change in the family's set-up",
            "an unsettled home life, with a move or tension at home",
        ),
        Moment(
            18,
            25,
            "comforts at home, a vehicle, or a move to a better place",
            "a change of residence",
            "an unsettled phase at home",
        ),
        Moment(
            25,
            None,
            "buying a home, land or a vehicle, or improving your house",
            "home and property matters in motion: a move, a renovation or a purchase",
            "property matters getting stuck in paperwork, repairs or disputes; big purchases "
            "are best not rushed",
        ),
    ),
    Domain.EDUCATION: (
        Moment(
            4,
            13,
            "good progress at school, with encouragement from teachers",
            "changes in schooling: a new school or a new way of learning",
            "studies needing extra effort: a tough class or trouble concentrating",
        ),
        Moment(
            13,
            18,
            "good results and clarity about your subjects or stream",
            "important choices about studies, with some uncertainty",
            "pressure in studies, with results lagging behind your effort",
        ),
        Moment(
            18,
            25,
            "success in higher studies: admissions, degrees or competitive exams",
            "changes in studies: a new course, college or city",
            "hurdles in studies: a gap, a change of course or an exam that needs another attempt",
        ),
        Moment(
            25,
            36,
            "a good time for further studies, professional courses or new skills",
            "learning something new for work, with mixed results",
            "courses or exams that take more effort than expected",
        ),
    ),
    Domain.PARENTS: (
        Moment(
            0, 18, "strong support from your parents and a secure family atmosphere", None, None
        ),
        Moment(
            18,
            None,
            "support and blessings from your parents or elders, or good news in their lives",
            None,
            None,
        ),
    ),
    Domain.SPIRITUALITY: (
        Moment(
            25,
            None,
            "a deeper interest in faith, meditation or pilgrimage",
            "questions about purpose and what really matters to you",
            "restlessness and a search for meaning",
        ),
    ),
    Domain.TRAVEL: (
        Moment(
            0,
            18,
            "trips with the family, or a move to a new city",
            "a change of place for the family",
            "an unsettled time, with moves or changes of place",
        ),
        Moment(
            18,
            None,
            "travel, relocation or a chance abroad, for study or work",
            "a change of place: travel or a move",
            "travel or relocation that brings stress or expense",
        ),
    ),
}

#: Short names for life areas, for headings and summaries.
AREA_NAMES: dict[Domain, str] = {
    Domain.CAREER: "career",
    Domain.MARRIAGE: "marriage and relationships",
    Domain.CHILDREN: "children",
    Domain.WEALTH: "money",
    Domain.PROPERTY: "home and property",
    Domain.EDUCATION: "studies",
    Domain.PARENTS: "parents and family",
    Domain.SPIRITUALITY: "inner life",
    Domain.TRAVEL: "travel and moves",
}
#: A year's title from its leading life area and tenor.
YEAR_TITLES: dict[Domain, dict[Tone, str]] = {
    Domain.CAREER: {
        "good": "progress at work",
        "mixed": "changes at work",
        "hard": "a year to work steadily",
    },
    Domain.MARRIAGE: {
        "good": "a year for love and commitment",
        "mixed": "relationships in focus",
        "hard": "a year for patience in relationships",
    },
    Domain.CHILDREN: {
        "good": "joy through children",
        "mixed": "children in focus",
        "hard": "children need your support",
    },
    Domain.WEALTH: {
        "good": "money matters improve",
        "mixed": "money in motion",
        "hard": "a year to budget carefully",
    },
    Domain.PROPERTY: {
        "good": "home and comforts improve",
        "mixed": "changes at home",
        "hard": "an unsettled year at home",
    },
    Domain.EDUCATION: {
        "good": "a good year for studies",
        "mixed": "changes in studies",
        "hard": "studies need extra effort",
    },
    Domain.PARENTS: {"good": "family support", "mixed": "family matters", "hard": "family matters"},
    Domain.SPIRITUALITY: {
        "good": "a year of inner growth",
        "mixed": "a reflective year",
        "hard": "a year of soul-searching",
    },
    Domain.TRAVEL: {
        "good": "travel and new places",
        "mixed": "a change of place",
        "hard": "moves need planning",
    },
}

#: The promise of a life area in the birth chart: strong, good, average, needs effort.
Level = Literal["strong", "good", "average", "effort"]
AREA_TITLES: dict[Domain, str] = {
    Domain.CAREER: "Career and work",
    Domain.WEALTH: "Money",
    Domain.MARRIAGE: "Love and marriage",
    Domain.CHILDREN: "Children",
    Domain.PROPERTY: "Home and property",
    Domain.EDUCATION: "Studies",
    Domain.TRAVEL: "Travel and living away",
    Domain.SPIRITUALITY: "Inner life",
}
AREA_PROMISE: dict[Domain, dict[Level, str]] = {
    Domain.CAREER: {
        "strong": "Your chart gives strong support to your career. You have the drive and the "
        "backing to rise to a position of responsibility and respect.",
        "good": "Your career has good support in your chart. Expect steady progress with a few "
        "clear high points rather than overnight success.",
        "average": "Your career moves in phases: some stretches move fast, others ask for "
        "patience. Choosing the right timing makes a real difference for you.",
        "effort": "Career progress asks more effort of you than of most people, and "
        "recognition can come late. Persistence pays, especially in the stronger periods.",
    },
    Domain.WEALTH: {
        "strong": "Money is one of the chart's strong points: you have a good capacity to earn "
        "and to build savings over time.",
        "good": "Your finances have good support. Income grows with your efforts, and savings "
        "build up steadily if you keep an eye on spending.",
        "average": "Money comes and goes in cycles for you. Saving in the good periods carries "
        "you through the slower ones.",
        "effort": "Building wealth takes discipline in your chart, as expenses can run ahead of "
        "income. Steady saving works far better for you than risky bets.",
    },
    Domain.MARRIAGE: {
        "strong": "Marriage and partnership are well supported in your chart: a caring partner "
        "and a stable married life are indicated.",
        "good": "Married life has good support. Like any relationship, it does best with "
        "patience and give-and-take.",
        "average": "Relationships are an area of learning for you: good times alternate with "
        "misunderstandings, and open, honest talk is your best tool.",
        "effort": "Relationships ask for extra patience in your chart: marriage may come a "
        "little later, or need more adjustment. Taking time to choose well, and talking things "
        "through, helps a great deal.",
    },
    Domain.CHILDREN: {
        "strong": "Children are a source of real joy in your chart, and the bond with them is "
        "strong.",
        "good": "Your chart supports family life with children; they bring happiness and pride.",
        "average": "Matters to do with children move at their own pace; the stronger periods "
        "are the best times for family plans.",
        "effort": "Children and family planning may need more patience in your chart; the "
        "stronger periods are the best times.",
    },
    Domain.PROPERTY: {
        "strong": "Home, property and comforts are well supported: owning a good home and "
        "vehicles is likely.",
        "good": "Your chart supports a comfortable home life, and owning property is quite "
        "possible with planning.",
        "average": "Property comes through planning rather than luck; check paperwork carefully "
        "before big purchases.",
        "effort": "Property matters take more effort for you, with delays or paperwork common, "
        "so plan purchases carefully and avoid rushing.",
    },
    Domain.EDUCATION: {
        "strong": "Studies are a strength: you learn well and can go far in higher education.",
        "good": "Your chart supports good studies, especially with a regular routine.",
        "average": "Studies go well in some phases and need extra effort in others; steady "
        "habits matter more than talent alone.",
        "effort": "Studies need extra effort and the right setting; good teachers and a steady "
        "routine make a big difference.",
    },
    Domain.TRAVEL: {
        "strong": "Travel and links far from home are strongly indicated: you may study, work or "
        "even settle far from your birthplace.",
        "good": "Travel is well supported, and links with other cities or countries help you grow.",
        "average": "Travel comes up from time to time, mostly for work or family.",
        "effort": "Long-distance moves can bring more stress than benefit for you, so plan them "
        "carefully.",
    },
    Domain.SPIRITUALITY: {
        "strong": "You have a strong inner life: faith, meditation or a spiritual teacher can "
        "mean a great deal to you.",
        "good": "Spiritual interests grow with age and bring you peace.",
        "average": "Your inner life comes and goes in phases; quiet time helps you most in busy "
        "periods.",
        "effort": "Peace of mind comes through practice rather than easily; simple routines like "
        "prayer or a daily walk help.",
    },
}

#: The promise of an area for readers under 18, where the adult words don't fit.
AREA_PROMISE_YOUNG: dict[Domain, dict[Level, str]] = {
    Domain.TRAVEL: {
        "strong": "Travel and new places are strongly indicated: later in life you may study "
        "or work far from your birthplace.",
        "good": "Travel is well supported, and new places help you grow.",
        "average": "Travel comes up from time to time, mostly with the family.",
        "effort": "Frequent moves can unsettle you; a stable home base helps you thrive.",
    },
}

#: Kinds of work each planet favours, for the career section.
CAREER_FIELDS: dict[Body, str] = {
    Body.SUN: "government, administration or management",
    Body.MOON: "hospitality, care work or dealing with the public",
    Body.MARS: "engineering, the police or forces, sports or real estate",
    Body.MERCURY: "business, accounts, IT or communication",
    Body.JUPITER: "teaching, law, finance or advisory roles",
    Body.VENUS: "the arts, design, media or hospitality",
    Body.SATURN: "industry, manufacturing or long-term service",
    Body.RAHU: "technology, research, foreign companies or new fields",
    Body.KETU: "research, computing or precise technical work",
}

#: The partner the chart describes, from the sign of the house of marriage.
PARTNER: dict[Sign, str] = {
    Sign.ARIES: "energetic, direct and independent",
    Sign.TAURUS: "calm, loyal and fond of comfort",
    Sign.GEMINI: "talkative, clever and youthful",
    Sign.CANCER: "caring, emotional and family-minded",
    Sign.LEO: "proud, generous and confident",
    Sign.VIRGO: "practical, careful and helpful",
    Sign.LIBRA: "charming, well-mannered and fair",
    Sign.SCORPIO: "intense, private and deeply loyal",
    Sign.SAGITTARIUS: "cheerful, principled and fond of learning or travel",
    Sign.CAPRICORN: "serious, hard-working and responsible",
    Sign.AQUARIUS: "independent, friendly and a little unconventional",
    Sign.PISCES: "gentle, kind and spiritual",
}

#: Traditional, free remedies for a planet's period. No cures, no purchases.
REMEDIES: dict[Body, str] = {
    Body.SUN: "Wake early, offer water to the rising Sun and treat your father and seniors "
    "with respect; Sunday is the Sun's day.",
    Body.MOON: "Keep a calm routine, spend time near water, look after your mother, and give "
    "milk or rice to those in need on Mondays.",
    Body.MARS: "Exercise regularly, keep your temper in check, and recite the Hanuman Chalisa "
    "on Tuesdays.",
    Body.MERCURY: "Keep learning, write things down, keep your word in business and help "
    "students; Wednesday is Mercury's day and green its colour.",
    Body.JUPITER: "Respect teachers and elders, share what you know, and give to good causes, "
    "traditionally yellow things such as turmeric or chana dal on Thursdays.",
    Body.VENUS: "Keep your relationships kind and respectful, keep your home clean and "
    "beautiful, and give white sweets or clothes on Fridays.",
    Body.SATURN: "Be disciplined and honest, help the elderly and working people, and give "
    "mustard oil or black sesame on Saturdays.",
    Body.RAHU: "Avoid shortcuts, intoxicants and deals that look too good to be true; pray to "
    "Goddess Durga and help those in need.",
    Body.KETU: "Make time for meditation or prayer, live simply, pray to Lord Ganesha and feed "
    "street dogs.",
}

#: Traditional favourable things from the ruler of the rising sign.
LUCKY: dict[Body, tuple[str, str, str, int]] = {
    Body.SUN: ("Ruby (Manik)", "Sunday", "orange and gold", 1),
    Body.MOON: ("Pearl (Moti)", "Monday", "white and silver", 2),
    Body.MARS: ("Red coral (Moonga)", "Tuesday", "red", 9),
    Body.MERCURY: ("Emerald (Panna)", "Wednesday", "green", 5),
    Body.JUPITER: ("Yellow sapphire (Pukhraj)", "Thursday", "yellow", 3),
    Body.VENUS: ("Diamond or white sapphire (Heera)", "Friday", "white and pastel shades", 6),
    Body.SATURN: ("Blue sapphire (Neelam)", "Saturday", "dark blue and black", 8),
}

#: Well-known favourable combinations, by rule id (or id prefix), in plain words.
YOGA_WORDS: dict[str, str] = {
    "chandra.gajakesari": "Jupiter and the Moon support each other (Gajakesari yoga), a classic "
    "sign of good judgement, respect and the ability to bounce back.",
    "surya.budha_aditya": "The Sun and Mercury sit together (Budhaditya yoga), giving a sharp, "
    "practical intelligence and a way with words.",
    "mahapurusha.ruchaka": "Mars is especially strong (Ruchaka yoga): courage, drive and "
    "leadership come naturally to you.",
    "mahapurusha.bhadra": "Mercury is especially strong (Bhadra yoga): intelligence, wit and "
    "skill in business or communication.",
    "mahapurusha.hamsa": "Jupiter is especially strong (Hamsa yoga): wisdom, good character and "
    "respect from others.",
    "mahapurusha.malavya": "Venus is especially strong (Malavya yoga): charm, artistic taste "
    "and a comfortable life.",
    "mahapurusha.sasa": "Saturn is especially strong (Sasa yoga): endurance, organising ability "
    "and authority earned through hard work.",
    "raja.yogakaraka": "One planet in your chart is especially helpful (a yogakaraka), and its "
    "period tends to bring success and status.",
    "raja.lords": "Your chart has a Raja yoga, a combination for status and success that shows "
    "itself in the periods of the planets involved.",
    "dhana.lords": "Your chart has a Dhana yoga, a combination for earning and building wealth.",
    "neecha_bhanga": "A weak planet in your chart is rescued by others (Neecha Bhanga Raja "
    "yoga): early struggles in one area can turn into later success.",
    "bhava.harsha": "A Viparita Raja yoga (Harsha) turns difficulties to your advantage: you "
    "tend to come out of tough situations stronger.",
    "bhava.sarala": "A Viparita Raja yoga (Sarala) gives fearlessness and the ability to "
    "recover from setbacks.",
    "bhava.vimala": "A Viparita Raja yoga (Vimala) makes you careful with money and "
    "independent in spirit.",
    "named.lakshmi": "Lakshmi yoga: prosperity, good fortune and a respected position.",
    "named.saraswati": "Saraswati yoga: learning, wisdom and talent in the arts or with words.",
    "chandra.adhi": "Gentle planets support your Moon (Adhi yoga): a stable, comfortable life "
    "and helpful people around you.",
    "chandra.chandra_mangala": "The Moon and Mars work together (Chandra-Mangala yoga): a drive "
    "to earn and practical business sense.",
    "named.amala": "Amala yoga: a good name and kind deeds that people remember.",
}

#: Jupiter's current position counted from the Moon sign: its tenor, then the words for
#: adults and for the young.
JUPITER_NOW: dict[int, tuple[Tone, str, str]] = {
    1: ("mixed", "Jupiter is passing over your Moon sign, which widens your outlook but can "
        "bring changes of place and some restlessness", ""),
    2: ("good", "Jupiter's position favours income, savings and happiness in the family",
        "Jupiter's position favours happiness in the family"),
    3: ("mixed", "Jupiter's position asks for effort; progress may feel slower than you'd "
        "like", ""),
    4: ("hard", "Jupiter's position asks you to give home matters attention; peace of mind "
        "comes from keeping things simple", ""),
    5: ("good", "Jupiter's position brings luck with studies, children, creativity and good "
        "decisions", "Jupiter's position brings luck with studies and creativity"),
    6: ("hard", "Jupiter's position raises work pressure and competition; avoid loans and "
        "disputes", "Jupiter's position brings more competition and pressure at school"),
    7: ("good", "Jupiter's position favours marriage, partnerships and dealings with others",
        "Jupiter's position favours friendships and getting on with others"),
    8: ("hard", "Jupiter's position calls for a slower, more careful pace; avoid big risks",
        "Jupiter's position calls for a slower, more careful pace"),
    9: ("good", "Jupiter's position brings luck, blessings, travel and support from elders", ""),
    10: ("mixed", "Jupiter's position brings changes at work; guard your reputation",
         "Jupiter's position brings changes at school; steady work pays"),
    11: ("good", "Jupiter's position brings gains, wishes fulfilled and helpful friends", ""),
    12: ("mixed", "Jupiter's position raises expenses and travel, and favours charity and "
         "spiritual life", "Jupiter's position brings travel and time away"),
}  # fmt: skip
#: Saturn's current position from the Moon sign, outside Sade Sati.
SATURN_NOW: dict[int, tuple[Tone, str, str]] = {
    3: ("good", "Saturn's position rewards effort: courage, initiative and steady gains",
        "Saturn's position rewards effort and builds confidence"),
    4: ("hard", "Saturn's position puts pressure on home and peace of mind; keep a calm "
        "routine", ""),
    5: ("mixed", "Saturn's position makes studies or children a source of some worry; "
        "patience helps", "Saturn's position makes studies need more patience"),
    6: ("good", "Saturn's position helps you overcome rivals, debts and obstacles",
        "Saturn's position helps you overcome obstacles and competition"),
    7: ("hard", "Saturn's position asks for patience with your partner and in business "
        "dealings", "Saturn's position asks for patience with friends"),
    8: ("hard", "Saturn's position makes this a heavier, slower phase; avoid big risks and "
        "keep commitments simple", "Saturn's position makes this a slower phase; simple "
        "routines help"),
    9: ("mixed", "Saturn's position slows luck a little; steady effort works better than "
        "shortcuts", ""),
    10: ("hard", "Saturn's position brings pressure and responsibility at work; stay "
         "disciplined", "Saturn's position brings more pressure at school; stay disciplined"),
    11: ("good", "Saturn's position brings steady gains and the reward of past effort",
         "Saturn's position rewards past effort"),
}  # fmt: skip
#: The three phases of Sade Sati, Saturn's passage over the Moon sign.
SADE_SATI_PHASES: dict[int, tuple[str, str, str]] = {
    12: (
        "first",
        "expenses rise and effort doesn't seem to pay yet",
        "restlessness, and effort that doesn't seem to pay yet",
    ),
    1: (
        "middle",
        "the most demanding phase, when patience and discipline matter most",
        "the most demanding phase, when patience and discipline matter most",
    ),
    2: (
        "last",
        "money and family need care, but the pressure starts to ease",
        "family matters need care, but the pressure starts to ease",
    ),
}

#: How a planet's standing in the chart colours its period, by tense, in a few ways.
VERDICTS: dict[Tense, dict[Tone, tuple[str, ...]]] = {
    "past": {
        "good": (
            "{planet} is well placed in your chart, so on the whole this was a good chapter.",
            "With {planet} well placed in your chart, these years mostly went your way.",
        ),
        "mixed": (
            "{planet} gives mixed results in your chart, so this chapter had its ups and downs.",
            "{planet} is neither strong nor weak in your chart, so these years brought some "
            "of each: openings in one area, effort in another.",
            "Results were mixed, as {planet} is of middling strength in your chart.",
        ),
        "hard": (
            "{planet} is under some strain in your chart, so this chapter asked a lot of you, "
            "but it also made you stronger.",
            "With {planet} under strain in your chart, these years took effort, and they "
            "taught you resilience.",
        ),
    },
    "now": {
        "good": (
            "{planet} is well placed in your chart, so this period works in your favour on "
            "the whole.",
        ),
        "mixed": (
            "{planet} gives mixed results in your chart: some doors open while others need a push.",
        ),
        "hard": (
            "{planet} is under some strain in your chart, so results come through patience "
            "and steady effort rather than luck.",
        ),
    },
    "future": {
        "good": (
            "{planet} is well placed in your chart, so this should be a good chapter.",
            "With {planet} well placed in your chart, these years look promising.",
        ),
        "mixed": (
            "{planet} gives mixed results in your chart, so expect ups and downs.",
            "With {planet} of middling strength in your chart, expect a mix of openings and "
            "effort.",
        ),
        "hard": (
            "{planet} is under some strain in your chart, so this chapter will reward "
            "patience and planning.",
        ),
    },
}

#: Ways to say that a planet is connected with areas of life.
LINKS = (
    "In your chart, {planet} is linked with {areas}.",
    "For you, {planet} is connected with {areas}.",
    "{planet} looks after {areas} in your chart.",
)
#: Ways to tell a stretch of time, by tense and (for the future) tenor. ``{when}`` is
#: the time, ``{ages}`` the age in brackets and ``{what}`` the moment's words.
#: Frames for the first years of life, which nobody remembers.
EARLY_FRAMES = (
    "{When} {ages} brought {what}.",
    "Around {when} {ages}, the chart shows {what}.",
)
PAST_FRAMES = (
    "{When} {ages} brought {what}.",
    "Around {when} {ages}, the chart shows {what}.",
    "{When} {ages} stands out for {what}.",
    "You may remember {when} {ages} for {what}.",
)
NOW_FRAMES = (
    "Until {end}, the chart shows {what}.",
    "Right now, and until about {end}, expect {what}.",
)
FUTURE_FRAMES: dict[Tone, tuple[str, ...]] = {
    "good": (
        "{When} {ages} looks promising for {what}.",
        "Look out for {when} {ages}, which should bring {what}.",
        "{When} {ages} is likely to bring {what}.",
    ),
    "mixed": (
        "{When} {ages} is likely to bring {what}.",
        "Around {when} {ages}, expect {what}.",
    ),
    "hard": (
        "Around {when} {ages}, be prepared for {what}.",
        "{When} {ages} may bring {what}; steady effort will see you through.",
    ),
}
#: Openings for a past chapter. ``{stage}`` is the life stage in words.
CHAPTER_OPENINGS = (
    "From {y0} to {y1}, when you were {a0} to {a1}, you were in the {planet} period.",
    "{Stage} ({y0} to {y1}) fell in the {planet} period.",
    "The {planet} period ran from {y0} to {y1}, covering {stage}.",
)

#: What a strong planet gives the person, for the portrait.
PLANET_GIFTS: dict[Body, str] = {
    Body.SUN: "confidence and a natural authority",
    Body.MOON: "emotional strength and an easy way with people",
    Body.MARS: "courage, energy and the will to win",
    Body.MERCURY: "a quick mind and a way with words and numbers",
    Body.JUPITER: "wisdom, good judgement and the goodwill of others",
    Body.VENUS: "charm, taste and a talent for enjoying life",
    Body.SATURN: "discipline, patience and staying power",
}
#: Checks for the past: what to compare with real events, by life area.
CHECK_LABELS: dict[Domain, str] = {
    Domain.EDUCATION: "Studies: a key exam, an admission or a change of course",
    Domain.CAREER: "Career: a first job, a promotion or a change of job",
    Domain.MARRIAGE: "Marriage, engagement or a serious relationship",
    Domain.CHILDREN: "A child's birth or important news about children",
    Domain.PROPERTY: "A house move, or buying property or a vehicle",
    Domain.TRAVEL: "Travel, relocation or time abroad",
    Domain.WEALTH: "A clear rise in income or savings",
}
