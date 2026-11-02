"""Club ratings and fixtures for all supported competitions.

One Elo scale for every club: European cup results since 2011 tie the leagues together, domestic league
results (last three seasons plus the current one) rate clubs inside each league. A Poisson goal model with
a per-competition goal level turns rating differences into expected goals.

Sources (cloned at run time into ext/, see .github/workflows/daily.yml):
  ext/champions-league  openfootball European cups (txt)
  ext/football.json     openfootball league data (json)
  ext/europe            openfootball Turkish Süper Lig (txt)
  data/uefa_2026_27.txt UEFA 2026/27 league phase fixtures and results (UCL, UEL, UECL)
"""
import collections, datetime as dt, glob, json, math, os, pathlib, re, unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXT = pathlib.Path(os.environ.get("EXT_DIR", ROOT / "ext"))
SEASON = "2026-27"
HISTORY = ["2023-24", "2024-25", "2025-26"]

COMPS = {
    "UCL": {"name": "Champions League", "lang": "en", "tags": ["ChampionsLeague", "UCL"]},
    "UEL": {"name": "Europa League", "lang": "en", "tags": ["EuropaLeague", "UEL"]},
    "UECL": {"name": "Conference League", "lang": "en", "tags": ["ConferenceLeague", "UECL"]},
    "TR1": {"name": "Süper Lig", "lang": "tr", "country": "TUR", "json": "tr.1", "tags": ["SüperLig", "TrendyolSüperLig"]},
    "EN1": {"name": "Premier League", "lang": "en", "country": "ENG", "json": "en.1", "tags": ["PremierLeague", "EPL"]},
    "ES1": {"name": "LaLiga", "lang": "es", "country": "ESP", "json": "es.1", "tags": ["LaLiga"]},
    "IT1": {"name": "Serie A", "lang": "it", "country": "ITA", "json": "it.1", "tags": ["SerieA"]},
    "DE1": {"name": "Bundesliga", "lang": "de", "country": "GER", "json": "de.1", "tags": ["Bundesliga"]},
    "FR1": {"name": "Ligue 1", "lang": "fr", "country": "FRA", "json": "fr.1", "tags": ["Ligue1"]},
}
LEAGUES = [c for c in COMPS if "country" in COMPS[c]]

# ---------------------------------------------------------------- names -> keys
DROP = {"fc", "cf", "sk", "fk", "kv", "afc", "ssc", "club", "de", "sl", "sfp", "pae", "sc", "jk", "as"}
ALIAS = {
    "psv": "psv eindhoven", "feyenoord rotterdam": "feyenoord", "internazionale milano": "inter",
    "racing lens": "lens", "rc lens": "lens", "racing club lens": "lens", "sporting clube portugal": "sporting cp",
    "sporting clube braga": "sporting braga", "aek athen": "aek athens", "sport lisboa e benfica": "benfica",
    "gnk dinamo zagreb": "dinamo zagreb", "real sociedad futbol": "real sociedad", "olympiakos piraeus": "olympiakos",
    "red bull salzburg": "rb salzburg", "ss lazio": "lazio roma", "lazio": "lazio roma", "bayer 04 leverkusen": "bayer leverkusen",
    "atalanta bc": "atalanta", "royale union saint-gilloise": "union saint-gilloise", "qarabag agdam": "qarabag",
    "kauno zalgiris": "zalgiris", "real betis balompie": "real betis", "roma": "as roma",
    # Turkish sponsor names
    "atiker konyaspor": "konyaspor", "aytemiz alanyaspor": "alanyaspor", "gencler birligi": "genclerbirligi",
    "kasimpasa": "kasimpasa", "kasimpasa sk": "kasimpasa", "galatasaray": "galatasaray",
    # league file vs European file spellings
    "rayo vallecano madrid": "rayo vallecano", "bor monchengladbach": "borussia monchengladbach",
    "1899 hoffenheim": "tsg 1899 hoffenheim", "stade rennais 1901": "stade rennais", "rc strasbourg alsace": "rc strasbourg",
}


def strip(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def norm(name):
    t = [w for w in strip(name).lower().replace(".", "").replace("ı", "i").split() if w not in DROP]
    k = " ".join(t)
    return ALIAS.get(k, k)


def key(name, country):
    return norm(name) + "|" + country


def split_country(n):
    m = re.match(r"(.+?)\s*\((\w+)\)$", n.strip())
    return (m.group(1), m.group(2)) if m else (n.strip(), "")


# ---------------------------------------------------------------- parsing
MONTHS = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
DATE_RE = re.compile(r"^\s*(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+([A-Z][a-z]{2})\s+(\d{1,2})(?:\s+(\d{4}))?\s*$")


class DateTracker:
    """Dates in openfootball txt files; the year follows the season (Jul-Dec = first year)."""
    def __init__(self, start_year):
        self.start, self.m, self.d = start_year, 7, 1

    def line(self, l):
        m = DATE_RE.match(l)
        if not m:
            return False
        self.m, self.d = MONTHS[m.group(1)], int(m.group(2))
        return True

    def date(self):
        return dt.date(self.start if self.m >= 7 else self.start + 1, self.m, self.d).isoformat()


def euro_cups():
    """European cup matches from openfootball/champions-league (all seasons)."""
    out = []
    for f in sorted(glob.glob(str(EXT / "champions-league" / "*" / "*.txt"))):
        season = f.split(os.sep)[-2]
        comp = os.path.basename(f)[:-4]
        if comp not in ("cl", "el", "conf", "clq", "elq", "confq"):
            continue
        tr = DateTracker(int(season[:4]))
        for l in open(f, encoding="utf8"):
            if tr.line(l):
                continue
            if " v " not in l:
                continue
            m = re.match(r"^\s*(?:\d{1,2}[:.]\d{2}\s+)?(.+?)\s+v\s+(.+?)\s+(\d+)-(\d+)\b(.*)$", l.rstrip())
            if not m:
                continue
            h, a, gh, ga, rest = m.groups()
            if "pen" in rest:
                m2 = re.search(r"(\d+)-(\d+)\s+a\.e\.t", rest)
                if m2:
                    gh, ga = m2.groups()
            (hn, hc), (an, ac) = split_country(h), split_country(a)
            out.append(dict(date=tr.date(), comp="EUR", h=key(hn, hc), a=key(an, ac), gh=int(gh), ga=int(ga),
                            neutral="Final" in l, hname=hn, aname=an))
    return out


def league_json(code, season, country):
    f = EXT / "football.json" / season / f"{code}.json"
    if not f.exists():
        return []
    out = []
    for m in json.load(open(f, encoding="utf8"))["matches"]:
        r = dict(date=m.get("date"), time=m.get("time"), round=m.get("round", ""), h=key(m["team1"], country),
                 a=key(m["team2"], country), hname=m["team1"], aname=m["team2"], neutral=False)
        sc = m.get("score")
        ft = sc.get("ft") if isinstance(sc, dict) else (sc if isinstance(sc, list) and len(sc) == 2 else None)
        if ft is None and "score1" in m and m.get("score1") is not None:
            ft = [m["score1"], m["score2"]]
        if ft:
            r.update(gh=ft[0], ga=ft[1])
        out.append(r)
    return out


def turkey_txt(season):
    f = EXT / "europe" / "turkey" / f"{season}_tr1.txt"
    if not f.exists():
        return []
    out, rnd = [], ""
    tr = DateTracker(int(season[:4]))
    for l in open(f, encoding="utf8"):
        if l.startswith("▪"):
            rnd = l.strip("▪ \n")
            continue
        if tr.line(l):
            continue
        m = re.match(r"^\s+(?:(\d{1,2}:\d{2})\s+)?(\S.*?)\s{2,}(?:(\d+)-(\d+)(?:\s+\(\d+-\d+\))?|v)\s{2,}(\S.*?)\s*$", l)
        if not m or l.strip().startswith("("):
            continue
        t, h, gh, ga, a = m.groups()
        r = dict(date=tr.date(), time=t, round=rnd, h=key(h, "TUR"), a=key(a, "TUR"), hname=h, aname=a, neutral=False)
        if gh is not None:
            r.update(gh=int(gh), ga=int(ga))
        out.append(r)
    return out


def uefa_file():
    out = []
    for l in open(ROOT / "data" / "uefa_2026_27.txt", encoding="utf8"):
        if l.startswith("#") or not l.strip():
            continue
        comp, d, t, h, a, s = [x.strip() for x in l.split("|")]
        r = dict(comp=comp, date=d, time=t, hname=h, aname=a, neutral=False)
        if s:
            r["gh"], r["ga"] = map(int, s.split("-"))
        out.append(r)
    return out


# UEFA short names -> keys (resolved against keys seen in openfootball data)
UEFA_NAMES = {
    "Milan": "ac milan|ITA", "Inter": "inter|ITA", "Juventus": "juventus|ITA", "Atalanta": "atalanta|ITA", "Napoli": "napoli|ITA",
    "Roma": "as roma|ITA", "Como": "como 1907|ITA", "Celta": "rc celta vigo|ESP", "Real Sociedad": "real sociedad|ESP",
    "Getafe": "getafe|ESP", "Real Betis": "real betis|ESP", "Villarreal": "villarreal|ESP", "Barcelona": "barcelona|ESP",
    "Real Madrid": "real madrid|ESP", "Atlético de Madrid": "atletico madrid|ESP", "Leverkusen": "bayer leverkusen|GER",
    "Hoffenheim": "tsg 1899 hoffenheim|GER", "Freiburg": "freiburg|GER", "Leipzig": "rb leipzig|GER", "Stuttgart": "vfb stuttgart|GER",
    "Bayern München": "bayern munchen|GER", "Borussia Dortmund": "borussia dortmund|GER", "Lyon": "olympique lyonnais|FRA",
    "Marseille": "olympique marseille|FRA", "Rennes": "stade rennais|FRA", "Monaco": "monaco|FRA", "Lille": "lille osc|FRA",
    "Lens": "lens|FRA", "Paris Saint-Germain": "paris saint-germain|FRA", "Bournemouth": "bournemouth|ENG",
    "Crystal Palace": "crystal palace|ENG", "Sunderland": "sunderland|ENG", "Brighton": "brighton & hove albion|ENG",
    "Aston Villa": "aston villa|ENG", "Arsenal": "arsenal|ENG", "Liverpool": "liverpool|ENG", "Manchester City": "manchester city|ENG",
    "Manchester United": "manchester united|ENG", "Beşiktaş": "besiktas|TUR", "Trabzonspor": "trabzonspor|TUR",
    "Galatasaray": "galatasaray|TUR", "Fenerbahçe": "fenerbahce|TUR", "Benfica": "benfica|POR", "Braga": "sporting braga|POR",
    "Sporting CP": "sporting cp|POR", "Porto": "porto|POR", "Torreense": "torreense|POR", "AZ Alkmaar": "az alkmaar|NED",
    "N.E.C. Nijmegen": "nec nijmegen|NED", "Ajax": "ajax|NED", "Twente": "twente|NED", "Feyenoord": "feyenoord|NED",
    "PSV Eindhoven": "psv eindhoven|NED", "Union SG": "union saint-gilloise|BEL", "Anderlecht": "anderlecht|BEL",
    "Gent": "gent|BEL", "Sint-Truidense": "sint-truidense vv|BEL", "Club Brugge": "brugge|BEL", "Celtic": "celtic|SCO",
    "Hearts": "heart of midlothian|SCO", "Salzburg": "rb salzburg|AUT", "Sturm Graz": "sturm graz|AUT", "LASK": "lask|AUT",
    "GNK Dinamo": "dinamo zagreb|CRO", "Hajduk Split": "hajduk split|CRO", "Copenhagen": "københavn|DEN",
    "Midtjylland": "midtjylland|DEN", "Nordsjælland": "nordsjælland|DEN", "Aarhus": "agf|DEN", "Crvena Zvezda": "crvena zvezda|SRB",
    "Olympiacos": "olympiakos|GRE", "Panathinaikos": "panathinaikos|GRE", "AEK Athens": "aek athens|GRE", "OFI Crete": "ofi crete|GRE",
    "Sparta Praha": "ac sparta praha|CZE", "Slavia Praha": "slavia praha|CZE", "Viktoria Plzeň": "viktoria plzen|CZE",
    "Jablonec": "jablonec|CZE", "Ferencváros": "ferencvarosi tc|HUN", "Lech Poznań": "lech poznan|POL", "Jagiellonia": "jagiellonia bialystok|POL",
    "Levski Sofia": "levski sofia|BUL", "CSKA Sofia": "cska sofia|BUL", "Celje": "nk celje|SVN", "Omonia": "omonia nikosia|CYP",
    "Pafos": "pafos|CYP", "Hapoel Beer-Sheva": "hapoel be'er sheva|ISR", "Lillestrøm": "lillestrom|NOR", "Brann": "brann|NOR",
    "Bodø/Glimt": "bodø/glimt|NOR", "Viking": "viking|NOR", "Mjällby": "mjallby aif|SWE", "Ararat-Armenia": "ararat-armenia|ARM",
    "Lugano": "lugano|SUI", "Thun": "thun|SUI", "KuPS Kuopio": "kuopion ps|FIN", "Riga": "riga|LVA", "Kairat Almaty": "kairat|KAZ",
    "Universitatea Craiova": "cs universitatea craiova|ROU", "Inter Escaldes": "inter d'escaldes|AND", "Egnatia": "egnatia rrogozhine|ALB",
    "Borac": "borac banja luka|BIH", "Kauno Žalgiris": "zalgiris|LTU", "Iberia Tbilisi": "iberia 1999|GEO",
    "Lincoln Red Imps": "lincoln red imps|GIB", "Shakhtar Donetsk": "shakhtar donetsk|UKR", "Sabah": "sabah|AZE",
    "Slovan Bratislava": "slovan bratislava|SVK", "Leverkusen ": "bayer leverkusen|GER",
}


def resolve_uefa(name, known):
    """Map a UEFA display name to a club key; fuzzy fallback against keys with history."""
    k = UEFA_NAMES.get(name)
    if k and k in known:
        return k
    n = norm(name)
    cands = [kk for kk in known if kk.split("|")[0] == n]
    if not cands:
        toks = set(n.split())
        cands = [kk for kk in known if toks and toks <= set(kk.split("|")[0].split())]
    if cands:
        return max(cands, key=lambda c: known[c])
    return k or (n + "|UEFA")


# ---------------------------------------------------------------- ratings
def build():
    matches, display = [], {}
    for m in euro_cups():
        matches.append(m)
    for c in LEAGUES:
        cc = COMPS[c]["country"]
        for s in HISTORY + [SEASON]:
            rows = turkey_txt(s) if (c == "TR1" and s == SEASON) else league_json(COMPS[c]["json"], s, cc)
            for r in rows:
                r["comp"] = c
                if s == SEASON:
                    display.setdefault(r["h"], r["hname"]); display.setdefault(r["a"], r["aname"])
                if "gh" in r and r.get("date"):
                    matches.append(r)
    games = collections.Counter()
    for m in matches:
        games[m["h"]] += 1; games[m["a"]] += 1
    uefa = uefa_file()
    for r in uefa:
        r["h"], r["a"] = resolve_uefa(r["hname"], games), resolve_uefa(r["aname"], games)
        display.setdefault(r["h"], r["hname"]); display.setdefault(r["a"], r["aname"])
        if "gh" in r:
            matches.append(r)
    matches.sort(key=lambda m: (m["date"], 0 if m["comp"] in ("EUR", "UCL", "UEL", "UECL") else 1))

    elo, hist, last, season_of = {}, [], collections.defaultdict(list), None
    HFA = 55

    def init(k):
        c = k.split("|")[1]
        vals = sorted((v for x, v in elo.items() if x.endswith("|" + c)), reverse=True)
        return (sum(vals[-6:]) / len(vals[-6:]) - 20) if vals else 1400

    for m in matches:
        y = int(m["date"][:4]); s = y if int(m["date"][5:7]) >= 7 else y - 1
        if season_of is not None and s != season_of:
            for k in elo:
                elo[k] -= (elo[k] - 1500) * 0.2
        season_of = s
        for k in (m["h"], m["a"]):
            if k not in elo:
                elo[k] = init(k)
        dr = elo[m["h"]] - elo[m["a"]] + (0 if m.get("neutral") else HFA)
        e = 1 / (1 + 10 ** (-dr / 400)); sres = 1 if m["gh"] > m["ga"] else 0.5 if m["gh"] == m["ga"] else 0
        gd = abs(m["gh"] - m["ga"]); mult = 1 if gd <= 1 else (1.5 if gd == 2 else (11 + gd) / 8)
        K = 30 if m["comp"] in ("EUR", "UCL", "UEL", "UECL") else 20
        hist.append((m["comp"], dr, m["gh"], m["ga"], m["date"]))
        d = K * mult * (sres - e); elo[m["h"]] += d; elo[m["a"]] -= d
        for k, opp, gf, ga in ((m["h"], m["a"], m["gh"], m["ga"]), (m["a"], m["h"], m["ga"], m["gh"])):
            last[k].append(("W" if gf > ga else "D" if gf == ga else "L", gf, ga, opp, m["date"]))

    # Poisson: shared slope, per-competition intercept (European cups pooled)
    def fit(rows):
        a, b = 0.3, 0.8
        for _ in range(100):
            g1 = g2 = h11 = h12 = h22 = 0
            for dr, gh, ga in rows:
                for y, sg in ((gh, 1), (ga, -1)):
                    x = sg * dr / 400; lam = math.exp(a + b * x)
                    g1 += y - lam; g2 += (y - lam) * x; h11 += lam; h12 += lam * x; h22 += lam * x * x
            det = h11 * h22 - h12 * h12
            da, db = (h22 * g1 - h12 * g2) / det, (h11 * g2 - h12 * g1) / det
            a += da; b += db
            if abs(da) + abs(db) < 1e-9:
                break
        return a, b
    a, b = fit([(dr, gh, ga) for _, dr, gh, ga, _ in hist])
    intercept = {}
    for c in list(COMPS) + ["EUR"]:
        pool = ("EUR", "UCL", "UEL", "UECL") if c in ("EUR", "UCL", "UEL", "UECL") else (c,)
        rows = [(dr, gh, ga) for comp, dr, gh, ga, d in hist if comp in pool and d >= "2023-07-01"]
        if len(rows) < 100:
            intercept[c] = a; continue
        obs = sum(gh + ga for _, gh, ga in rows); pred = sum(math.exp(a + b * dr / 400) + math.exp(a - b * dr / 400) for dr, _, _ in rows)
        intercept[c] = a + math.log(obs / pred)

    teams = {}
    for k in elo:
        teams[k] = {"elo": round(elo[k]), "n": games[k], "last": [[r, gf, ga, display.get(o, o.split("|")[0].title()), d[:4]]
                                                                for r, gf, ga, o, d in last[k][-5:]]}
    return {"teams": teams, "model": {"a": a, "b": b, "hfa": HFA, "intercept": intercept}, "display": display, "uefa": uefa,
            "matches": matches}


def fixtures(data, start, end):
    """Unplayed fixtures with start <= date <= end (ISO strings)."""
    out = []
    for r in data["uefa"]:
        if "gh" not in r and start <= r["date"] <= end:
            out.append(dict(comp=r["comp"], date=r["date"], time=r["time"], h=r["h"], a=r["a"], home=r["hname"], away=r["aname"], matchday=None))
    for c in LEAGUES:
        rows = turkey_txt(SEASON) if c == "TR1" else league_json(COMPS[c]["json"], SEASON, COMPS[c]["country"])
        for r in rows:
            if "gh" in r or not r.get("date") or not (start <= r["date"] <= end):
                continue
            md = re.search(r"(\d+)\s*$", r.get("round", ""))
            out.append(dict(comp=c, date=r["date"], time=None, h=r["h"], a=r["a"], home=r["hname"], away=r["aname"],
                            matchday=int(md.group(1)) if md else None))
    return out
