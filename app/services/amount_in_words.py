"""An amount written out in words, in French or in English (#194).

A Tunisian invoice states its total in words under the figures ("Arrêtée la
présente facture à la somme de ..."). Written here rather than with a library:
two languages, whole numbers up to the billions, and the currency's own words
for its unit and its fraction - a few dozen lines with no new dependency.

French follows the traditional spelling the invoice reference uses: "quatre
mille neuf cent vingt-sept", hyphens only inside the tens, "et" for 21 to 71,
"quatre-vingts" and "deux cents" plural only when nothing follows, "mille"
invariable. English writes "four thousand nine hundred twenty-seven", without
"and".
"""

from decimal import ROUND_HALF_UP, Decimal

_FR_UNITS = ["zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix",
             "onze", "douze", "treize", "quatorze", "quinze", "seize"]
_FR_TENS = {20: "vingt", 30: "trente", 40: "quarante", 50: "cinquante", 60: "soixante"}

_EN_UNITS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
             "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
             "nineteen"]
_EN_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

# The unit and the fraction of each currency, singular and plural, and how
# many digits the fraction has.
CURRENCIES = {
    "TND": {"digits": 3,
            "fr": (("dinar", "dinars"), ("millime", "millimes")),
            "en": (("dinar", "dinars"), ("millime", "millimes"))},
    "EUR": {"digits": 2,
            "fr": (("euro", "euros"), ("centime", "centimes")),
            "en": (("euro", "euros"), ("cent", "cents"))},
    "USD": {"digits": 2,
            "fr": (("dollar", "dollars"), ("cent", "cents")),
            "en": (("dollar", "dollars"), ("cent", "cents"))},
}


def _fr_below_100(n: int, final: bool) -> str:
    if n <= 16:
        return _FR_UNITS[n]
    if n < 20:
        return f"dix-{_FR_UNITS[n - 10]}"
    if n < 70:
        tens, unit = divmod(n, 10)
        word = _FR_TENS[tens * 10]
        if unit == 0:
            return word
        return f"{word} et un" if unit == 1 else f"{word}-{_FR_UNITS[unit]}"
    if n < 80:
        # 70-79: soixante-dix, soixante et onze, soixante-douze...
        return "soixante et onze" if n == 71 else f"soixante-{_fr_below_100(n - 60, final)}"
    # 80-99: quatre-vingts takes its s only when it ends the number.
    if n == 80:
        return "quatre-vingts" if final else "quatre-vingt"
    return f"quatre-vingt-{_fr_below_100(n - 80, final)}"


def _fr_below_1000(n: int, final: bool) -> str:
    hundreds, rest = divmod(n, 100)
    parts = []
    if hundreds:
        if hundreds == 1:
            parts.append("cent")
        else:
            plural = rest == 0 and final
            parts.append(f"{_FR_UNITS[hundreds]} {'cents' if plural else 'cent'}")
    if rest:
        parts.append(_fr_below_100(rest, final))
    return " ".join(parts)


def _french(n: int) -> str:
    if n == 0:
        return _FR_UNITS[0]
    parts = []
    for size, singular, plural in ((10**9, "milliard", "milliards"), (10**6, "million", "millions")):
        count, n = divmod(n, size)
        if count:
            # A noun: "deux cents millions" keeps the plural of cent.
            parts.append(f"{_fr_below_1000(count, True)} {singular if count == 1 else plural}")
    thousands, n = divmod(n, 1000)
    if thousands:
        # "mille", never "un mille"; and mille is not a noun: "deux cent mille".
        parts.append("mille" if thousands == 1 else f"{_fr_below_1000(thousands, False)} mille")
    if n:
        parts.append(_fr_below_1000(n, True))
    return " ".join(parts)


def _en_below_1000(n: int) -> str:
    hundreds, rest = divmod(n, 100)
    parts = []
    if hundreds:
        parts.append(f"{_EN_UNITS[hundreds]} hundred")
    if rest:
        if rest < 20:
            parts.append(_EN_UNITS[rest])
        else:
            tens, unit = divmod(rest, 10)
            parts.append(_EN_TENS[tens] + (f"-{_EN_UNITS[unit]}" if unit else ""))
    return " ".join(parts)


def _english(n: int) -> str:
    if n == 0:
        return _EN_UNITS[0]
    parts = []
    for size, name in ((10**9, "billion"), (10**6, "million"), (1000, "thousand")):
        count, n = divmod(n, size)
        if count:
            parts.append(f"{_en_below_1000(count)} {name}")
    if n:
        parts.append(_en_below_1000(n))
    return " ".join(parts)


def number_in_words(n: int, locale: str) -> str:
    """A whole number from 0 up, in words."""
    if n < 0:
        raise ValueError("an amount in words cannot be negative")
    return _french(n) if locale == "fr" else _english(n)


def amount_in_words(value, currency: str = "TND", locale: str = "fr") -> str:
    """'quatre mille neuf cent vingt-sept dinars et cinq cents millimes'.

    The fraction is rounded to the currency's digits and left out when it is
    zero; the unit is left out when only a fraction is due.
    """
    spec = CURRENCIES.get(currency, CURRENCIES["TND"])
    (unit_one, unit_many), (frac_one, frac_many) = spec["fr" if locale == "fr" else "en"]
    scaled = (Decimal(str(value)) * 10 ** spec["digits"]).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    whole, fraction = divmod(int(scaled), 10 ** spec["digits"])
    words = []
    if whole or not fraction:
        number = number_in_words(whole, locale)
        # French: "deux millions de dinars", "un milliard d'euros".
        if locale == "fr" and number.endswith(("million", "millions", "milliard", "milliards")):
            words.append(f"{number} d'{unit_many}" if unit_many[0] in "aeiou" else f"{number} de {unit_many}")
        else:
            words.append(f"{number} {unit_one if whole <= 1 else unit_many}")
    if fraction:
        words.append(f"{number_in_words(fraction, locale)} {frac_one if fraction == 1 else frac_many}")
    return (" et " if locale == "fr" else " and ").join(words)
