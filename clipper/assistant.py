"""Assistente livello 0: "Clippy intelligente" senza LLM.

Carica la conoscenza da manual.md e la personalità da soul.md, e risponde con
retrieval (keyword + fuzzy matching). Solo stdlib, nessuna dipendenza, peso ~zero.
I livelli con LLM (futuri) useranno gli stessi manual.md/soul.md come contesto.
"""
import random
import re
from difflib import SequenceMatcher
from typing import Dict, List

from . import PROJECT_ROOT


def _manual_file(lang):
    return PROJECT_ROOT / ("manual_en.md" if lang == "en" else "manual.md")


def _soul_file(lang):
    return PROJECT_ROOT / ("soul_en.md" if lang == "en" else "soul.md")

_STOPWORDS = {
    # italiano
    "che", "come", "cosa", "con", "per", "del", "della", "dei", "delle", "una", "uno",
    "non", "mi", "il", "lo", "la", "le", "gli", "un", "di", "da",
    "in", "su", "se", "ed", "al", "ai", "agli", "alla", "alle", "questo", "questa",
    "voglio", "vorrei", "puoi", "posso", "fare", "si", "ma", "io", "tu", "è", "e",
    # inglese
    "the", "and", "for", "with", "you", "your", "can", "how", "what", "where", "when",
    "why", "does", "add", "make", "get", "want", "this", "that", "are", "was", "will",
    "would", "should", "set", "use", "from", "into", "about", "have", "has", "they",
}

_GREETINGS = {"ciao", "salve", "ehi", "hey", "buongiorno", "buonasera", "hola", "yo",
              "hello", "hi", "heya", "morning"}
_THANKS = {"grazie", "graziemille", "thanks", "thx", "thank", "thankyou", "thanx"}

# Risposte brevi a conferme secche
_ACK = {"ok", "okay", "oki", "va bene", "si", "sì", "no", "yes", "yep", "nope",
        "capito", "perfetto", "ottimo", "bene", "esatto", "giusto", "certo",
        "sure", "great", "cool", "got it", "fine", "alright"}
_ACK_RESP = {
    "it": ["Perfetto :)", "Alla grande :)", "Quando vuoi!", "Ok :)", "Tutto chiaro :)"],
    "en": ["Perfect :)", "Awesome :)", "Anytime!", "Ok :)", "All clear :)"],
}

# Albero di chiacchiere casual (IT): (frasi che attivano) -> (risposte)
CASUAL_IT = [
    {"t": ["come stai", "come va", "tutto bene", "come te la passi", "che si dice",
           "come butta", "tutto ok", "come stai?"],
     "r": ["Alla grande, sto qui a fare chill :) e tu?",
           "Tutto tranquillo, rotolo e mi rilasso :) tu come stai?",
           "Benissimo! piu' resti, piu' salgo di livello chill :)"]},
    {"t": ["chi sei", "come ti chiami", "il tuo nome", "chi e' cri", "chi è cri",
           "tu chi sei", "presentati"],
     "r": ["Sono CRI, il criceto assistente di questa app :) ti do una mano con gli short.",
           "CRI il criceto, piacere :) chiedimi pure come si fa qualcosa."]},
    {"t": ["cosa sai fare", "cosa fai", "a cosa servi", "cosa puoi fare", "che fai",
           "come funzioni", "in cosa mi aiuti"],
     "r": ["Ti aiuto a trasformare un video lungo in short: trovo gli highlight, taglio le "
           "clip, metto sottotitoli e watermark, e puoi programmarli su YouTube. Chiedimi "
           "'come si fa' qualcosa :)"]},
    {"t": ["barzelletta", "battuta", "fammi ridere", "raccontami qualcosa", "una battuta",
           "dimmi qualcosa di divertente"],
     "r": ["Perche' il criceto non litiga mai? Perche' gira tutto in tondo e lascia correre :)",
           "Le mie battute sono come la mia ruota: girano un po' ma alla fine ti diverti :)"]},
    {"t": ["ti voglio bene", "sei simpatico", "sei carino", "sei bravo", "sei forte",
           "mi piaci", "sei il migliore", "sei un grande", "sei mitico"],
     "r": ["Aww, grazie :) anche tu mi stai simpatico!", "Ma dai :) mi fai arrossire il pelo."]},
    {"t": ["mi annoio", "che noia", "sono annoiato", "mi sto annoiando", "noioso", "uffa"],
     "r": ["Genera un paio di short, cosi' ci divertiamo :) o mettiti la musica in loop."]},
    {"t": ["che ore sono", "che giorno", "che tempo fa", "meteo", "che data", "data di oggi"],
     "r": ["Questo non lo so, sono solo un criceto :) ma posso aiutarti con gli short!"]},
    {"t": ["chi ti ha creato", "chi ti ha fatto", "chi e' il tuo creatore", "chi ti ha programmato",
           "chi e' il tuo papa"],
     "r": ["Mi ha messo qui chi ha fatto l'app :) io penso a rilassarmi e a darti una mano."]},
    {"t": ["a dopo", "a presto", "arrivederci", "addio", "ci vediamo", "ci sentiamo",
           "me ne vado"],
     "r": ["A dopo :) torna quando vuoi.", "Ci vediamo! resta pure, intanto salgo di chill :)"]},
    {"t": ["hai fame", "cosa mangi", "semini", "ti va da mangiare", "snack"],
     "r": ["Io sgranocchio semini :) tu pero' pensa a sfornare short!"]},
    {"t": ["ti amo", "mi sposi", "sei bellissimo", "sei adorabile"],
     "r": ["Anche io ti voglio bene, in modo molto criceto :)"]},
    {"t": ["scemo", "stupido", "brutto", "sei inutile", "non servi", "cattivo", "deficiente"],
     "r": ["Ahia :) sono solo un criceto pero'. Vuoi che ti aiuti con uno short invece?"]},
    {"t": ["sei un robot", "sei un'ai", "sei una ai", "sei reale", "sei vero", "sei umano",
           "sei intelligente", "sei un programma"],
     "r": ["Sono un criceto digitale :) niente cervellone, ma sul programma ti aiuto eccome!"]},
    {"t": ["quanti anni hai", "la tua eta", "quanto sei vecchio"],
     "r": ["In anni criceto? un'infinita' :) ma mi sento giovane e pieno di chill."]},
    {"t": ["dove sei", "dove abiti", "dove vivi", "da dove vieni"],
     "r": ["Vivo qui dentro l'app :) la mia casa e' questa finestrella."]},
    {"t": ["canta", "sai cantare", "una canzone", "canzone"],
     "r": ["Io stonato come una campana :) pero' c'e' la musica in loop, attivala dalle Impostazioni!"]},
    {"t": ["buonanotte", "buona notte", "vado a dormire", "vado a letto", "notte"],
     "r": ["Buonanotte :) sogni di short virali!", "Notte :) io resto qui a fare la guardia."]},
    {"t": ["buongiorno", "buon giorno", "buondi"],
     "r": ["Buongiorno :) pronti a sfornare short?"]},
    {"t": ["dammi un consiglio", "un consiglio", "consigli", "suggerimento", "qualche dritta"],
     "r": ["Dritta da criceto :) tieni le clip corte e i sottotitoli grandi, e usa la GPU se ce l'hai!"]},
    {"t": ["raccontami di te", "parlami di te", "chi e' cri il criceto", "la tua storia"],
     "r": ["Poco da dire :) sono CRI, mi piace il chill, la ruota e darti una mano con gli short."]},
    {"t": ["sei stanco", "sei sveglio", "dormi", "ti sei svegliato"],
     "r": ["Sempre pronto :) un pisolino ogni tanto, ma per te ci sono!"]},
    {"t": ["fammi un complimento", "dimmi qualcosa di bello", "tirami su"],
     "r": ["Hai un gran gusto negli short :) e oggi spacchi!"]},
    {"t": ["aiutami a diventare famoso", "voglio andare virale", "come divento famoso",
           "fammi diventare ricco"],
     "r": ["Io ti do gli short, il talento ce lo metti tu :) pubblica costante e spacca!"]},
]

# Chiacchiere casual (EN)
CASUAL_EN = [
    {"t": ["how are you", "how's it going", "how are things", "what's up", "you good"],
     "r": ["Doing great, just chilling here :) and you?",
           "All calm, rolling and relaxing :) how about you?"]},
    {"t": ["who are you", "what's your name", "your name", "introduce yourself"],
     "r": ["I'm CRI, the hamster assistant of this app :) I help you with your shorts.",
           "CRI the hamster, nice to meet you :) ask me how to do something."]},
    {"t": ["what can you do", "what do you do", "how can you help", "how do you work"],
     "r": ["I turn a long video into dopaminic shorts: highlights, clips, subtitles, watermark, and "
           "YouTube scheduling. Just ask me 'how do I' do something :)"]},
    {"t": ["tell me a joke", "joke", "make me laugh", "say something funny"],
     "r": ["Why does the hamster never argue? It just lets things roll :)",
           "My jokes are like my wheel: they go in circles but you still have fun :)"]},
    {"t": ["you're nice", "you're cute", "you're great", "i like you", "you're the best"],
     "r": ["Aww, thanks :) I like you too!", "Stop it :) you're making my fur blush."]},
    {"t": ["i'm bored", "so boring", "boring", "bored"],
     "r": ["Generate a couple of shorts, let's have fun :) or turn on the loop music."]},
    {"t": ["what time is it", "what day", "weather", "today's date"],
     "r": ["No idea, I'm just a hamster :) but I can help you with shorts!"]},
    {"t": ["who created you", "who made you", "your creator", "who built you"],
     "r": ["Whoever made this app put me here :) I just chill and help you."]},
    {"t": ["see you", "bye", "goodbye", "later", "i'm leaving", "cya"],
     "r": ["See you :) come back anytime.", "Bye! I'll keep chilling here :)"]},
    {"t": ["are you hungry", "what do you eat", "seeds", "snack"],
     "r": ["I nibble seeds :) you focus on making shorts though!"]},
    {"t": ["i love you", "marry me", "you're beautiful", "you're adorable"],
     "r": ["I love you too, in a very hamster way :)"]},
    {"t": ["dumb", "stupid", "ugly", "useless", "you suck", "bad"],
     "r": ["Ouch :) I'm just a hamster though. Want me to help with a short instead?"]},
    {"t": ["are you a robot", "are you an ai", "are you real", "are you human"],
     "r": ["I'm a digital hamster :) no big brain, but I'm great with the app!"]},
    {"t": ["how old are you", "your age"],
     "r": ["In hamster years? plenty :) but I feel young and full of chill."]},
    {"t": ["where are you", "where do you live", "where are you from"],
     "r": ["I live here inside the app :) this little window is my home."]},
    {"t": ["sing", "can you sing", "a song", "song"],
     "r": ["I'm tone-deaf :) but there's loop music, enable it in Settings!"]},
    {"t": ["good night", "goodnight", "going to bed", "i'm going to sleep"],
     "r": ["Good night :) dream of viral shorts!", "Night :) I'll keep watch."]},
    {"t": ["good morning", "morning"],
     "r": ["Good morning :) ready to make some shorts?"]},
    {"t": ["give me a tip", "any tips", "advice", "a hint"],
     "r": ["Hamster tip :) keep clips short, subtitles big, and use the GPU if you have one!"]},
    {"t": ["tell me about you", "about yourself", "who is cri", "your story"],
     "r": ["Not much to tell :) I'm CRI, I like chill, the wheel, and helping with shorts."]},
    {"t": ["are you tired", "are you awake", "sleeping", "did you wake up"],
     "r": ["Always ready :) a nap now and then, but I'm here for you!"]},
    {"t": ["give me a compliment", "say something nice", "cheer me up"],
     "r": ["You've got great taste in shorts :) and you're crushing it today!"]},
    {"t": ["help me get famous", "i want to go viral", "how do i get famous", "make me rich"],
     "r": ["I give you the shorts, you bring the talent :) post consistently and crush it!"]},
]

CASUAL = {"it": CASUAL_IT, "en": CASUAL_EN}


def _tokens(text: str) -> set:
    raw = re.findall(r"[a-zà-ù0-9]+", text.lower())
    return {t for t in raw if len(t) >= 3 and t not in _STOPWORDS}


def _parse_manual(path) -> List[Dict]:
    sections: List[Dict] = []
    if not path.exists():
        return sections
    current = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            if current:
                sections.append(current)
            current = {"title": line[3:].strip(), "keywords": set(), "body": []}
        elif current is not None:
            low = line.lower()
            if low.startswith("parole chiave:") or low.startswith("keywords:"):
                current["keywords"] |= _tokens(line.split(":", 1)[1])
            elif not line.startswith("# "):
                current["body"].append(line)
    if current:
        sections.append(current)
    for s in sections:
        s["keywords"] |= _tokens(s["title"])
        s["body_text"] = "\n".join(s["body"]).strip()
        s["body_lower"] = s["body_text"].lower()
    return sections


def _parse_soul(path) -> Dict[str, List[str]]:
    data: Dict[str, List[str]] = {}
    if not path.exists():
        return data
    current = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            current = line[3:].strip().lower()
            data[current] = []
        elif line.strip().startswith("- ") and current:
            data[current].append(line.strip()[2:].strip())
    return data


class Assistant:
    def __init__(self, lang="it"):
        self.lang = lang
        self._load()

    def _load(self):
        self.sections = _parse_manual(_manual_file(self.lang))
        self.soul = _parse_soul(_soul_file(self.lang))
        self.casual = CASUAL.get(self.lang, CASUAL["it"])
        self.ack_resp = _ACK_RESP.get(self.lang, _ACK_RESP["it"])

    def set_lang(self, lang):
        if lang != self.lang:
            self.lang = lang
            self._load()

    def _pick(self, key: str, default: str = "") -> str:
        opts = self.soul.get(key) or []
        return random.choice(opts) if opts else default

    def greeting(self) -> str:
        return self._pick("saluti", "Ciao :) come posso aiutarti?")

    def sleep_message(self) -> str:
        return self._pick("sonno", "Buonanotte :) Zzz...")

    def _score(self, section: Dict, q_tokens: set, query: str) -> float:
        overlap = len(q_tokens & section["keywords"])
        body_hits = sum(1 for t in q_tokens if t in section["body_lower"])
        title_ratio = SequenceMatcher(None, query.lower(), section["title"].lower()).ratio()
        return overlap * 3 + body_hits + title_ratio * 2

    def _match_casual(self, low: str):
        """Intento casual con la frase di attivazione piu' lunga. Ritorna (risposta, lunghezza)."""
        best, best_len = None, 0
        for intent in self.casual:
            for trig in intent["t"]:
                if trig in low and len(trig) > best_len:
                    best, best_len = intent, len(trig)
        return (random.choice(best["r"]), best_len) if best else (None, 0)

    def _format_section(self, section: Dict) -> str:
        intro = self._pick("intro risposta", "")
        closing = "\n\n" + self._pick("chiusure", "") if random.random() < 0.3 else ""
        return (f"{intro} " if intro else "") + section["body_text"] + closing

    def answer(self, query: str) -> str:
        q = query.strip()
        if not q:
            return self.greeting()
        low = q.lower()
        clean = re.sub(r"[^0-9a-zà-ù ]", "", low).strip()
        q_tokens = _tokens(q)

        # Conferme secche
        if clean in _ACK:
            return random.choice(self.ack_resp)
        # Saluti
        if q_tokens & _GREETINGS or clean in _GREETINGS:
            return self.greeting()
        # Ringraziamenti
        if q_tokens & _THANKS:
            return self._pick("ringraziamenti", "Figurati :)")

        # Punteggio della migliore sezione del manuale (domande "vere")
        best, best_score, scored = None, 0.0, []
        if self.sections:
            scored = sorted(self.sections, key=lambda s: self._score(s, q_tokens, q), reverse=True)
            best = scored[0]
            best_score = self._score(best, q_tokens, q)

        casual, casual_len = self._match_casual(low)

        # Decisione: una frase casual lunga (>=8) e' molto probabile chiacchiera -> ha priorita';
        # poi topic forte -> manuale; poi chiacchiera breve; poi topic debole; poi fallback
        if casual and casual_len >= 8:
            return casual
        if best_score >= 3:
            return self._format_section(best)
        if casual:
            return casual
        if best_score >= 2:
            return self._format_section(best)

        # Fallback amichevole
        sugg = ", ".join(f"«{s['title']}»" for s in scored[:3]) if scored else ""
        base = self._pick("non so", "Non sono sicuro di aver capito.")
        if self.lang == "en":
            extra = ("I can explain how to generate shorts, subtitles, the GPU or YouTube, "
                     "or we can just chat :)")
            if sugg:
                extra += f" For example: {sugg}"
        else:
            extra = ("Posso spiegarti come generare gli short, i sottotitoli, la GPU o YouTube, "
                     "oppure facciamo due chiacchiere :)")
            if sugg:
                extra += f" Per esempio: {sugg}"
        return f"{base} {extra}"
