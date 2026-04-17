from dataclasses import dataclass


@dataclass(frozen=True)
class FeedSource:
    name: str
    url: str
    category: str


FEEDS: list[FeedSource] = [
    # World / General
    FeedSource("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml", "world"),
    FeedSource("Reuters World", "https://feeds.reuters.com/reuters/worldNews", "world"),
    FeedSource("AP Top News", "https://feeds.apnews.com/apnews/topnews", "world"),
    FeedSource("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml", "world"),
    FeedSource("DW World", "https://rss.dw.com/rdf/rss-en-world", "world"),
    FeedSource("France24", "https://www.france24.com/en/rss", "world"),
    FeedSource("NPR World", "https://feeds.npr.org/1004/rss.xml", "world"),
    FeedSource("Guardian World", "https://www.theguardian.com/world/rss", "world"),
    FeedSource("Euronews", "https://www.euronews.com/rss?format=mrss&level=theme&name=news", "world"),
    FeedSource("SCMP World", "https://www.scmp.com/rss/2/feed", "world"),

    # Geopolitics
    FeedSource("Foreign Policy", "https://foreignpolicy.com/feed/", "geopolitics"),
    FeedSource("Council on Foreign Relations", "https://www.cfr.org/rss/region/global", "geopolitics"),
    FeedSource("Stratfor", "https://worldview.stratfor.com/rss.xml", "geopolitics"),
    FeedSource("The Diplomat", "https://thediplomat.com/feed/", "geopolitics"),
    FeedSource("War on the Rocks", "https://warontherocks.com/feed/", "geopolitics"),
    FeedSource("Defense One", "https://www.defenseone.com/rss/all/", "geopolitics"),
    FeedSource("Arms Control Wonk", "https://www.armscontrolwonk.com/feed/", "geopolitics"),

    # Conflict / Security
    FeedSource("Bellingcat", "https://www.bellingcat.com/feed/", "conflict"),
    FeedSource("Acled", "https://acleddata.com/feed/", "conflict"),
    FeedSource("RAND Security", "https://www.rand.org/topics/national-security.rss", "conflict"),
    FeedSource("ISW", "https://www.understandingwar.org/rss.xml", "conflict"),
    FeedSource("Jane's 360", "https://www.janes.com/feeds/news", "conflict"),
    FeedSource("Small Arms Survey", "https://www.smallarmssurvey.org/rss.xml", "conflict"),

    # Cyber
    FeedSource("Krebs on Security", "https://krebsonsecurity.com/feed/", "cyber"),
    FeedSource("BleepingComputer", "https://www.bleepingcomputer.com/feed/", "cyber"),
    FeedSource("SANS ISC", "https://isc.sans.edu/rssfeed.xml", "cyber"),
    FeedSource("Threatpost", "https://threatpost.com/feed/", "cyber"),
    FeedSource("Dark Reading", "https://www.darkreading.com/rss.xml", "cyber"),
    FeedSource("Recorded Future", "https://www.recordedfuture.com/feed", "cyber"),
    FeedSource("CISA Alerts", "https://www.cisa.gov/uscert/ncas/alerts.xml", "cyber"),
    FeedSource("Schneier on Security", "https://www.schneier.com/feed/atom", "cyber"),

    # Energy
    FeedSource("Oil Price", "https://oilprice.com/rss/main", "energy"),
    FeedSource("Reuters Energy", "https://feeds.reuters.com/reuters/energyNews", "energy"),
    FeedSource("EIA", "https://www.eia.gov/rss/news.xml", "energy"),
    FeedSource("S&P Energy", "https://www.spglobal.com/commodityinsights/en/rss-feed/oil", "energy"),
    FeedSource("Platts", "https://www.spglobal.com/platts/en/rss-feed/natural-gas", "energy"),

    # Finance / Economy
    FeedSource("FT World Economy", "https://www.ft.com/world?format=rss", "finance"),
    FeedSource("Bloomberg Markets", "https://feeds.bloomberg.com/markets/news.rss", "finance"),
    FeedSource("IMF News", "https://www.imf.org/en/News/rss", "finance"),
    FeedSource("World Bank", "https://feeds.worldbank.org/worldbank/news-rss", "finance"),
    FeedSource("Project Syndicate", "https://www.project-syndicate.org/rss", "finance"),

    # Regional — Asia
    FeedSource("Nikkei Asia", "https://asia.nikkei.com/rss/feed/nar", "regional_asia"),
    FeedSource("South China Morning Post Asia", "https://www.scmp.com/rss/4/feed", "regional_asia"),
    FeedSource("The Hindu", "https://www.thehindu.com/news/international/feeder/default.rss", "regional_asia"),
    FeedSource("Straits Times", "https://www.straitstimes.com/news/world/rss.xml", "regional_asia"),
    FeedSource("Taiwan News", "https://www.taiwannews.com.tw/en/rss/index.rss", "regional_asia"),

    # Regional — Europe
    FeedSource("Politico EU", "https://www.politico.eu/feed/", "regional_europe"),
    FeedSource("Der Spiegel International", "https://www.spiegel.de/international/index.rss", "regional_europe"),
    FeedSource("EUobserver", "https://euobserver.com/rss.xml", "regional_europe"),
    FeedSource("Kyiv Independent", "https://kyivindependent.com/feed/", "regional_europe"),
    FeedSource("Balkan Insight", "https://balkaninsight.com/feed/", "regional_europe"),

    # Regional — Americas
    FeedSource("Latin America Reports", "https://www.latinnews.com/rss.xml", "regional_americas"),
    FeedSource("InSight Crime", "https://insightcrime.org/feed/", "regional_americas"),
    FeedSource("The Brazil Report", "https://thebrazilreport.com/feed/", "regional_americas"),

    # Tech / General
    FeedSource("MIT Tech Review", "https://www.technologyreview.com/feed/", "tech"),
    FeedSource("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index", "tech"),
    FeedSource("The Verge", "https://www.theverge.com/rss/index.xml", "tech"),
]
