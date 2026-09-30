/** Names of grahas, signs, nakshatras, tithis, weekdays and life domains, in English and Hindi. */

import type { Lang } from "@/lib/i18n";

const PLANETS: Record<string, [string, string]> = {
  sun: ["Sun", "सूर्य"],
  moon: ["Moon", "चंद्र"],
  mars: ["Mars", "मंगल"],
  mercury: ["Mercury", "बुध"],
  jupiter: ["Jupiter", "गुरु"],
  venus: ["Venus", "शुक्र"],
  saturn: ["Saturn", "शनि"],
  rahu: ["Rahu", "राहु"],
  ketu: ["Ketu", "केतु"],
};
const SIGNS_EN = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"];
const SIGNS_HI = ["मेष", "वृषभ", "मिथुन", "कर्क", "सिंह", "कन्या", "तुला", "वृश्चिक", "धनु", "मकर", "कुंभ", "मीन"];
const NAKSHATRAS_HI = [
  "अश्विनी", "भरणी", "कृत्तिका", "रोहिणी", "मृगशिरा", "आर्द्रा", "पुनर्वसु", "पुष्य", "आश्लेषा",
  "मघा", "पूर्वाफाल्गुनी", "उत्तराफाल्गुनी", "हस्त", "चित्रा", "स्वाति", "विशाखा", "अनुराधा", "ज्येष्ठा",
  "मूल", "पूर्वाषाढ़ा", "उत्तराषाढ़ा", "श्रवण", "धनिष्ठा", "शतभिषा", "पूर्वाभाद्रपद", "उत्तराभाद्रपद", "रेवती",
];
const TITHIS_HI = [
  "प्रतिपदा", "द्वितीया", "तृतीया", "चतुर्थी", "पंचमी", "षष्ठी", "सप्तमी", "अष्टमी",
  "नवमी", "दशमी", "एकादशी", "द्वादशी", "त्रयोदशी", "चतुर्दशी", "पूर्णिमा",
];
const VARAS: Record<string, string> = {
  Ravivara: "रविवार",
  Somavara: "सोमवार",
  Mangalavara: "मंगलवार",
  Budhavara: "बुधवार",
  Guruvara: "गुरुवार",
  Shukravara: "शुक्रवार",
  Shanivara: "शनिवार",
};
const DOMAINS: Record<string, [string, string]> = {
  career: ["Career", "करियर"],
  marriage: ["Marriage", "विवाह"],
  children: ["Children", "संतान"],
  wealth: ["Wealth", "धन"],
  property: ["Property", "संपत्ति"],
  education: ["Education", "शिक्षा"],
  parents: ["Parents", "माता-पिता"],
  spirituality: ["Spirituality", "आध्यात्मिकता"],
  health: ["Health", "स्वास्थ्य"],
  travel: ["Travel", "यात्रा"],
};

const pick = (pair: [string, string] | undefined, lang: Lang, fallback: string) =>
  pair ? pair[lang === "hi" ? 1 : 0] : fallback;

export const planetName = (body: string, lang: Lang) => pick(PLANETS[body], lang, body);
export const signName = (index: number, lang: Lang) => (lang === "hi" ? SIGNS_HI : SIGNS_EN)[index] ?? String(index);
export const domainName = (domain: string, lang: Lang) => pick(DOMAINS[domain], lang, domain);

/** Nakshatra ``number`` is 1 (Ashwini) to 27; ``english`` is the API's name. */
export const nakshatraName = (number: number, english: string, lang: Lang) =>
  lang === "hi" ? (NAKSHATRAS_HI[number - 1] ?? english) : english;

/** Tithi ``number`` is 1 to 30 (15 Purnima, 30 Amavasya). */
export function tithiName(number: number, english: string, lang: Lang): string {
  if (lang !== "hi") return english;
  if (number === 30) return "अमावस्या";
  return TITHIS_HI[(number - 1) % 15] ?? english;
}

export const varaName = (english: string, lang: Lang) => (lang === "hi" ? (VARAS[english] ?? english) : english);
