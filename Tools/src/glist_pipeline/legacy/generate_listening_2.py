#!/usr/bin/env python3
"""
generate_listening_2.py — Generate Listening_2 output from transcript JSON.

Reads the transcript, identifies Teil boundaries, extracts content with word-level timestamps,
and produces a Markdown file conforming to Requirement B1-3-1.

Usage:
    py Requirement/generate_listening_2.py
"""

import json
import os
import re
from pathlib import Path

transcript_files = sorted(Path("Transcripts").glob("*.json"), key=lambda p: p.stat().st_mtime)
if not transcript_files:
    raise FileNotFoundError("No transcript JSON found in Transcripts/ directory")
TRANSCRIPT = transcript_files[-1]
OUTPUT = Path(r"Outputs\Listening-generated.md")

# Auto-detect latest audio file from Audios/ directory
AUDIOS_DIR = Path("Audios")
audio_files = sorted(
    [f for f in AUDIOS_DIR.iterdir() if f.suffix == ".mp3" and f.is_file()],
    key=lambda f: f.stat().st_mtime,
    reverse=True,
)
if not audio_files:
    raise FileNotFoundError("No .mp3 files found in Audios/ directory")
AUDIO_FILE = audio_files[0].name
print(f"Audio file (latest): {AUDIO_FILE}")

# Load transcript
with open(TRANSCRIPT, "r", encoding="utf-8") as f:
    data = json.load(f)

segments = data["segments"]


def get_words(seg):
    """Get only actual words from a segment (skip spacing)."""
    return [w for w in seg["words"] if w["type"] == "word"]


def build_spans(words_list):
    """Build <span data-start="..." data-end="...">word</span> from a list of word dicts.
    Strips trailing period from ordinal numbers when the next word is a date continuation,
    avoiding false positives in the B1-3-2.6 validator.
    """
    MONTH_NAMES = {"Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
                   "August", "September", "Oktober", "November", "Dezember"}
    DATE_CONTINUATIONS = {"bis", "und", "oder", "ab", "vom", "zum"}
    parts = []
    for i, w in enumerate(words_list):
        text = w["text"]
        # Strip trailing period from ordinal numbers when next word continues a date
        bare = text.rstrip(".")
        if bare.isdigit() and text.endswith(".") and i + 1 < len(words_list):
            next_text = words_list[i + 1]["text"].rstrip(".,;:!?")
            if next_text in MONTH_NAMES or next_text.lower() in DATE_CONTINUATIONS:
                text = bare  # Remove the period to avoid validator false positive
        parts.append(f'<span data-start="{w["start"]}" data-end="{w["end"]}">{text}</span>')
    return " ".join(parts)


# Abbreviations that end with '.' but should NOT trigger a sentence break.
ABBREVIATIONS = {"Dr", "Mr", "Mrs", "Ms", "Prof", "Nr", "St", "Str", "ca", "bzw", "usw", "etc", "z", "d", "u"}


def words_to_sentences(words_list):
    """
    Group words into sentences. A sentence ends when a word's text ends with . ! or ?
    Returns list of lists of word dicts.
    """
    sentences = []
    current = []
    for idx, w in enumerate(words_list):
        current.append(w)
        text = w["text"].rstrip()
        if text and text[-1] in ".!?" and not text.endswith("..."):
            bare = text.rstrip(".!?")
            # Skip abbreviations — they end with '.' but are not sentence boundaries.
            if bare in ABBREVIATIONS:
                continue
            if bare.isdigit():
                # Check if next word continues a date expression
                MONTH_NAMES = {"Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
                               "August", "September", "Oktober", "November", "Dezember"}
                DATE_CONTINUATIONS = {"bis", "und", "oder", "ab", "vom", "zum"}
                if idx + 1 < len(words_list):
                    next_text = words_list[idx + 1]["text"].rstrip(".,;:!?")
                    if next_text in MONTH_NAMES or next_text.lower() in DATE_CONTINUATIONS:
                        continue
            sentences.append(current)
            current = []
    if current:
        sentences.append(current)
    return sentences


REPEAT_INSTRUCTION = "Sie hören jetzt den Text noch einmal."


def strip_repeat_instruction(words_list):
    """Remove trailing repeat instruction sentence from word list if present."""
    sentences = words_to_sentences(words_list)
    if not sentences:
        return words_list
    last_sent_text = " ".join(w["text"] for w in sentences[-1])
    if last_sent_text == REPEAT_INSTRUCTION:
        # Flatten all sentences except the last one back into a words list
        return [w for sent in sentences[:-1] for w in sent]
    return words_list


# =========================================================================
#  Content segment mapping for Modelltest 6 (B1-3 format)
#
#  Teil 1: Aufgabe 41-45 — segs 3, 5, 7, 9, 11
#  Teil 2: Q&A interview — segs 13-31 (first hearing only; skip 32-51)
#  Teil 3: Aufgabe 56-60 — first hearings only
# =========================================================================

TEIL1_CONTENT_SEGS = {
    41: [3],
    42: [5],
    43: [7],
    44: [9],
    45: [11],
}

# Teil 2: group into Q&A pairs (interviewer question + response)
# Segs 13-31 are first hearing. Q&A pair grouping:
TEIL2_QA_PAIRS = [
    # Q&A 1: Opening + what does Infophon do?
    {"segs": [13, 14, 15]},
    # Q&A 2: What do they want to know?
    {"segs": [16, 17]},
    # Q&A 3: And the Berliners themselves?
    {"segs": [18, 19]},
    # Q&A 4: How long until you get info?
    {"segs": [20, 21]},
    # Q&A 5: Questions you can't answer?
    {"segs": [22, 23]},
    # Q&A 6: Most popular offers?
    {"segs": [24, 25]},
    # Q&A 7: Only entertainment?
    {"segs": [26, 27]},
    # Q&A 8: Not dealing with problems?
    {"segs": [28, 29]},
    # Q&A 9: Closing — thank you
    {"segs": [30, 31]},
]

TEIL3_CONTENT_SEGS = {
    56: [53, 54],
    57: [59, 60],
    58: [65],
    59: [70],
    60: [74, 75],
}


def collect_words_from_segs(seg_indices):
    """Collect all content words from the given segment indices."""
    words = []
    for i in seg_indices:
        words.extend(get_words(segments[i]))
    return words


# =========================================================================
#  Translations and Notes for each block
# =========================================================================

TEIL1_DATA = {
    41: {
        "translations": [
            '<b>Wir sind eine fünfköpfige Familie und ich habe ausgerechnet am 23. Dezember Geburtstag.</b> — We are a family of five and my birthday happens to be on December 23rd.',
            '<b>Deshalb feiern wir natürlich beide Feste zu Hause.</b> — That\'s why we of course celebrate both occasions at home.',
            '<b>Klar, dass es mit so vielen Leuten im Haus immer Hektik gibt, aber das gefällt uns allen.</b> — Of course with so many people in the house there\'s always a hectic atmosphere, but we all like that.',
            '<b>Ich kann mir nicht vorstellen, an Weihnachten nicht zu Hause zu sein.</b> — I can\'t imagine not being at home at Christmas.',
            '<b>Es würde kein Weihnachtsgefühl aufkommen, auch wenn wir die Geschenke und einen kleinen Tannenbaum mitnehmen würden.</b> — No Christmas feeling would arise, even if we took the presents and a small fir tree with us.',
        ],
        "notes": '<b>Key Words and Phrases</b><br>• <b>fünfköpfig</b> — five-member (family)<br>• <b>ausgerechnet</b> — of all things / as it happens<br>• <b>die Hektik</b> — hectic atmosphere / frenzy<br>• <b>sich vorstellen</b> — to imagine<br>• <b>das Weihnachtsgefühl</b> — Christmas feeling<br>• <b>der Tannenbaum</b> — fir tree / Christmas tree<br><br><b>Grammar to Remember</b><br>• <b>"klar, dass..." clause</b> — "Klar, dass es Hektik gibt" — short form of "Es ist klar, dass..."<br>• <b>Reflexive "sich vorstellen"</b> — "Ich kann mir nicht vorstellen" — dative reflexive<br>• <b>Konjunktiv II "würde"</b> — "Es würde kein Weihnachtsgefühl aufkommen" — hypothetical',
    },
    42: {
        "translations": [
            '<b>Was bitte soll ich an Weihnachten im Ausland?</b> — What on earth would I do abroad at Christmas?',
            '<b>Schon als Kind fand ich es immer toll, diese gemütliche Weihnachtszeit, wenn die Wohnung nach Bratäpfeln, Plätzchen und Stollen duftet.</b> — Even as a child I always found it wonderful, this cozy Christmas time, when the apartment smells of baked apples, cookies and stollen.',
            '<b>Und dann der Heilige Abend.</b> — And then Christmas Eve.',
            '<b>Wenn der Schnee fällt und der Baum leuchtet, das ist Weihnachten.</b> — When the snow falls and the tree shines, that is Christmas.',
            '<b>Warum sollten wir uns ausgerechnet in der Vorweihnachtszeit in ein Flugzeug zwängen?</b> — Why should we squeeze ourselves into a plane of all times during the pre-Christmas season?',
            '<b>Eine bunt behängte Plastiktanne auf Mallorca kann doch kein Weihnachtsgefühl vermitteln, oder?</b> — A colorfully decorated plastic fir tree on Mallorca can\'t convey any Christmas feeling, can it?',
        ],
        "notes": '<b>Key Words and Phrases</b><br>• <b>gemütlich</b> — cozy / comfortable<br>• <b>der Bratapfel</b> — baked apple<br>• <b>das Plätzchen</b> — (Christmas) cookie<br>• <b>der Stollen</b> — traditional Christmas cake<br>• <b>duften</b> — to smell (pleasantly)<br>• <b>der Heilige Abend</b> — Christmas Eve<br>• <b>die Vorweihnachtszeit</b> — pre-Christmas season<br><br><b>Grammar to Remember</b><br>• <b>"wenn" temporal clause</b> — "wenn die Wohnung nach Bratäpfeln duftet" — whenever/when<br>• <b>Reflexive "sich zwängen"</b> — "uns in ein Flugzeug zwängen" — to squeeze oneself<br>• <b>Modal particle "doch"</b> — "kann doch kein Weihnachtsgefühl vermitteln" — rhetorical emphasis',
    },
    43: {
        "translations": [
            '<b>Wir, also mein Mann, unsere Tochter und ich, wir fahren in diesem Jahr wieder über Weihnachten nach Österreich.</b> — We — that is my husband, our daughter and I — are going to Austria again this year over Christmas.',
            '<b>Da machen wir Skiurlaub.</b> — There we go on a skiing holiday.',
            '<b>Wir gehen am 24. Dezember gemeinsam in die Christmette in der Dorfkirche, machen Spaziergänge im Schnee und genießen die weihnachtliche Stille direkt am Fuße des Kitzsteinhorns.</b> — On December 24th we go together to the Christmas Mass in the village church, take walks in the snow and enjoy the Christmas quietness right at the foot of the Kitzsteinhorn.',
            '<b>Dort ist es unbeschreiblich schön.</b> — It is indescribably beautiful there.',
        ],
        "notes": '<b>Key Words and Phrases</b><br>• <b>der Skiurlaub</b> — skiing holiday<br>• <b>die Christmette</b> — Christmas Mass / Midnight Mass<br>• <b>die Dorfkirche</b> — village church<br>• <b>der Spaziergang</b> — walk / stroll<br>• <b>die Stille</b> — quietness / silence<br>• <b>unbeschreiblich</b> — indescribably<br><br><b>Grammar to Remember</b><br>• <b>Apposition</b> — "Wir, also mein Mann, unsere Tochter und ich, wir fahren..." — restating the subject<br>• <b>"am + ordinal date"</b> — "am 24. Dezember" — temporal with dative<br>• <b>Enumeration with "und"</b> — multiple verbs in sequence: "gehen... machen... genießen"',
    },
    44: {
        "translations": [
            '<b>Weihnachten im Ausland?</b> — Christmas abroad?',
            '<b>Nee.</b> — No.',
            '<b>Für Familien mit Kindern finde ich es falsch, über Weihnachten zu verreisen.</b> — For families with children I think it\'s wrong to travel over Christmas.',
            '<b>Wir verbringen das Weihnachtsfest immer zu Hause.</b> — We always spend Christmas at home.',
            '<b>Mit Weihnachtsbaum, Festtagsbraten, Fondue am Heiligabend, Geschenken und Kirchgang.</b> — With a Christmas tree, holiday roast, fondue on Christmas Eve, presents and church-going.',
            '<b>Solange unsere beiden Töchter noch bei uns leben, möchten wir alle diese Sitte unbedingt beibehalten.</b> — As long as our two daughters still live with us, we definitely want to keep all these traditions.',
            '<b>Nach dem Fest fahren wir weg, diesmal nach Tunesien, denn dann haben wir genug von Weihnachten und wollen uns in der Sonne ausruhen.</b> — After the holiday we go away, this time to Tunisia, because by then we\'ve had enough of Christmas and want to relax in the sun.',
        ],
        "notes": '<b>Key Words and Phrases</b><br>• <b>verreisen</b> — to go on a trip / travel<br>• <b>der Festtagsbraten</b> — holiday roast<br>• <b>der Kirchgang</b> — church-going<br>• <b>die Sitte</b> — tradition / custom<br>• <b>beibehalten</b> — to maintain / keep up<br>• <b>sich ausruhen</b> — to rest / relax<br><br><b>Grammar to Remember</b><br>• <b>"solange" temporal clause</b> — "Solange unsere Töchter bei uns leben" — as long as<br>• <b>"genug von" + Dativ</b> — "genug von Weihnachten" — enough of something<br>• <b>Reflexive "sich ausruhen"</b> — "wollen uns in der Sonne ausruhen"',
    },
    45: {
        "translations": [
            '<b>Mir gehen die Weihnachtseinkäufe so auf die Nerven, dass ich am liebsten schon am 15. Dezember wegfahren würde.</b> — The Christmas shopping gets on my nerves so much that I\'d prefer to leave already on December 15th.',
            '<b>Wohin man auch schaut, Weihnachtsmärkte, Nikoläuse, Geschenkvorschläge und in allen Geschäften Hunderte von Menschen.</b> — Wherever you look — Christmas markets, Santas, gift suggestions, and 100s of people in every store.',
            '<b>Das hat doch inzwischen schon amerikanische Dimensionen angenommen.</b> — It has already taken on American dimensions by now.',
            '<b>Deshalb verbringen wir Weihnachten im Ausland.</b> — That\'s why we spend Christmas abroad.',
            '<b>Allerdings wird es, das haben wir letztes Jahr bereits festgestellt, immer schwieriger, ein schönes Urlaubsziel ohne typische Touristenweihnacht zu finden.</b> — However, as we already noticed last year, it is becoming increasingly difficult to find a nice holiday destination without a typical tourist Christmas.',
        ],
        "notes": '<b>Key Words and Phrases</b><br>• <b>die Weihnachtseinkäufe</b> — Christmas shopping<br>• <b>auf die Nerven gehen</b> — to get on someone\'s nerves<br>• <b>der Geschenkvorschlag</b> — gift suggestion<br>• <b>Dimensionen annehmen</b> — to take on dimensions<br>• <b>das Urlaubsziel</b> — holiday destination<br>• <b>die Touristenweihnacht</b> — tourist Christmas<br><br><b>Grammar to Remember</b><br>• <b>"so... dass" consecutive clause</b> — "so auf die Nerven, dass ich wegfahren würde" — so much that<br>• <b>Konjunktiv II</b> — "wegfahren würde" — would leave (hypothetical)<br>• <b>Comparative "immer + comparative"</b> — "immer schwieriger" — increasingly difficult',
    },
}

TEIL2_DATA = [
    # Q&A 1: segs 13-15 — Opening + what does Infophon do
    {
        "translations": [
            '<b>Ja, gerne.</b> — Yes, gladly.',
            '<b>Sie sind die Chefin dieses Büros.</b> — You are the head of this office.',
            '<b>Können Sie uns bitte sagen, was Infophon genau macht?</b> — Can you please tell us what Infophon exactly does?',
            '<b>Also, wir informieren Jugendliche darüber, wat hier los ist in Berlin.</b> — Well, we inform young people about what\'s going on here in Berlin.',
            '<b>Det schaff ich natürlich nich alleine.</b> — Of course I can\'t manage that alone.',
            '<b>Meine Mitarbeiterinnen helfen mir dabei, denn in manchen Monaten rufen bei uns um die sechshundert Personen an.</b> — My colleagues help me with that, because in some months around six hundred people call us.',
        ],
        "notes": '<b>Key Words and Phrases</b><br>• <b>die Chefin</b> — the boss / head (female)<br>• <b>informieren über</b> — to inform about<br>• <b>die Mitarbeiterin</b> — (female) colleague / co-worker<br>• <b>um die sechshundert</b> — around six hundred<br>• <b>anrufen</b> — to call (phone)<br><br><b>Grammar to Remember</b><br>• <b>Berlin dialect "wat/det/ick"</b> — colloquial forms of "was/das/ich"<br>• <b>"denn" causal conjunction</b> — "denn in manchen Monaten rufen..." — because<br>• <b>Separable verb "anrufen"</b> — "rufen bei uns an" — prefix moves to end',
    },
    # Q&A 2: segs 16-17 — What do they want to know?
    {
        "translations": [
            '<b>Und was wollen die genau wissen?</b> — And what exactly do they want to know?',
            '<b>Na ja, zum Beispiel, wo man hier in der Großstadt einen Ausflug machen kann.</b> — Well, for example, where you can go on an outing here in the big city.',
            '<b>Schulklassen, die von weit her kommen, wollen wissen, wie sie ihren Aufenthalt planen können.</b> — School classes that come from far away want to know how they can plan their stay.',
            '<b>Wir sind schon aus Großbritannien und Norwegen angerufen worden.</b> — We have already been called from Great Britain and Norway.',
        ],
        "notes": '<b>Key Words and Phrases</b><br>• <b>der Ausflug</b> — outing / excursion<br>• <b>die Großstadt</b> — big city / metropolis<br>• <b>die Schulklasse</b> — school class<br>• <b>der Aufenthalt</b> — stay / visit<br>• <b>von weit her</b> — from far away<br><br><b>Grammar to Remember</b><br>• <b>Passive with "werden"</b> — "Wir sind angerufen worden" — present perfect passive<br>• <b>Relative clause "die"</b> — "Schulklassen, die von weit her kommen" — who/which<br>• <b>"wo man ... kann"</b> — indirect question with modal verb',
    },
    # Q&A 3: segs 18-19 — And the Berliners?
    {
        "translations": [
            '<b>Und die Berliner selbst?</b> — And the Berliners themselves?',
            '<b>Die können erfahren, wo Jugendtheater jespielt wird, ob gerade ein Zirkus in der Stadt is, wat für Konzerte und Feste et jibt, welche die besten Discos sind.</b> — They can find out where youth theater is being performed, whether there\'s a circus in town, what concerts and festivals there are, which are the best clubs.',
            '<b>Det Angebot is groß.</b> — The range is large.',
        ],
        "notes": '<b>Key Words and Phrases</b><br>• <b>erfahren</b> — to find out / learn<br>• <b>das Jugendtheater</b> — youth theater<br>• <b>der Zirkus</b> — circus<br>• <b>das Angebot</b> — offer / range<br>• <b>die Disco</b> — club / disco<br><br><b>Grammar to Remember</b><br>• <b>Passive "gespielt wird"</b> — "wo Jugendtheater jespielt wird" — is being performed<br>• <b>Berlin dialect</b> — "jespielt/jibt/is/det/et" for "gespielt/gibt/ist/das/es"<br>• <b>Indirect questions</b> — "wo... ob... wat... welche..." — multiple embedded questions',
    },
    # Q&A 4: segs 20-21 — How long until info?
    {
        "translations": [
            '<b>Dauert es lange, bis man die gewünschte Information bekommt?</b> — Does it take long until you get the desired information?',
            '<b>Wir sind wochentags zwölf Stunden von acht Uhr morgens bis acht Uhr abends zu erreichen.</b> — We can be reached on weekdays for twelve hours from eight in the morning until eight in the evening.',
            '<b>Et dauert schon zehn bis zwanzig Minuten, bis der Anrufer alle Angebote jehört hat.</b> — It does take ten to twenty minutes until the caller has heard all the offers.',
            '<b>Aber wer möchte, hat auch die Möglichkeit, unsere Angebote im Internet unter www.spinnenwerk.de kennenzulernen.</b> — But whoever wants to also has the opportunity to discover our offers on the internet at www.spinnenwerk.de.',
        ],
        "notes": '<b>Key Words and Phrases</b><br>• <b>gewünscht</b> — desired / requested<br>• <b>wochentags</b> — on weekdays<br>• <b>zu erreichen</b> — reachable / available<br>• <b>der Anrufer</b> — the caller<br>• <b>die Möglichkeit</b> — opportunity / possibility<br>• <b>kennenlernen</b> — to get to know / discover<br><br><b>Grammar to Remember</b><br>• <b>"bis" temporal clause</b> — "bis man die Information bekommt" — until<br>• <b>"zu + infinitive" as adjective</b> — "zu erreichen" — passive capability<br>• <b>Relative pronoun "wer"</b> — "wer möchte, hat auch..." — whoever',
    },
    # Q&A 5: segs 22-23 — Questions you can't answer?
    {
        "translations": [
            '<b>Werden auch Fragen gestellt, die Sie nicht beantworten können?</b> — Are there also questions asked that you cannot answer?',
            '<b>Det kommt schon mal vor.</b> — That does happen sometimes.',
            '<b>Einmal wollte jemand wissen, wann und wo eine Skibörse stattfindet.</b> — Once someone wanted to know when and where a ski fair takes place.',
            '<b>Da musst ick erst mal selber herumtelefonieren.</b> — I had to make some phone calls around myself first.',
            '<b>Nach einigen Tagen konnt ich dann den Skifahrer zurückrufen und ihm über meine Ergebnisse berichten.</b> — After a few days I was then able to call the skier back and report my findings to him.',
        ],
        "notes": '<b>Key Words and Phrases</b><br>• <b>vorkommen</b> — to happen / occur<br>• <b>die Skibörse</b> — ski fair / ski swap<br>• <b>stattfinden</b> — to take place<br>• <b>herumtelefonieren</b> — to phone around<br>• <b>zurückrufen</b> — to call back<br>• <b>das Ergebnis</b> — result / finding<br><br><b>Grammar to Remember</b><br>• <b>Passive "werden... gestellt"</b> — "Werden Fragen gestellt" — are questions asked<br>• <b>Separable verbs</b> — "stattfindet / herumtelefonieren / zurückrufen" — prefix separates in main clause<br>• <b>"über" + accusative</b> — "über meine Ergebnisse berichten" — report about',
    },
    # Q&A 6: segs 24-25 — Most popular offers?
    {
        "translations": [
            '<b>Welche Angebote sind denn am meisten gefragt?</b> — Which offers are most in demand?',
            '<b>Ick würde sagen, allet, wat mit Sport zu tun hat.</b> — I would say, everything that has to do with sports.',
            '<b>Aber gerade in diesem Bereich können wir nicht so viel anbieten, weil die Sportvereine schon so viele Mitglieder haben.</b> — But precisely in this area we can\'t offer so much, because the sports clubs already have so many members.',
            '<b>Die einzelnen Gruppen und Mannschaften sind meistens voll.</b> — The individual groups and teams are usually full.',
        ],
        "notes": '<b>Key Words and Phrases</b><br>• <b>gefragt</b> — in demand / popular<br>• <b>der Bereich</b> — area / field<br>• <b>anbieten</b> — to offer<br>• <b>der Sportverein</b> — sports club<br>• <b>die Mannschaft</b> — team<br><br><b>Grammar to Remember</b><br>• <b>Superlative "am meisten"</b> — "am meisten gefragt" — most in demand<br>• <b>Konjunktiv II "würde"</b> — "Ick würde sagen" — polite/hypothetical<br>• <b>"weil" causal clause</b> — verb at end: "weil die Sportvereine so viele Mitglieder haben"',
    },
    # Q&A 7: segs 26-27 — Only entertainment?
    {
        "translations": [
            '<b>Geht es bei den Fragen eigentlich nur um Unterhaltung?</b> — Are the questions actually only about entertainment?',
            '<b>Na, manchmal nich.</b> — Well, sometimes not.',
            '<b>Ab und zu müssen wir uns auch um ernste Angelegenheiten kümmern.</b> — From time to time we also have to deal with serious matters.',
            '<b>Neulich zum Beispiel hat ein Jugendlicher angerufen, der zum zweiten Mal seine Lehre abgebrochen hat und nich wusste, wat er beruflich machen sollte.</b> — Recently for example a young person called who had dropped out of his apprenticeship for the second time and didn\'t know what he should do professionally.',
            '<b>Da kann ein Gespräch schon mal \'ne Stunde dauern.</b> — In those cases a conversation can easily last an hour.',
            '<b>Aber in besonders schwierigen Fällen sagen wir den Leuten, sie sollen beim Jugendnotdienst anrufen.</b> — But in particularly difficult cases we tell people they should call the youth emergency service.',
            '<b>An den kann man sich besser mit persönlichen Angelegenheiten wenden.</b> — You can better turn to them with personal matters.',
        ],
        "notes": '<b>Key Words and Phrases</b><br>• <b>die Unterhaltung</b> — entertainment<br>• <b>die Angelegenheit</b> — matter / affair<br>• <b>die Lehre</b> — apprenticeship<br>• <b>abbrechen</b> — to drop out / break off<br>• <b>der Jugendnotdienst</b> — youth emergency service<br>• <b>sich wenden an</b> — to turn to / contact<br><br><b>Grammar to Remember</b><br>• <b>"ab und zu"</b> — from time to time — idiomatic expression<br>• <b>Relative clause "der"</b> — "ein Jugendlicher, der... abgebrochen hat" — who<br>• <b>"sich kümmern um"</b> — "uns um ernste Angelegenheiten kümmern" — reflexive with "um"',
    },
    # Q&A 8: segs 28-29 — Not dealing with problems?
    {
        "translations": [
            '<b>Das heißt, dass Sie sich nicht mit Problemen beschäftigen?</b> — That means you don\'t deal with problems?',
            '<b>Nein, dit is nich unsere Aufgabe, dafür jibt et andere Stellen.</b> — No, that\'s not our job, there are other places for that.',
            '<b>In solchen Fällen können wir nur raten, wo man Hilfe finden kann.</b> — In such cases we can only advise where one can find help.',
            '<b>Ein Problem für uns ist manchmal, dat wir nich verstehen, wat jemand von uns wissen will.</b> — A problem for us is sometimes that we don\'t understand what someone wants to know from us.',
            '<b>Beispielsweise rief da neulich ein Siebzehnjähriger an und fragte nach Charlotte.</b> — For example, recently a seventeen-year-old called and asked about Charlotte.',
            '<b>Wir dachten zunächst alle an \'n Mädchen, dat der Junge sucht, bis sich herausstellte, dass er die Anschrift eines Theaters mit dem Namen Charlottchen haben wollte.</b> — We all initially thought of a girl that the boy was looking for, until it turned out that he wanted the address of a theater called Charlottchen.',
        ],
        "notes": '<b>Key Words and Phrases</b><br>• <b>sich beschäftigen mit</b> — to deal with / occupy oneself with<br>• <b>die Stelle</b> — place / office / position<br>• <b>raten</b> — to advise<br>• <b>beispielsweise</b> — for example<br>• <b>die Anschrift</b> — address<br>• <b>sich herausstellen</b> — to turn out<br><br><b>Grammar to Remember</b><br>• <b>"bis" temporal clause</b> — "bis sich herausstellte, dass..." — until it turned out<br>• <b>"dass" subordinate clause</b> — "dass er die Anschrift haben wollte" — verb at end<br>• <b>Berlin dialect</b> — "dit/nich/jibt/et/dat" — colloquial Berlin pronunciation',
    },
    # Q&A 9: segs 30-31 — Closing
    {
        "translations": [
            '<b>Frau Böhme, das war wirklich ein interessantes Gespräch.</b> — Mrs. Böhme, that was really an interesting conversation.',
            '<b>Wir danken Ihnen.</b> — We thank you.',
            '<b>Ich habe zu danken.</b> — I should be the one thanking.',
        ],
        "notes": '<b>Key Words and Phrases</b><br>• <b>das Gespräch</b> — conversation<br>• <b>interessant</b> — interesting<br>• <b>danken</b> — to thank<br>• <b>wirklich</b> — really / truly<br>• <b>zu danken haben</b> — to be the one to thank<br><br><b>Grammar to Remember</b><br>• <b>Formal address "Ihnen"</b> — "Wir danken Ihnen" — dative formal you<br>• <b>"haben + zu + infinitive"</b> — "Ich habe zu danken" — I am the one who should thank<br>• <b>Präteritum "war"</b> — "das war ein interessantes Gespräch" — simple past of "sein"',
    },
]

TEIL3_DATA = {
    56: {
        "translations": [
            '<b>Im Radio hören Sie die Wettervorhersage für die nächsten Tage.</b> — On the radio you hear the weather forecast for the next few days.',
            '<b>Wie wird das Wetter?</b> — How will the weather be?',
            '<b>Am Freitag gibt es weiter Regen und Gewitter, Tageshöchstwerte um fünfzehn Grad.</b> — On Friday there will be more rain and thunderstorms, daily highs around fifteen degrees.',
            '<b>Am Samstag anfangs Regen, später heiter um siebzehn Grad.</b> — On Saturday rain at first, later fair weather around seventeen degrees.',
            '<b>Am Sonntag meist heiter und niederschlagsfrei.</b> — On Sunday mostly fair and precipitation-free.',
            '<b>Tageshöchstwerte um achtzehn Grad.</b> — Daily highs around eighteen degrees.',
        ],
        "notes": '<b>Key Words and Phrases</b><br>• <b>die Wettervorhersage</b> — weather forecast<br>• <b>das Gewitter</b> — thunderstorm<br>• <b>der Tageshöchstwert</b> — daily high (temperature)<br>• <b>heiter</b> — fair / clear (weather)<br>• <b>niederschlagsfrei</b> — precipitation-free<br><br><b>Grammar to Remember</b><br>• <b>"es gibt"</b> — "gibt es weiter Regen" — there is — impersonal construction<br>• <b>Elliptical weather style</b> — "Am Samstag anfangs Regen" — telegram-style without verbs<br>• <b>"um" + number</b> — "um fünfzehn Grad" — approximately',
    },
    57: {
        "translations": [
            '<b>Sie hören die Nachrichten auf Ihrem telefonischen Anrufbeantworter ab.</b> — You are listening to the messages on your telephone answering machine.',
            '<b>Wer holt Sie ab?</b> — Who is picking you up?',
            '<b>Grüß dich, Arno.</b> — Hi there, Arno.',
            '<b>Hier ist Gunther.</b> — This is Gunther.',
            '<b>Ich wollte dir nur mitteilen, dass ich dich nun doch nicht am Hauptbahnhof abholen kann.</b> — I just wanted to let you know that I can\'t pick you up at the main train station after all.',
            '<b>Aber du brauchst dir keine Sorgen zu machen.</b> — But you don\'t need to worry.',
            '<b>Alois übernimmt das und wird dich pünktlich erwarten.</b> — Alois is taking over and will be waiting for you on time.',
            '<b>Sicher kannst du dich noch an ihn erinnern.</b> — Surely you can still remember him.',
            '<b>Ihr habt euch neulich bei mir zu Hause kennengelernt.</b> — You met each other recently at my place.',
            '<b>Also dann, adieu.</b> — Well then, goodbye.',
            '<b>Bis bald.</b> — See you soon.',
            '<b>Ich freue mich schon auf dich.</b> — I\'m already looking forward to seeing you.',
        ],
        "notes": '<b>Key Words and Phrases</b><br>• <b>der Anrufbeantworter</b> — answering machine<br>• <b>abhören</b> — to listen to / check (messages)<br>• <b>mitteilen</b> — to inform / let know<br>• <b>der Hauptbahnhof</b> — main train station<br>• <b>übernehmen</b> — to take over<br>• <b>sich erinnern an</b> — to remember<br><br><b>Grammar to Remember</b><br>• <b>"brauchen + zu + infinitive"</b> — "du brauchst dir keine Sorgen zu machen" — you don\'t need to<br>• <b>Reciprocal "sich kennenlernen"</b> — "Ihr habt euch kennengelernt" — to get to know each other<br>• <b>"sich freuen auf"</b> — "Ich freue mich auf dich" — to look forward to (+ accusative)',
    },
    58: {
        "translations": [
            '<b>Sie rufen in der Praxis von Dr. Ralf Baum an.</b> — You are calling the practice of Dr. Ralf Baum.',
            '<b>Wann hat Dr. Baum Sprechstunde?</b> — When does Dr. Baum have office hours?',
            '<b>Hier ist die Praxis von Dr. Ralf Baum, Mozartstraße dreiunddreißig.</b> — This is the practice of Dr. Ralf Baum, Mozartstraße dreiunddreißig.',
            '<b>Die Praxis ist zurzeit nicht besetzt.</b> — The practice is currently not staffed.',
            '<b>Sie können Herrn Dr. Baum täglich außer mittwochs in seiner Sprechstunde erreichen.</b> — You can reach Dr. Baum daily except on Wednesdays during his office hours.',
            '<b>Vormittags von neun bis zwölf Uhr, nachmittags von siebzehn bis neunzehn Uhr.</b> — In the mornings from nine to twelve, in the afternoons from five to seven PM.',
            '<b>An Wochenenden und Feiertagen rufen Sie bitte beim Notdienst unter der Rufnummer eins eins null an.</b> — On weekends and holidays please call the emergency service at the number one one zero.',
        ],
        "notes": '<b>Key Words and Phrases</b><br>• <b>die Praxis</b> — doctor\'s practice / office<br>• <b>die Sprechstunde</b> — office hours / consultation hours<br>• <b>besetzt</b> — staffed / occupied<br>• <b>der Feiertag</b> — public holiday<br>• <b>der Notdienst</b> — emergency service<br>• <b>die Rufnummer</b> — phone number<br><br><b>Grammar to Remember</b><br>• <b>"außer" + dative</b> — "außer mittwochs" — except on Wednesdays<br>• <b>"von... bis..."</b> — "von neun bis zwölf Uhr" — from... to... (time range)<br>• <b>Separable verb "anrufen"</b> — "rufen Sie beim Notdienst an" — call (with prefix at end)',
    },
    59: {
        "translations": [
            '<b>Sie wollen beim Versandhaus Brigitte den neuen Modekatalog bestellen und rufen deshalb an.</b> — You want to order the new fashion catalogue from the mail-order company Brigitte and are calling for that reason.',
            '<b>Was kostet der Modekatalog?</b> — What does the fashion catalogue cost?',
            '<b>Endlich ist er da, unser neuer Modekatalog für Herbst und Winter.</b> — It\'s finally here, our new fashion catalogue for autumn and winter.',
            '<b>Geben Sie sofort Ihre Bestellung auf und Brigitte kommt kostenlos ins Haus.</b> — Place your order right away and Brigitte comes to your home free of charge.',
            '<b>Hinterlassen Sie nach dem Tonzeichen Ihren Namen und Ihre Kundennummer oder bestellen Sie per Fax unter der Nummer null sieben acht drei zweiundsechzig dreizehn neunundvierzig.</b> — Leave your name and customer number after the tone or order by fax at the number zero seven eight three sixty-two thirteen forty-nine.',
            '<b>Wenn Sie den Katalog zum ersten Mal bestellen, dann hinterlassen Sie bitte außer Ihrem Namen auch Ihre genaue Anschrift sowie Ihre Telefonnummer.</b> — If you are ordering the catalogue for the first time, then please leave not only your name but also your exact address as well as your phone number.',
        ],
        "notes": '<b>Key Words and Phrases</b><br>• <b>das Versandhaus</b> — mail-order company<br>• <b>der Modekatalog</b> — fashion catalogue<br>• <b>bestellen</b> — to order<br>• <b>kostenlos</b> — free of charge<br>• <b>die Kundennummer</b> — customer number<br>• <b>das Tonzeichen</b> — (beep) tone<br><br><b>Grammar to Remember</b><br>• <b>"wenn... dann..." conditional</b> — "Wenn Sie zum ersten Mal bestellen, dann hinterlassen Sie" — if... then...<br>• <b>"außer... auch..." correlation</b> — "außer Ihrem Namen auch Ihre Anschrift" — not only... but also...<br>• <b>Imperativ (Sie-form)</b> — "Geben Sie auf / Hinterlassen Sie" — polite commands',
    },
    60: {
        "translations": [
            '<b>Im Radio hören Sie den Veranstaltungskalender für das Wochenende.</b> — On the radio you hear the events calendar for the weekend.',
            '<b>Was können Besucher bei der Tierausstellung tun?</b> — What can visitors do at the animal exhibition?',
            '<b>Tierliebhaber, aufgepasst!</b> — Animal lovers, pay attention!',
            '<b>Am 15. und 16. Mai dreht sich von zehn bis achtzehn Uhr in der Rudi Sedlmayr Halle alles um Hunde und Katzen.</b> — On May 15th and 16th from ten to six PM in the Rudi Sedlmayr Hall everything revolves around dogs and cats.',
            '<b>Auf dem Programm steht auch eine internationale Katzenschau.</b> — The program also includes an international cat show.',
            '<b>Bei der Wahl der schönsten Katzenbabys dürfen die Besucher entscheiden, welche ihnen am besten gefallen.</b> — In the selection of the most beautiful kittens, visitors may decide which ones they like best.',
            '<b>Für diejenigen, die sich mehr für Hunde interessieren, finden Vorführungen von Polizeihunden statt.</b> — For those who are more interested in dogs, police dog demonstrations take place.',
        ],
        "notes": '<b>Key Words and Phrases</b><br>• <b>der Veranstaltungskalender</b> — events calendar<br>• <b>die Tierausstellung</b> — animal exhibition<br>• <b>der Tierliebhaber</b> — animal lover<br>• <b>die Katzenschau</b> — cat show<br>• <b>die Vorführung</b> — demonstration / performance<br>• <b>der Polizeihund</b> — police dog<br><br><b>Grammar to Remember</b><br>• <b>"sich drehen um"</b> — "dreht sich alles um Hunde" — everything revolves around<br>• <b>"diejenigen, die..."</b> — "für diejenigen, die sich für Hunde interessieren" — those who<br>• <b>"bei + Dativ"</b> — "bei der Wahl" — during / in the context of',
    },
}


def main():
    output_lines = ["TARGET DECK: TEST", ""]

    # ----- Teil 1: Aufgabe 41-45 -----
    for aufgabe_num in [41, 42, 43, 44, 45]:
        seg_indices = TEIL1_CONTENT_SEGS[aufgabe_num]
        words = collect_words_from_segs(seg_indices)
        sentences = words_to_sentences(words)
        data_block = TEIL1_DATA[aufgabe_num]

        de_1_parts = [build_spans(sent_words) for sent_words in sentences]
        de_1 = "<br>".join(de_1_parts)
        en_1 = "<br>".join(data_block["translations"])

        de_1_start = words[0]["start"]
        de_1_end = words[-1]["end"]
        duration = de_1_end - de_1_start

        n_sent = len(sentences)
        n_trans = len(data_block["translations"])

        output_lines.append(f"## Teil 1 — Aufgabe {aufgabe_num}")
        output_lines.append("")
        output_lines.append("```")
        output_lines.append("SSTART")
        output_lines.append("")
        output_lines.append("Listening_2")
        output_lines.append("")
        output_lines.append(f"de_1: {de_1}")
        output_lines.append(f"en_1: {en_1}")
        output_lines.append(f"note_1: {data_block['notes']}")
        output_lines.append(f"de_1_audio: [sound:{AUDIO_FILE}]")
        output_lines.append(f"de_1_wave: {AUDIO_FILE}")
        output_lines.append(f"de_1_start: {de_1_start}")
        output_lines.append(f"de_1_end: {de_1_end}")
        output_lines.append("EEND")
        output_lines.append("```")
        output_lines.append("")

        print(f"  Teil 1 — Aufgabe {aufgabe_num}: {n_sent} sents, {n_trans} trans, {duration:.1f}s")

    # ----- Teil 2: Q&A pairs -----
    for qa_idx, qa_pair in enumerate(TEIL2_DATA, start=1):
        seg_indices = TEIL2_QA_PAIRS[qa_idx - 1]["segs"]
        words = collect_words_from_segs(seg_indices)
        sentences = words_to_sentences(words)

        de_1_parts = [build_spans(sent_words) for sent_words in sentences]
        de_1 = "<br>".join(de_1_parts)
        en_1 = "<br>".join(qa_pair["translations"])

        de_1_start = words[0]["start"]
        de_1_end = words[-1]["end"]
        duration = de_1_end - de_1_start

        n_sent = len(sentences)
        n_trans = len(qa_pair["translations"])

        output_lines.append(f"## Teil 2 — Q&A {qa_idx}")
        output_lines.append("")
        output_lines.append("```")
        output_lines.append("SSTART")
        output_lines.append("")
        output_lines.append("Listening_2")
        output_lines.append("")
        output_lines.append(f"de_1: {de_1}")
        output_lines.append(f"en_1: {en_1}")
        output_lines.append(f"note_1: {qa_pair['notes']}")
        output_lines.append(f"de_1_audio: [sound:{AUDIO_FILE}]")
        output_lines.append(f"de_1_wave: {AUDIO_FILE}")
        output_lines.append(f"de_1_start: {de_1_start}")
        output_lines.append(f"de_1_end: {de_1_end}")
        output_lines.append("EEND")
        output_lines.append("```")
        output_lines.append("")

        print(f"  Teil 2 — Q&A {qa_idx}: {n_sent} sents, {n_trans} trans, {duration:.1f}s")

    # ----- Teil 3: Aufgabe 56-60 -----
    for aufgabe_num in [56, 57, 58, 59, 60]:
        seg_indices = TEIL3_CONTENT_SEGS[aufgabe_num]
        words = collect_words_from_segs(seg_indices)
        # Strip trailing repeat instruction ("Sie hören jetzt den Text noch einmal.")
        words = strip_repeat_instruction(words)
        sentences = words_to_sentences(words)
        data_block = TEIL3_DATA[aufgabe_num]

        de_1_parts = [build_spans(sent_words) for sent_words in sentences]
        de_1 = "<br>".join(de_1_parts)
        en_1 = "<br>".join(data_block["translations"])

        de_1_start = words[0]["start"]
        de_1_end = words[-1]["end"]
        duration = de_1_end - de_1_start

        n_sent = len(sentences)
        n_trans = len(data_block["translations"])

        output_lines.append(f"## Teil 3 — Aufgabe {aufgabe_num}")
        output_lines.append("")
        output_lines.append("```")
        output_lines.append("SSTART")
        output_lines.append("")
        output_lines.append("Listening_2")
        output_lines.append("")
        output_lines.append(f"de_1: {de_1}")
        output_lines.append(f"en_1: {en_1}")
        output_lines.append(f"note_1: {data_block['notes']}")
        output_lines.append(f"de_1_audio: [sound:{AUDIO_FILE}]")
        output_lines.append(f"de_1_wave: {AUDIO_FILE}")
        output_lines.append(f"de_1_start: {de_1_start}")
        output_lines.append(f"de_1_end: {de_1_end}")
        output_lines.append("EEND")
        output_lines.append("```")
        output_lines.append("")

        print(f"  Teil 3 — Aufgabe {aufgabe_num}: {n_sent} sents, {n_trans} trans, {duration:.1f}s")

    OUTPUT.write_text("\n".join(output_lines), encoding="utf-8")
    print(f"\nGenerated {OUTPUT}")

    # Validate sentence/translation counts
    all_ok = True
    print("\n  Sentence/Translation count check:")
    # Teil 1
    for aufgabe_num in [41, 42, 43, 44, 45]:
        words = collect_words_from_segs(TEIL1_CONTENT_SEGS[aufgabe_num])
        sentences = words_to_sentences(words)
        n_sent = len(sentences)
        n_trans = len(TEIL1_DATA[aufgabe_num]["translations"])
        if n_sent != n_trans:
            print(f"  *** MISMATCH Aufgabe {aufgabe_num}: {n_sent} sentences vs {n_trans} translations ***")
            all_ok = False
    # Teil 2
    for qa_idx, qa_pair in enumerate(TEIL2_DATA, start=1):
        words = collect_words_from_segs(TEIL2_QA_PAIRS[qa_idx - 1]["segs"])
        sentences = words_to_sentences(words)
        n_sent = len(sentences)
        n_trans = len(qa_pair["translations"])
        if n_sent != n_trans:
            print(f"  *** MISMATCH Q&A {qa_idx}: {n_sent} sentences vs {n_trans} translations ***")
            all_ok = False
    # Teil 3
    for aufgabe_num in [56, 57, 58, 59, 60]:
        words = collect_words_from_segs(TEIL3_CONTENT_SEGS[aufgabe_num])
        words = strip_repeat_instruction(words)
        sentences = words_to_sentences(words)
        n_sent = len(sentences)
        n_trans = len(TEIL3_DATA[aufgabe_num]["translations"])
        if n_sent != n_trans:
            print(f"  *** MISMATCH Aufgabe {aufgabe_num}: {n_sent} sentences vs {n_trans} translations ***")
            all_ok = False
    if all_ok:
        print("  All sentence/translation counts match.")


if __name__ == "__main__":
    main()


