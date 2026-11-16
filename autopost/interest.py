"""How much a match is worth a YouTube Short: big clubs, derbies and national teams first, quiet leagues last.

The YouTube slot posts only matches at or above `youtube_selection.min_score` (config.json), best first, a few a day:
a handful of strong videos does better on Shorts than many ordinary ones.
"""

# competition base weight (national teams count via UNL)
COMP = {"UCL": 2, "UNL": 1, "EN1": 1, "ES1": 1, "TR1": 1, "IT1": 1, "DE1": 1, "UEL": 1,
        "FR1": 0.5, "UECL": 0, "UWCL": -3}

# clubs and national teams people search for; same keys as leagues.py / teams.py
BIG = {
    "real madrid|ESP", "barcelona|ESP", "atletico madrid|ESP",
    "manchester city|ENG", "manchester united|ENG", "liverpool|ENG", "arsenal|ENG", "chelsea|ENG", "tottenham hotspur|ENG",
    "bayern munchen|GER", "borussia dortmund|GER",
    "juventus|ITA", "inter|ITA", "ac milan|ITA", "napoli|ITA",
    "paris saint-germain|FRA",
    "galatasaray|TUR", "fenerbahce|TUR", "besiktas|TUR",
    "spain|NAT", "france|NAT", "england|NAT", "germany|NAT", "italy|NAT", "portugal|NAT", "netherlands|NAT", "belgium|NAT",
}
MID = {
    "trabzonspor|TUR", "benfica|POR", "porto|POR", "sporting cp|POR", "ajax|NED", "psv eindhoven|NED", "feyenoord|NED",
    "as roma|ITA", "lazio roma|ITA", "atalanta|ITA", "bayer leverkusen|GER", "rb leipzig|GER", "schalke 04|GER",
    "newcastle united|ENG", "aston villa|ENG", "olympique marseille|FRA", "olympique lyonnais|FRA", "monaco|FRA",
    "sevilla|ESP", "real betis|ESP", "athletic|ESP", "celtic|SCO", "rangers|SCO",
    "croatia|NAT", "switzerland|NAT", "denmark|NAT", "austria|NAT", "poland|NAT", "serbia|NAT", "scotland|NAT",
}
DERBIES = {frozenset(p) for p in [
    ("galatasaray|TUR", "fenerbahce|TUR"), ("galatasaray|TUR", "besiktas|TUR"), ("fenerbahce|TUR", "besiktas|TUR"),
    ("trabzonspor|TUR", "fenerbahce|TUR"), ("trabzonspor|TUR", "galatasaray|TUR"), ("trabzonspor|TUR", "besiktas|TUR"),
    ("real madrid|ESP", "barcelona|ESP"), ("real madrid|ESP", "atletico madrid|ESP"), ("sevilla|ESP", "real betis|ESP"),
    ("barcelona|ESP", "atletico madrid|ESP"),
    ("manchester united|ENG", "manchester city|ENG"), ("liverpool|ENG", "manchester united|ENG"), ("liverpool|ENG", "everton|ENG"),
    ("arsenal|ENG", "tottenham hotspur|ENG"), ("chelsea|ENG", "arsenal|ENG"), ("chelsea|ENG", "tottenham hotspur|ENG"),
    ("liverpool|ENG", "manchester city|ENG"), ("arsenal|ENG", "manchester city|ENG"), ("arsenal|ENG", "liverpool|ENG"),
    ("ac milan|ITA", "inter|ITA"), ("as roma|ITA", "lazio roma|ITA"), ("juventus|ITA", "inter|ITA"), ("juventus|ITA", "torino|ITA"),
    ("bayern munchen|GER", "borussia dortmund|GER"), ("borussia dortmund|GER", "schalke 04|GER"),
    ("paris saint-germain|FRA", "olympique marseille|FRA"), ("olympique lyonnais|FRA", "olympique marseille|FRA"),
    ("benfica|POR", "porto|POR"), ("benfica|POR", "sporting cp|POR"), ("ajax|NED", "feyenoord|NED"), ("celtic|SCO", "rangers|SCO"),
    ("england|NAT", "germany|NAT"), ("spain|NAT", "portugal|NAT"), ("france|NAT", "germany|NAT"), ("italy|NAT", "germany|NAT"),
]}


def team(k, priority):
    if k in priority:
        return 4  # the channel's own audience (Turkish clubs, the national team)
    return 3 if k in BIG else 1 if k in MID else 0


def score(f, cfg):
    pr = set(cfg.get("priority_teams", []))
    s = COMP.get(f["comp"], 0) + team(f["h"], pr) + team(f["a"], pr)
    if frozenset((f["h"], f["a"])) in DERBIES:
        s += 4
    return s


def why(f, cfg):
    """short label for the run log"""
    return f"interest {score(f, cfg):g}" + (" derby" if frozenset((f["h"], f["a"])) in DERBIES else "")
