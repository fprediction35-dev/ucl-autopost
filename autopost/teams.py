"""Display name, ball label and kit colours per club key. Unknown clubs get a derived label and colour."""
import hashlib, re

T = {
    # Süper Lig
    "galatasaray|TUR": ("Galatasaray", "GS", "#F6B40E", "#A90432"), "fenerbahce|TUR": ("Fenerbahçe", "FB", "#FFED00", "#002D72"),
    "besiktas|TUR": ("Beşiktaş", "BJK", "#111111", "#FFFFFF"), "trabzonspor|TUR": ("Trabzonspor", "TS", "#8B1D41", "#3FA9F5"),
    "istanbul basaksehir|TUR": ("Başakşehir", "İBFK", "#F26522", "#0A2A5E"), "samsunspor|TUR": ("Samsunspor", "SAM", "#E30A17", "#FFFFFF"),
    "goztepe|TUR": ("Göztepe", "GÖZ", "#F7D417", "#D2232A"), "eyupspor|TUR": ("Eyüpspor", "EYP", "#6C2C91", "#F6D200"),
    "kasimpasa|TUR": ("Kasımpaşa", "KSM", "#0D3B8C", "#FFFFFF"), "konyaspor|TUR": ("Konyaspor", "KON", "#00843D", "#FFFFFF"),
    "alanyaspor|TUR": ("Alanyaspor", "ALY", "#F58220", "#00843D"), "caykur rizespor|TUR": ("Rizespor", "RİZ", "#0A7C3E", "#2E6DB4"),
    "gaziantep|TUR": ("Gaziantep FK", "GFK", "#D71920", "#111111"), "kocaelispor|TUR": ("Kocaelispor", "KOC", "#00843D", "#111111"),
    "genclerbirligi|TUR": ("Gençlerbirliği", "GB", "#E30A17", "#111111"), "amed|TUR": ("Amedspor", "AMD", "#00843D", "#E30A17"),
    "bb erzurumspor|TUR": ("Erzurumspor", "ERZ", "#1F4FA3", "#FFFFFF"), "corum|TUR": ("Çorum FK", "ÇOR", "#E30A17", "#111111"),
    # Premier League
    "arsenal|ENG": ("Arsenal", "ARS", "#EF0107", "#FFFFFF"), "aston villa|ENG": ("Aston Villa", "AVL", "#670E36", "#95BFE5"),
    "bournemouth|ENG": ("Bournemouth", "BOU", "#DA291C", "#111111"), "brentford|ENG": ("Brentford", "BRE", "#E30613", "#FFFFFF"),
    "brighton & hove albion|ENG": ("Brighton", "BHA", "#0057B8", "#FFFFFF"), "chelsea|ENG": ("Chelsea", "CHE", "#034694", "#FFFFFF"),
    "coventry city|ENG": ("Coventry City", "COV", "#59CBE8", "#FFFFFF"), "crystal palace|ENG": ("Crystal Palace", "CRY", "#1B458F", "#C4122E"),
    "everton|ENG": ("Everton", "EVE", "#003399", "#FFFFFF"), "fulham|ENG": ("Fulham", "FUL", "#FFFFFF", "#111111"),
    "hull city|ENG": ("Hull City", "HUL", "#F5A12D", "#111111"), "ipswich town|ENG": ("Ipswich Town", "IPS", "#3A64A3", "#FFFFFF"),
    "leeds united|ENG": ("Leeds United", "LEE", "#FFFFFF", "#1D428A"), "liverpool|ENG": ("Liverpool", "LIV", "#C8102E", "#00B2A9"),
    "manchester city|ENG": ("Manchester City", "MCI", "#6CABDD", "#1C2C5B"), "manchester united|ENG": ("Manchester United", "MUN", "#DA291C", "#FBE122"),
    "newcastle united|ENG": ("Newcastle", "NEW", "#241F20", "#FFFFFF"), "nottingham forest|ENG": ("Nottingham Forest", "NFO", "#DD0000", "#FFFFFF"),
    "sunderland|ENG": ("Sunderland", "SUN", "#EB172B", "#FFFFFF"), "tottenham hotspur|ENG": ("Tottenham", "TOT", "#FFFFFF", "#132257"),
    # LaLiga
    "athletic|ESP": ("Athletic Club", "ATH", "#EE2523", "#FFFFFF"), "ca osasuna|ESP": ("Osasuna", "OSA", "#D91A21", "#0A346F"),
    "atletico madrid|ESP": ("Atlético de Madrid", "ATM", "#CB3524", "#1C2C5B"), "deportivo alaves|ESP": ("Alavés", "ALA", "#0761AF", "#FFFFFF"),
    "elche|ESP": ("Elche", "ELC", "#FFFFFF", "#05642C"), "barcelona|ESP": ("Barcelona", "BAR", "#A50044", "#004D98"),
    "getafe|ESP": ("Getafe", "GET", "#005999", "#FFFFFF"), "levante ud|ESP": ("Levante", "LEV", "#B4053F", "#0A2F7A"),
    "malaga|ESP": ("Málaga", "MAL", "#1E7FCB", "#FFFFFF"), "rc celta vigo|ESP": ("Celta", "CEL", "#8AC3EE", "#FFFFFF"),
    "rc deportivo la coruna|ESP": ("Deportivo", "DEP", "#0B4EA2", "#FFFFFF"), "rcd espanyol barcelona|ESP": ("Espanyol", "ESP", "#1E73BE", "#FFFFFF"),
    "rayo vallecano|ESP": ("Rayo Vallecano", "RAY", "#FFFFFF", "#E53027"), "real betis|ESP": ("Real Betis", "BET", "#00954C", "#FFFFFF"),
    "real madrid|ESP": ("Real Madrid", "RMA", "#FFFFFF", "#FEBE10"), "real racing santander|ESP": ("Racing Santander", "RAC", "#00843D", "#FFFFFF"),
    "real sociedad|ESP": ("Real Sociedad", "RSO", "#0067B1", "#FFFFFF"), "sevilla|ESP": ("Sevilla", "SEV", "#FFFFFF", "#D81E05"),
    "valencia|ESP": ("Valencia", "VAL", "#FFFFFF", "#EE3524"), "villarreal|ESP": ("Villarreal", "VIL", "#FFE667", "#005187"),
    # Serie A
    "ac milan|ITA": ("Milan", "MIL", "#FB090B", "#111111"), "ac monza|ITA": ("Monza", "MON", "#E2001A", "#FFFFFF"),
    "acf fiorentina|ITA": ("Fiorentina", "FIO", "#482E92", "#FFFFFF"), "as roma|ITA": ("Roma", "ROM", "#8E1F2F", "#F0BC42"),
    "atalanta|ITA": ("Atalanta", "ATA", "#1E71B8", "#111111"), "bologna 1909|ITA": ("Bologna", "BOL", "#1A2F48", "#A21C26"),
    "cagliari calcio|ITA": ("Cagliari", "CAG", "#B01028", "#002350"), "como 1907|ITA": ("Como", "COM", "#1B3F8F", "#FFFFFF"),
    "inter|ITA": ("Inter", "INT", "#0068A8", "#111111"), "frosinone calcio|ITA": ("Frosinone", "FRO", "#FFDD00", "#0A3F8F"),
    "genoa cfc|ITA": ("Genoa", "GEN", "#A1162B", "#002B5C"), "juventus|ITA": ("Juventus", "JUV", "#FFFFFF", "#111111"),
    "parma calcio 1913|ITA": ("Parma", "PAR", "#FFE300", "#1B4A9B"), "lazio roma|ITA": ("Lazio", "LAZ", "#87D8F7", "#FFFFFF"),
    "napoli|ITA": ("Napoli", "NAP", "#12A0D7", "#FFFFFF"), "torino|ITA": ("Torino", "TOR", "#8A1E03", "#FFFFFF"),
    "us lecce|ITA": ("Lecce", "LEC", "#FFD200", "#DA291C"), "us sassuolo calcio|ITA": ("Sassuolo", "SAS", "#00A752", "#111111"),
    "udinese calcio|ITA": ("Udinese", "UDI", "#FFFFFF", "#111111"), "venezia|ITA": ("Venezia", "VEN", "#111111", "#F47920"),
    # Bundesliga
    "1 koln|GER": ("Köln", "KOE", "#FFFFFF", "#ED1C24"), "1 union berlin|GER": ("Union Berlin", "FCU", "#EB1923", "#FFFFFF"),
    "1 fsv mainz 05|GER": ("Mainz 05", "M05", "#C3141E", "#FFFFFF"), "bayer leverkusen|GER": ("Leverkusen", "B04", "#E32221", "#111111"),
    "borussia dortmund|GER": ("Dortmund", "BVB", "#FDE100", "#111111"), "borussia monchengladbach|GER": ("Gladbach", "BMG", "#FFFFFF", "#00A651"),
    "eintracht frankfurt|GER": ("Frankfurt", "SGE", "#E1000F", "#111111"), "augsburg|GER": ("Augsburg", "FCA", "#BA3733", "#46714D"),
    "bayern munchen|GER": ("Bayern München", "FCB", "#DC052D", "#FFFFFF"), "schalke 04|GER": ("Schalke 04", "S04", "#004D9D", "#FFFFFF"),
    "hamburger sv|GER": ("Hamburger SV", "HSV", "#FFFFFF", "#0A3F86"), "rb leipzig|GER": ("Leipzig", "RBL", "#DD0741", "#FFFFFF"),
    "freiburg|GER": ("Freiburg", "SCF", "#111111", "#E2001A"), "paderborn 07|GER": ("Paderborn", "SCP", "#005CA9", "#111111"),
    "sv 07 elversberg|GER": ("Elversberg", "SVE", "#111111", "#FFFFFF"), "sv werder bremen|GER": ("Werder Bremen", "SVW", "#1D9053", "#FFFFFF"),
    "tsg 1899 hoffenheim|GER": ("Hoffenheim", "TSG", "#1961B5", "#FFFFFF"), "vfb stuttgart|GER": ("Stuttgart", "VFB", "#E32219", "#FFFFFF"),
    # Ligue 1
    "aj auxerre|FRA": ("Auxerre", "AJA", "#FFFFFF", "#005BAB"), "monaco|FRA": ("Monaco", "ASM", "#E7242F", "#FFFFFF"),
    "angers sco|FRA": ("Angers", "SCO", "#111111", "#FFFFFF"), "es troyes ac|FRA": ("Troyes", "ESTAC", "#005AAA", "#FFFFFF"),
    "lorient|FRA": ("Lorient", "FCL", "#F58113", "#111111"), "le havre ac|FRA": ("Le Havre", "HAC", "#7DB6E1", "#1E3765"),
    "le mans|FRA": ("Le Mans", "LMFC", "#E30613", "#F6D600"), "lille osc|FRA": ("Lille", "LOSC", "#E01E13", "#1A2B5B"),
    "ogc nice|FRA": ("Nice", "OGCN", "#E31B23", "#111111"), "olympique lyonnais|FRA": ("Lyon", "OL", "#FFFFFF", "#1A3E8C"),
    "olympique marseille|FRA": ("Marseille", "OM", "#FFFFFF", "#2FAEE0"), "paris|FRA": ("Paris FC", "PFC", "#1B2A4A", "#FFFFFF"),
    "paris saint-germain|FRA": ("Paris Saint-Germain", "PSG", "#004170", "#DA291C"), "rc strasbourg|FRA": ("Strasbourg", "RCSA", "#009FE3", "#FFFFFF"),
    "lens|FRA": ("Lens", "RCL", "#FFD100", "#E30613"), "stade brestois 29|FRA": ("Brest", "SB29", "#E30613", "#FFFFFF"),
    "stade rennais|FRA": ("Rennes", "SRFC", "#E30613", "#111111"), "toulouse|FRA": ("Toulouse", "TFC", "#5F2D91", "#FFFFFF"),
    # European cups (others)
    "ajax|NED": ("Ajax", "AJA", "#FFFFFF", "#D2122E"), "az alkmaar|NED": ("AZ Alkmaar", "AZ", "#E30613", "#FFFFFF"),
    "feyenoord|NED": ("Feyenoord", "FEY", "#E30613", "#FFFFFF"), "psv eindhoven|NED": ("PSV", "PSV", "#ED1C24", "#FFFFFF"),
    "twente|NED": ("Twente", "TWE", "#E30613", "#FFFFFF"), "nec nijmegen|NED": ("NEC", "NEC", "#E30613", "#00843D"),
    "benfica|POR": ("Benfica", "SLB", "#E30613", "#FFFFFF"), "porto|POR": ("Porto", "FCP", "#00428C", "#FFFFFF"),
    "sporting cp|POR": ("Sporting CP", "SCP", "#008057", "#FFFFFF"), "sporting braga|POR": ("Braga", "SCB", "#D7242F", "#FFFFFF"),
    "torreense|POR": ("Torreense", "SCU", "#1A1A1A", "#FFFFFF"), "brugge|BEL": ("Club Brugge", "BRU", "#0067CE", "#111111"),
    "rsc anderlecht|BEL": ("Anderlecht", "AND", "#5E2B8A", "#FFFFFF"), "kaa gent|BEL": ("Gent", "GNT", "#0066B3", "#FFFFFF"),
    "union saint-gilloise|BEL": ("Union SG", "USG", "#F6D300", "#1F3C88"), "sint-truidense vv|BEL": ("Sint-Truiden", "STVV", "#FFE100", "#0055A4"),
    "celtic|SCO": ("Celtic", "CEL", "#018749", "#FFFFFF"), "heart of midlothian|SCO": ("Hearts", "HRT", "#7A1E30", "#FFFFFF"),
    "rb salzburg|AUT": ("Salzburg", "RBS", "#DD0741", "#FFFFFF"), "sturm graz|AUT": ("Sturm Graz", "STU", "#111111", "#FFFFFF"),
    "lask|AUT": ("LASK", "LASK", "#111111", "#FFFFFF"), "dinamo zagreb|CRO": ("Dinamo Zagreb", "DIN", "#0A47A3", "#FFFFFF"),
    "hajduk split|CRO": ("Hajduk Split", "HAJ", "#FFFFFF", "#003DA5"), "københavn|DEN": ("Copenhagen", "FCK", "#FFFFFF", "#003DA5"),
    "midtjylland|DEN": ("Midtjylland", "FCM", "#111111", "#D7181F"), "nordsjælland|DEN": ("Nordsjælland", "FCN", "#F7A800", "#D7181F"),
    "agf|DEN": ("Aarhus", "AGF", "#FFFFFF", "#003DA5"), "crvena zvezda|SRB": ("Crvena Zvezda", "CZV", "#E30613", "#FFFFFF"),
    "olympiakos|GRE": ("Olympiacos", "OLY", "#E30613", "#FFFFFF"), "panathinaikos|GRE": ("Panathinaikos", "PAO", "#007A33", "#FFFFFF"),
    "aek athens|GRE": ("AEK Athens", "AEK", "#FFD200", "#111111"), "ofi crete|GRE": ("OFI Crete", "OFI", "#111111", "#FFFFFF"),
    "ac sparta praha|CZE": ("Sparta Praha", "SPA", "#A50034", "#FFFFFF"), "slavia praha|CZE": ("Slavia Praha", "SLA", "#E4002B", "#FFFFFF"),
    "viktoria plzen|CZE": ("Viktoria Plzeň", "PLZ", "#E30613", "#005BAC"), "jablonec|CZE": ("Jablonec", "JAB", "#00843D", "#FFFFFF"),
    "ferencvarosi tc|HUN": ("Ferencváros", "FTC", "#00843D", "#FFFFFF"), "lech poznan|POL": ("Lech Poznań", "LPO", "#1C4DA1", "#FFFFFF"),
    "jagiellonia białystok|POL": ("Jagiellonia", "JAG", "#F6D300", "#D7181F"), "levski sofia|BUL": ("Levski Sofia", "LEV", "#0055A4", "#FFFFFF"),
    "cska sofia|BUL": ("CSKA Sofia", "CSKA", "#D7181F", "#FFFFFF"), "nk celje|SVN": ("Celje", "CEL", "#F6D300", "#0055A4"),
    "omonia nikosia|CYP": ("Omonia", "OMO", "#00843D", "#FFFFFF"), "pafos|CYP": ("Pafos", "PAF", "#0A3E8C", "#FFFFFF"),
    "hapoel be'er sheva|ISR": ("Hapoel Beer-Sheva", "HBS", "#E30613", "#FFFFFF"), "lillestrom|NOR": ("Lillestrøm", "LSK", "#F6D300", "#111111"),
    "brann|NOR": ("Brann", "BRA", "#E30613", "#FFFFFF"), "bodø/glimt|NOR": ("Bodø/Glimt", "BOD", "#FFE600", "#111111"),
    "viking|NOR": ("Viking", "VIK", "#1C3F94", "#FFFFFF"), "mjallby aif|SWE": ("Mjällby", "MAIF", "#F6D300", "#111111"),
    "lugano|SUI": ("Lugano", "LUG", "#111111", "#FFFFFF"), "thun|SUI": ("Thun", "THU", "#E30613", "#FFFFFF"),
    "shakhtar donetsk|UKR": ("Shakhtar Donetsk", "SHA", "#F26522", "#111111"), "slovan bratislava|SVK": ("Slovan Bratislava", "SLO", "#2E7CC4", "#FFFFFF"),
    "sabah|AZE": ("Sabah", "SAB", "#E31E24", "#FFFFFF"), "ararat-armenia|ARM": ("Ararat-Armenia", "ARA", "#E30613", "#F6D300"),
    "kuopion ps|FIN": ("KuPS", "KUPS", "#F6D300", "#111111"), "riga|LVA": ("Riga FC", "RIG", "#0A3E8C", "#FFFFFF"),
    "kairat|KAZ": ("Kairat", "KAI", "#F6D300", "#111111"), "cs universitatea craiova|ROU": ("U Craiova", "UCV", "#0055A4", "#FFFFFF"),
    "inter d'escaldes|AND": ("Inter Escaldes", "IEC", "#F6D300", "#0055A4"), "egnatia rrogozhine|ALB": ("Egnatia", "EGN", "#E30613", "#111111"),
    "borac banja luka|BIH": ("Borac", "BOR", "#E30613", "#0055A4"), "zalgiris|LTU": ("Žalgiris", "ZAL", "#00843D", "#FFFFFF"),
    "iberia 1999|GEO": ("Iberia 1999", "IBE", "#0055A4", "#FFFFFF"), "lincoln red imps|GIB": ("Lincoln Red Imps", "LRI", "#E30613", "#FFFFFF"),
}

PALETTE = ["#E30613", "#0055A4", "#00843D", "#F6D300", "#6C2C91", "#F58220", "#111111", "#12A0D7", "#8B1D41"]


def info(k, fallback_name, lang="en"):
    if k.endswith("|NAT"):  # national teams (Nations League): data/nations.json, Turkish names for Turkish captions
        from .leagues import NATIONS
        t = NATIONS.get(fallback_name)
        if t:
            return {"name": t["name_tr"] if lang == "tr" else t["name"], "short": t["short"], "c1": t["c1"], "c2": t["c2"]}
    if k.endswith("|W"):  # women's clubs (Women's Champions League): data/womens.json
        from .leagues import WOMENS
        t = WOMENS.get(fallback_name)
        if t:
            return {"name": t["name"], "short": t["short"], "c1": t["c1"], "c2": t["c2"]}
    if k in T:
        name, short, c1, c2 = T[k]
        return {"name": name, "short": short, "c1": c1, "c2": c2}
    name = re.sub(r"\b(FC|AFC|CF|SC|AC|SK|FK|Calcio)\b", "", fallback_name).strip() or fallback_name
    words = [w for w in re.split(r"[\s\-/]+", name) if w]
    short = (words[0][:3] if len(words) == 1 else "".join(w[0] for w in words[:3])).upper()
    h = int(hashlib.md5(k.encode()).hexdigest(), 16)
    c1 = PALETTE[h % len(PALETTE)]
    c2 = "#FFFFFF" if c1 not in ("#F6D300",) else "#111111"
    return {"name": name, "short": short, "c1": c1, "c2": c2}
