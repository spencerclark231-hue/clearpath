"""
Build the CLEARPATH knowledge base.

Turns the raw CSVs in data/raw/ (pulled from IMF PortWatch, World Bank, Drewry,
NY Fed, insurance-market reporting, the Joint War Committee, etc.) plus researched
narrative into 11 documents in documents/:

  * 9 PDFs  - with running headers, footers and "Page X of Y" lines on every page
              (deliberate real-world formatting noise for the cleaning stage)
  * 2 TXTs  - plain text briefs, to show multi-format loading

Every fact is attributed to its source inside the document. Run:

    python scripts/build_knowledge_base.py
"""
from __future__ import annotations

import csv
from pathlib import Path

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "documents"
COMPILED = "Compiled 26 November 2026"


def rows(name: str) -> list[dict]:
    with open(RAW / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def pct(v: str) -> str:
    v = int(float(v))
    return f"+{v}%" if v > 0 else f"{v}%"


# --------------------------------------------------------------------------- #
# PDF rendering
# --------------------------------------------------------------------------- #
STY_TITLE = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=17, leading=21, spaceAfter=4)
STY_SUB = ParagraphStyle("s", fontName="Helvetica", fontSize=10, leading=13, textColor="#555555", spaceAfter=14)
STY_H = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=11.5, leading=15, spaceBefore=10, spaceAfter=5)
STY_P = ParagraphStyle("p", fontName="Helvetica", fontSize=9.6, leading=13.2, alignment=TA_LEFT, spaceAfter=6)
STY_B = ParagraphStyle("b", parent=STY_P, leftIndent=12, bulletIndent=2, spaceAfter=3)


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_pdf(doc: dict) -> None:
    path = OUT / doc["file"]
    header = f"CLEARPATH KNOWLEDGE BASE  |  {doc['code']}  |  {doc['short']}"

    def on_page(canvas, d):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillGray(0.45)
        canvas.drawString(0.8 * inch, LETTER[1] - 0.5 * inch, header)
        canvas.drawString(0.8 * inch, 0.45 * inch, f"{COMPILED}  -  Internal reference document")
        canvas.drawRightString(LETTER[0] - 0.8 * inch, 0.45 * inch, f"Page {d.page} of {d._total}")
        canvas.restoreState()

    class Doc(SimpleDocTemplate):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self._total = 0

    def make_story():
        story = [Paragraph(esc(doc["title"]), STY_TITLE), Paragraph(esc(doc["subtitle"]), STY_SUB)]
        for heading, blocks in doc["sections"]:
            story.append(Paragraph(esc(heading), STY_H))
            for b in blocks:
                if b.startswith("- "):
                    story.append(Paragraph(esc(b[2:]), STY_B, bulletText="•"))
                else:
                    story.append(Paragraph(esc(b), STY_P))
            story.append(Spacer(1, 4))
        return story

    # two-pass build so the footer can print "Page X of Y"
    tmp = Doc(str(path), pagesize=LETTER, leftMargin=0.8 * inch, rightMargin=0.8 * inch,
              topMargin=0.85 * inch, bottomMargin=0.8 * inch, title=doc["title"])
    tmp._total = 99
    tmp.build(make_story(), onFirstPage=on_page, onLaterPages=on_page)
    final = Doc(str(path), pagesize=LETTER, leftMargin=0.8 * inch, rightMargin=0.8 * inch,
                topMargin=0.85 * inch, bottomMargin=0.8 * inch, title=doc["title"])
    final._total = tmp.page
    final.build(make_story(), onFirstPage=on_page, onLaterPages=on_page)


def build_txt(doc: dict) -> None:
    lines = [doc["title"], doc["subtitle"], "=" * 72, ""]
    for heading, blocks in doc["sections"]:
        lines += [heading.upper(), "-" * len(heading)]
        for b in blocks:
            lines.append(b)
        lines.append("")
    lines += ["", f"[{doc['code']}] {COMPILED}"]
    (OUT / doc["file"]).write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------------------------------- #
# Document content
# --------------------------------------------------------------------------- #
def doc_chokepoints() -> dict:
    status = rows("portwatch_chokepoint_status_2026-11-22.csv")
    db = {r["portname"]: r for r in rows("portwatch_chokepoints_database.csv")}
    table = [
        f"- {r['chokepoint']}: {r['ships_per_day_7d']} transits per day (7-day average), "
        f"{pct(r['change_vs_year_ago_pct'])} versus the same week a year earlier; "
        f"{r['tankers_per_day_7d']} tankers per day, {pct(r['tankers_vs_early2023_pct'])} versus the January-October 2023 baseline."
        for r in status
    ]
    profile = []
    for r in status:
        d = db.get(r["chokepoint"])
        if not d:
            continue
        inds = ", ".join(x for x in (d["industry_top1"], d["industry_top2"], d["industry_top3"]) if x)
        profile.append(
            f"- {d['portname']}: {int(d['vessel_count_total']):,} vessels in the PortWatch reference count "
            f"({int(d['vessel_count_container']):,} container, {int(d['vessel_count_dry_bulk']):,} dry bulk, "
            f"{int(d['vessel_count_general_cargo']):,} general cargo, {int(d['vessel_count_RoRo']):,} RoRo, "
            f"{int(d['vessel_count_tanker']):,} tanker)."
            + (f" Top industries by trade value: {inds}." if inds else "")
        )
    return dict(
        code="SCI-01", file="SCI-01_Global_Chokepoint_Traffic_Monitor.pdf", short="Chokepoint Traffic Monitor",
        title="Global Chokepoint Traffic Monitor - Week Ending 22 November 2026",
        subtitle="Daily transit counts for 28 maritime chokepoints. Source data: IMF PortWatch (UN Global Platform AIS), "
                 "retrieved via the PortWatch ArcGIS API and the DaveManuel.com PortWatch tracker (data pulled 25 Nov 2026).",
        sections=[
            ("1. About this monitor", [
                "This monitor summarizes how many ships crossed each of the 28 maritime chokepoints tracked by the IMF's "
                "PortWatch platform. PortWatch detects ships crossing each chokepoint from satellite AIS position data "
                "provided by the UN Global Platform; a ship is counted once per crossing. Figures below are seven-day averages "
                "for the week ending 22 November 2026, compared with the same week one year earlier. Tanker counts are "
                "compared with an early-2023 baseline (January to October 2023), before the Red Sea and Hormuz crises.",
                "Important limitation: ships that switch off AIS transponders are not counted. During the 2026 Hormuz crisis, "
                "monitoring groups estimated roughly 30 escorted ships per day in October that transmitted no AIS signal, so "
                "satellite counts should be treated as a floor rather than an exact figure.",
            ]),
            ("2. Headline figures", [
                "Across all 28 chokepoints PortWatch recorded about 1,743 transits per day in the latest week, down 10% year on "
                "year (this is a sum of crossings, not unique ships). Eight of the 28 chokepoints are down 20% or more year on year.",
                "The most severe disruption is at the Strait of Hormuz, which averaged only 3 transits per day (-96% year on year) "
                "and 0 tankers per day against 36 a year earlier. Before the 2026 war PortWatch typically counted about 60 ships "
                "per day through Hormuz. The Kerch Strait recorded 0 transits (-100%) after Russia halted passage on 10 July 2026 "
                "following Ukrainian strikes on 13 vessels in the Sea of Azov.",
                "Other chokepoints with large declines: Bosporus Strait 49 per day (-48%), Bab el-Mandeb Strait 27 per day (-31%, "
                "tankers -64% versus early 2023), Cape of Good Hope 69 per day (-22%), Oresund Strait (-20%), Tsugaru Strait (-20%), "
                "Ombai Strait (-42%) and Bering Strait (-60%, seasonal).",
                "Chokepoints with traffic growth: Magellan Strait (+96%), Mindoro Strait (+74%), Luzon Strait (+44%), Balabac Strait "
                "(+36%), Makassar Strait (+19%), Lombok Strait (+13%), Suez Canal (+12%) and Taiwan Strait (+7%). Some Suez traffic "
                "returned in 2026 as carriers re-evaluated routings during the Hormuz crisis, although Red Sea risk rose again "
                "in the second half of the year.",
            ]),
            ("3. Full chokepoint table (week ending 22 Nov 2026)", table),
            ("4. Structural profile: vessel mix and cargo at each chokepoint", [
                "The PortWatch chokepoints database records a reference count of vessel transits by vessel type and the top "
                "industries (by trade value) moving through each passage. Use these figures to judge how exposed a given cargo "
                "type is to each chokepoint. Mineral products (which include crude oil, refined fuels and ores) are the top "
                "industry at every chokepoint where data are available.",
            ] + profile),
            ("5. What this means for a containerized importer", [
                "Container exposure is greatest at the Taiwan Strait (31,190 container transits in the reference count), Korea "
                "Strait (20,682), Malacca Strait (18,154), Dover Strait (12,535) and Gibraltar Strait (11,698). Suez Canal and Bab "
                "el-Mandeb each carry about 5,000 container transits in the reference count, so a Red Sea disruption mainly hits "
                "Asia-Europe and Asia-Mediterranean services.",
                "The Taiwan Strait carried 223 ships per day (+7%) in the latest week. China staged a blockade-style exercise in "
                "December 2025 and began 2026 coast-guard patrols that radio passing cargo ships, but commercial traffic has not "
                "been disrupted to date. Because it is the busiest container chokepoint in the dataset, it remains a key "
                "low-probability, high-impact risk to monitor.",
                "The Panama Canal averaged 28 ships per day (-8%). Drought-related capacity limits during 2026 are covered in SCI-04.",
            ]),
        ],
    )


def doc_hormuz() -> dict:
    return dict(
        code="SCI-02", file="SCI-02_Strait_of_Hormuz_Crisis_Brief_2026.pdf", short="Hormuz Crisis Brief",
        title="Strait of Hormuz Crisis Brief - 2026",
        subtitle="Timeline, traffic, energy and insurance impact of the 2026 closure of the Strait of Hormuz. Sources: IMF PortWatch, "
                 "EIA, S&P Global Platts, Marsh, BRS, Insurance Journal, Insurance Business, The National, Caixin, Green Worldwide, ENGINE.",
        sections=[
            ("1. Why Hormuz matters", [
                "In normal times the Strait of Hormuz carries about 20 million barrels of oil per day (EIA: 21.8 mb/d in 2023, 20.7 "
                "mb/d in 2024 and 20.9 mb/d in the first half of 2025), plus more than a fifth of global LNG trade, mostly from Qatar. "
                "Before the 2026 war, PortWatch typically counted about 60 ships per day through the strait.",
                "Bypass capacity is limited: Saudi and UAE pipelines can carry roughly 4.7 million barrels per day around Hormuz, "
                "well short of normal strait flows.",
            ]),
            ("2. Timeline of the 2026 crisis", [
                "- 28 February 2026: US and Israeli strikes on Iran. PortWatch recorded 57 transits that day.",
                "- About 2 March 2026: the strait was declared closed; the transit count reached zero by 4 March.",
                "- 3 March 2026: the London market's Joint War Committee issued circular JWLA-033, adding Bahrain, Djibouti, Kuwait, Oman "
                "and Qatar to the listed areas and amending the Persian/Arabian Gulf, Gulf of Oman, Indian Ocean, Gulf of Aden and "
                "Southern Red Sea waters (see SCI-06).",
                "- 8 April 2026: temporary ceasefire. The strait stayed effectively shut through spring while the US Navy blockaded "
                "Iranian shipping.",
                "- 17 June 2026: US-Iran memorandum. Traffic peaked at 51 transits on 24 June, the high since the war began.",
                "- 27 June 2026: renewed hostilities undermined the ceasefire.",
                "- 14 July 2026: the US reimposed its blockade and traffic fell back to single digits.",
                "- 31 August 2026: fighting resumed, with two supertankers hit. Saudi Arabia shut its East-West pipeline on 10 September.",
                "- Mid-October 2026: the IMO had counted more than 100 incidents and at least 24 seafarer deaths.",
                "- November 2026: IMO records show additional commercial vessels damaged in incidents on 4, 5, 7, 10, 11, 13 and 15 "
                "November. In the week ending 22 November, PortWatch counted 3 transits per day (-96% year on year) and no tankers.",
            ]),
            ("3. Energy price impact", [
                "Brent crude was about $72 per barrel on 27 February 2026, closed above $115 in late April, and has swung with each "
                "ceasefire and attack since. The EIA reported a Q2 2026 Brent average of $102.93 per barrel. Bunker fuel impacts are "
                "covered in SCI-08.",
            ]),
            ("4. War-risk insurance impact", [
                "Before the conflict, the additional war-risk premium (AWRP) for a vessel transiting Hormuz was about 0.25% of hull value. "
                "In early March insurers began writing seven-day cover at about 1% of hull value (Caixin; Marsh put ratings at 1-1.5%). "
                "The Persian Gulf AWRP peaked near 2.5% of hull and machinery value per seven-day period in early March and eased "
                "to about 1% by late March (S&P Global Platts).",
                "Rates escalated sharply after spring: BRS put the premium at about 10% of hull value in mid-June, with European tanker "
                "sources quoting 7-9% for clean tankers and 5-5.75% for crude tankers. After the June peace memorandum the rate fell "
                "to about 3-4% (from 4.5-6%), then rose to as much as 6% by 10 July and to 7.5-10% of hull value by 22 July (Marsh).",
                "Worked example (The National): at these rates a $100 million tanker faces a war-risk premium of $3 million to $10 million, "
                "compared with about $250,000 before the war.",
                "Market capacity responses: on 19 June 2026 Chubb launched a war-risk consortium with Lloyd's syndicates offering up to "
                "$200 million for hull and third-party liabilities and $200 million for cargo. Chubb, AIG and Berkshire Hathaway backed "
                "a $40 billion US reinsurance facility. Marsh estimated global hull war capacity at $2.5-3 billion.",
            ]),
            ("5. Implications for importers", [
                "Any cargo routed to or from Persian Gulf ports carries listed-area war-risk exposure. Cargo war-risk pricing is being "
                "quoted voyage by voyage, with market ranges reported from 2 cents to 2% of cargo value (Risk & Insurance, October 2026). "
                "Shippers typically see these costs as carrier war-risk surcharges on top of base freight.",
                "Satellite transit counts understate actual traffic because escorted ships may run without AIS; decisions should combine "
                "PortWatch data with carrier advisories and insurer notices.",
            ]),
        ],
    )


def doc_redsea() -> dict:
    return dict(
        code="SCI-03", file="SCI-03_Red_Sea_and_Suez_Canal_Brief.pdf", short="Red Sea & Suez Brief",
        title="Red Sea, Bab el-Mandeb and Suez Canal Brief - November 2026",
        subtitle="Security situation, transit volumes, canal tolls and routing economics. Sources: Lloyd's List Intelligence, IMF PortWatch, "
                 "Drewry, Suez Canal Authority circulars (via Hellenic Shipping News, FreshPlaza, Port Technology), Africa Center for "
                 "Strategic Studies, Al Jazeera, AP, gCaptain, Xeneta, Ambrey, S&P Global.",
        sections=[
            ("1. Background", [
                "The Red Sea corridor links Asia with Europe and the Mediterranean via the Bab el-Mandeb Strait and the Suez Canal. "
                "In normal conditions roughly 10-15% of global seaborne trade uses the corridor; UNCTAD estimates the Suez Canal "
                "alone carries about 12-15% of world trade.",
                "The Houthi campaign against merchant shipping began on 19 November 2023 with the seizure of the Galaxy Leader. "
                "Attacks paused after the Gaza ceasefire of October 2025, and from about 11 November 2025 until late February 2026 "
                "there were no sustained, confirmed missile or drone attacks on merchant vessels attributed to the group.",
            ]),
            ("2. The 2026 escalation", [
                "Houthi attacks on shipping resumed in July 2026, initially targeting Saudi-linked shipping, after the group declared "
                "a maritime blockade of Saudi Arabia. The Africa Center for Strategic Studies counted 12 attacks or attempted attacks "
                "on commercial vessels in the southern Red Sea between July and October 2026.",
                "In September 2026 the Houthis seized the port of Mocha and Perim Island beside the Bab el-Mandeb strait. In August an "
                "attack on the Egyptian-owned cargo ship Tihamah in the strait killed at least six people, including crew and rescuers, "
                "according to Yemeni authorities - the first shipping deaths linked to the Houthis since the Iran war began. On 11 "
                "November 2026 two US Navy warships were targeted with drones and missiles in the Bab el-Mandeb; the attacks failed.",
                "Risk consultancy Ambrey places Saudi-flagged, Saudi-owned or Saudi-operated vessels, and ships calling at Saudi Red Sea "
                "ports, in a high-risk category.",
            ]),
            ("3. Transit volumes", [
                "Lloyd's List Intelligence (Red Sea Brief, 12 November 2026): the Suez Canal handled 1,338 transits (125.6 million dwt) in "
                "October 2026, up from 1,228 transits (106.3 million dwt) in September. October traffic was up 63% year on year but still "
                "34% below pre-Houthi-crisis levels. The Bab el-Mandeb handled 1,363 transits (112.3 million dwt) in October, compared "
                "with a January-November 2023 monthly average of 2,009 transits (182 million dwt).",
                "Container shipping is returning: Drewry counted 57 containership transits through the Suez Canal in the week ending 15 "
                "November 2026, up 73% from the same week in 2025. IMF PortWatch shows the Suez Canal at 46 ships per day (+12% year on "
                "year) and the Bab el-Mandeb at 27 per day (-31%) in the week ending 22 November.",
                "Carrier moves in 2026 include the Maersk/Hapag-Lloyd ME-11 service rerouting back through Suez with 24,000 TEU-class "
                "ships (February 2026) and Maersk announcing that one of its Gemini services with Hapag-Lloyd would return to the "
                "trans-Suez corridor. CMA CGM has been one of the few carriers to keep scheduled Red Sea services throughout.",
            ]),
            ("4. Suez Canal transit fees", [
                "The Suez Canal Authority (SCA) introduced a 15% rebate on transit tolls for container ships of 130,000 Suez Canal Net "
                "Tonnage or more on 15 May 2025 (Navigational Circular No. 3/2025), applying in both directions, laden or ballast, "
                "granted automatically. It was extended to 30 June 2026, then suspended with effect from 7 April 2026 without an "
                "official explanation. Industry observers linked the withdrawal to the small number of ships still transiting and to "
                "falling revenue during the Hormuz crisis.",
                "Egypt's Suez Canal revenue fell from $10.2 billion in 2023 to $4.1 billion in 2025.",
            ]),
            ("5. Insurance cost of the Red Sea route", [
                "The Red Sea additional war-risk premium fell to about 0.2% of hull value in December 2025, its lowest since November "
                "2023. After the Houthis' Saudi embargo it jumped about 150%, from roughly 0.3% to about 0.75% of vessel value "
                "(July 2026). In late July, premiums for Bab el-Mandeb transits were about 0.5% of hull value versus about 0.1% for "
                "ships staying in the Red Sea near western Saudi Arabia en route to Suez. See SCI-05 for the full rate history.",
            ]),
            ("6. Suez versus Cape of Good Hope routing", [
                "The detour around the Cape of Good Hope, used since the Red Sea attacks began, adds more than 10 days per Asia-Europe "
                "voyage according to the IMF. Xeneta estimates the longer Cape routing absorbs about 2 million TEU of global container "
                "capacity. A large-scale return to the Red Sea would release that capacity and could push freight rates sharply lower, "
                "although Xeneta does not expect an imminent return to 2023 levels.",
                "PortWatch shows Cape of Good Hope traffic at 69 ships per day (-22% year on year), but tanker traffic around the Cape is "
                "up 40% versus early 2023 as oil flows avoid the Red Sea. EIA data show Cape oil flows rising from 6.2 mb/d in 2023 to "
                "9.3 mb/d in 2024, while Bab el-Mandeb flows fell from 9.3 to 4.1 mb/d.",
            ]),
        ],
    )


def doc_panama() -> dict:
    ev = rows("panama_canal_2026.csv")
    evl = [f"- {r['date']}: {r['event']}" + (f" ({r['value']})" if r['value'] else "") + f". Source: {r['source']}." for r in ev]
    return dict(
        code="SCI-04", file="SCI-04_Panama_Canal_Operations_and_Fees_2026.pdf", short="Panama Canal Operations",
        title="Panama Canal Operations, Transit Slots and Fees - 2026",
        subtitle="Drought restrictions, booking system, auction prices and the 2027 dry-season slot allocation. Sources: Panama Canal "
                 "Authority (ACP) advisories, gCaptain, Maritime Executive, DTN, Rio Times, Argus, IMF PortWatch, EIA.",
        sections=[
            ("1. Role of the canal", [
                "The Panama Canal carries about 5% of world maritime trade according to the Panama Canal Authority (ACP), and the United "
                "States is its biggest user. Normal capacity is 38-40 transits per day. The canal depends on rain-fed freshwater from "
                "Gatun Lake, which makes it vulnerable to drought.",
                "In the 2023-2024 drought, daily transits fell from the normal 38-40 to 32 and then to as few as 20 booking slots per day "
                "by January 2024. That crisis moved the canal from a first-come, first-served system to a pre-booked slot and auction model.",
            ]),
            ("2. How transit slots are sold", [
                "The ACP sells reservations in booking periods. Unsold or cancelled capacity feeds a daily auction; on a normal day three "
                "to five slots reach the auction, mainly from cancelled bookings. From 3 September 2026 the daily auction slot for "
                "Neopanamax, Supers and Regular vessels was organized into groups, with Group 1 for LNG and LPG carriers and Group 2 for "
                "dry bulk carriers, general cargo and others. Customer limits do not apply to slots won at auction.",
                "Long-term Slot Allocation (LoTSA): for the 2027 dry season (3 January to 3 April 2027) the ACP is auctioning 558 slots in "
                "advance. The Neopanamax programme offers 36 packages totalling 270 slots (165 northbound, 105 southbound) in a sealed-bid "
                "auction on 17 November 2026. For the first time the older Panamax locks join the scheme, through a pilot auction on 24 "
                "November 2026.",
            ]),
            ("3. 2026 drought restrictions and record auction prices", [
                "Forecasts of a moderate-to-strong 2026 El Nino (the WMO put the chance of El Nino developing in June-August 2026 at about "
                "80%) led the ACP to impose restrictions from mid-2026. Auction prices hit records: the gas carrier G. Arete paid $4.6 "
                "million for a Neopanamax slot on 14 August, and SK Gas paid a record $5.3 million for the LPG carrier G. Spirit to transit "
                "on 1 September 2026 - the highest price ever paid for a single Panama Canal transit slot.",
                "Daily capacity was cut to 34 transits from 3 September and 32 from 15 September 2026, the most significant restrictions "
                "since 2023-2024. Conditions then improved: on 28 September the ACP added a slot and a foot of draft, and in a 9 November "
                "2026 advisory it raised daily capacity to 34 vessels and restored the maximum Neopanamax draft to 50 feet, citing better "
                "lake levels and favourable hydrological forecasts. PortWatch showed 28 ships per day (-8% year on year) in the week "
                "ending 22 November.",
            ]),
            ("4. 2026 event log", evl),
            ("5. Implications for shippers", [
                "Carriers that secure LoTSA slots can avoid dry-season queues and auction premiums; shippers on US East Coast-Asia "
                "services via Panama should ask carriers whether their services hold LoTSA allocations for January-April 2027. Panama "
                "Canal oil flows are modest (EIA: 2.2 mb/d in fiscal 2023, 2.3 mb/d in the first half of 2025), but LNG and LPG carriers "
                "have been the most aggressive auction bidders, which drives the record prices.",
            ]),
        ],
    )


def doc_insurance() -> dict:
    rr = rows("war_risk_premiums_2026.csv")
    tl = []
    for r in rr:
        rng = r["rate_low_pct"] if r["rate_low_pct"] == r["rate_high_pct"] else f"{r['rate_low_pct']}-{r['rate_high_pct']}"
        tl.append(f"- {r['date']} | {r['region']} | {r['cover']}: {rng}% ({r['basis']}). Source: {r['source']}.")
    return dict(
        code="SCI-05", file="SCI-05_Marine_War_Risk_Insurance_Pricing_Bulletin.pdf", short="War-Risk Insurance Bulletin",
        title="Marine War-Risk Insurance Pricing Bulletin - 2026",
        subtitle="How hull and cargo war-risk cover is priced, and the 2025-2026 rate history for Hormuz, the Persian Gulf, the Red Sea and "
                 "Bab el-Mandeb. Sources: Marsh, BRS, WTW, Aon, LMA, Argus, S&P Global Platts, Insurance Journal, Al Jazeera, Risk & Insurance.",
        sections=[
            ("1. How war-risk insurance works", [
                "Physical damage to ships is covered by hull and machinery insurance, and cargo by marine cargo insurance, but standard "
                "policies exclude war perils such as missile strikes, drone attacks, mines and seizure. Ships carry separate war-risk "
                "cover, usually with an annual premium, but that annual cover does not extend to the most dangerous zones, known as "
                "listed areas, which are published by the London market's Joint War Committee (see SCI-06).",
                "To enter a listed area an owner must notify underwriters and buy an Additional War Risk Premium (AWRP). The AWRP is "
                "priced as a percentage of the vessel's hull value, is typically valid for seven days, and during the 2026 crisis was "
                "being reviewed every 24 to 48 hours. Rating is negotiated case by case between underwriters and brokers; the JWC "
                "plays no role in pricing. Ships linked to US or Israeli ownership or management have been quoted considerably higher rates.",
                "Cargo owners buy cargo war-risk cover separately, priced as a percentage of the cargo value. Aon reported in March 2026 "
                "that cargo war quotes were being reviewed voyage by voyage, particularly for energy and bulk commodity trades. "
                "Container shippers usually experience these costs indirectly, as carrier war-risk surcharges added to the freight bill.",
            ]),
            ("2. Rate history, 2025-2026", tl),
            ("3. Reading the numbers", [
                "Hormuz: from a pre-war baseline of 0.25% of hull value, premiums moved to about 1% in early March 2026, peaked around "
                "2.5% in the Persian Gulf, eased to 1% in late March, and then escalated to 7.5-10% by late July 2026 - four times the "
                "five-year average according to Al Jazeera's reporting of S&P Global data. Rates have swung with each ceasefire and attack.",
                "Red Sea: about 0.2% in December 2025 during the ceasefire, rising to about 0.75% after the July 2026 Houthi embargo on "
                "Saudi Arabia. Transits of the Bab el-Mandeb itself were quoted near 0.5%, while ships staying in the northern Red Sea "
                "near western Saudi Arabia paid about 0.1%. In the 2024 Houthi campaign the AWRP rarely reached 1% of hull value.",
                "Black Sea: S&P Global Platts assessed the war-risk premium for crude loaded from Black Sea ports at $2.9 per barrel on 21 "
                "September 2026, up from $0.9 per barrel on 31 December 2025.",
            ]),
            ("4. Worked examples", [
                "Tanker, Hormuz, July 2026: a $100 million tanker at 3-10% pays $3-10 million for war cover, against about $250,000 at the "
                "pre-war rate of 0.25% (The National). Most large tankers are valued at $200-300 million; at 3%, a $250 million tanker "
                "pays about $7.5 million versus about $625,000 before the conflict (Insurance Journal, March 2026).",
                "Illustrative container cargo calculation (CLEARPATH method, not a market quote): a $2,000,000 consignment insured for cargo "
                "war risk at 0.05% costs $1,000; at 0.5% it costs $10,000; at 2% (the top of the October 2026 Hormuz range) it costs "
                "$40,000. Always obtain a voyage-specific quote from the broker.",
            ]),
            ("5. Market capacity", [
                "Marsh estimated global hull war capacity at about $2.5-3 billion in July 2026, noting less appetite from underwriters to "
                "offer spot coverage. On 19 June 2026 Chubb partnered with Lloyd's syndicates to launch a war-risk consortium providing up "
                "to $200 million for hull and third-party liabilities and $200 million for cargo, and Chubb, AIG and Berkshire Hathaway "
                "backed a $40 billion US reinsurance facility. The IMO Secretary-General urged governments to curb high insurance rates, "
                "prompting pushback from insurers.",
            ]),
        ],
    )


def doc_jwc() -> dict:
    la = rows("jwc_listed_areas_jwla035.csv")
    by_region: dict[str, list[str]] = {}
    for r in la:
        by_region.setdefault(r["region"], []).append(r["listed_area"] + (f" ({r['notes']})" if r["notes"] else ""))
    blocks = [f"- {reg}: " + "; ".join(items) + "." for reg, items in by_region.items()]
    return dict(
        code="SCI-06", file="SCI-06_JWC_Listed_Areas_Register_JWLA-035.pdf", short="JWC Listed Areas Register",
        title="Joint War Committee Listed Areas Register - JWLA-035",
        subtitle="Areas of perceived enhanced risk for hull war, piracy, terrorism and related perils, as amended to circular JWLA-035 "
                 "(16 September 2026). Sources: Lloyd's Market Association (LMA), IUA, TT Club, HKSOA, Swedish Club, Insurance Day.",
        sections=[
            ("1. What the listed areas are", [
                "The Joint War Committee (JWC) is a joint committee of the Lloyd's Market Association (LMA) and the International "
                "Underwriting Association (IUA). It publishes a list of Areas of Perceived Enhanced Risk for hull war, piracy, terrorism "
                "and related perils. Ships sailing into a listed area must notify underwriters and may need additional war-risk "
                "cover; how the list is applied to individual contracts is a matter for specific negotiation.",
                "Named countries include their ports and coastal waters up to 12 nautical miles offshore unless specifically varied. "
                "Named ports include all facilities and terminals within the relevant port authority area. Most Protection & Indemnity "
                "(P&I) policies require underlying war-risk insurance, including a primary layer of war P&I, while a vessel is in a listed area.",
            ]),
            ("2. Recent circulars", [
                "- JWLA-032 (18 December 2023): listed areas update during the first Red Sea crisis.",
                "- JWLA-033 (3 March 2026): issued after the outbreak of the Iran war. Added Bahrain, Djibouti, Kuwait, Oman and Qatar, and "
                "amended the Persian/Arabian Gulf, Gulf of Oman, Indian Ocean, Gulf of Aden and Southern Red Sea waters. The LMA said Gulf "
                "states hosting US bases were added because they were now considered targets by Iran. The related advisory took effect "
                "72 hours after issuance rather than the usual 7 days.",
                "- JWLA-034 (29 July 2026): amended the listing for Saudi Arabia.",
                "- JWLA-035 (16 September 2026): the current list. TT Club applied the changes to its members from 30 September 2026.",
            ]),
            ("3. Current listed areas (JWLA-035)", blocks),
            ("4. Defined waters", [
                "Persian/Arabian Gulf, Gulf of Oman, Indian Ocean, Gulf of Aden and Southern Red Sea: waters bounded to the northwest by the "
                "Red Sea south of 25.5 degrees N (excluding Egyptian territorial waters); to the northeast from the Pakistan coastline at "
                "25 deg 19' 15\" N, 65 deg E; to the east by a line through 10 deg 48' N, 65 deg E and 10 deg 48' N, 60 deg 15' E, then to "
                "6 deg 45' S, 48 deg 45' E; and to the southwest by the Somalia border at 1 deg 40' S, 41 deg 34' E.",
                "Gulf of Guinea: waters bounded on the west by the Togo coast, south to 0 deg 40' S, 3 deg E, then east to Cape Lopez "
                "Peninsula, Gabon. Cabo Delgado: the territorial sea of Mozambique and Tanzania between defined points. Europe: the Sea of "
                "Azov; the Black Sea excluding territorial waters of countries other than Russia and Ukraine; inland waters of Ukraine; "
                "specified Russian inland waters on the Don and Donets; and Belarusian inland waters south of 52 deg 30' N.",
            ]),
            ("5. Practical checklist for cargo owners", [
                "- Check every port of call and transit on the routing against the current listed areas before booking.",
                "- Ask the carrier which war-risk surcharges apply to the service and whether they change at short notice.",
                "- Confirm with the cargo insurance broker whether the open cargo policy covers war risk in listed areas and what notice is required.",
                "- Re-check after every new JWC circular; the list changed three times in 2026 (JWLA-033, -034 and -035).",
            ]),
        ],
    )


def doc_freight() -> dict:
    w = rows("drewry_wci_2025_2026.csv")
    comp = [r for r in w if r["route"] == "WCI Composite"]
    lanes = [r for r in w if r["route"] != "WCI Composite"]
    cl = [f"- {r['assessment_date']}: WCI composite ${int(r['usd_per_feu']):,} per 40ft container"
          + (f" ({pct(r['week_change_pct'])} week on week)" if r["week_change_pct"] else "") + "." for r in comp]
    ll = [f"- {r['assessment_date']} | {r['route']}: ${int(r['usd_per_feu']):,} per 40ft"
          + (f" ({pct(r['week_change_pct'])} week on week)" if r["week_change_pct"] else "") + "." for r in lanes]
    return dict(
        code="SCI-07", file="SCI-07_Container_Freight_Rate_Report.pdf", short="Container Freight Rate Report",
        title="Container Freight Rate Report - Drewry World Container Index, November 2026",
        subtitle="Spot container rates, lane detail, capacity management and outlook. Sources: Drewry WCI (via Drewry, ShipUniverse, "
                 "Hellenic Shipping News, Green Worldwide, Daily Cargo News), Xeneta, WorldACD.",
        sections=[
            ("1. About the index", [
                "Drewry's World Container Index (WCI) is a weekly composite of spot rates per 40-foot container (FEU) on eight major "
                "East-West routes, widely referenced by procurement teams for index-linked contracts. Assessments are published on Thursdays.",
            ]),
            ("2. Latest reading", [
                "On 19 November 2026 the WCI composite fell 3% to $4,176 per 40ft container, its fourth consecutive weekly decline, but "
                "remained 126% higher than a year earlier. On 12 November it had fallen 2% to $4,305 (from $4,389 on 5 November), when "
                "Drewry reported a +132% year-on-year change.",
                "Lane detail for 19 November 2026: Shanghai-New York $8,194 (-9%, from $9,020); Shanghai-Los Angeles $7,026 (-5%, from "
                "$7,416); Shanghai-Genoa $4,436 (+6%, from $4,168); Shanghai-Rotterdam $3,496 (roughly flat, from $3,504). Transpacific "
                "rates have now fallen for seven consecutive weeks while Mediterranean rates rebounded.",
            ]),
            ("3. Composite history", cl),
            ("4. Lane history", ll),
            ("5. Capacity and outlook", [
                "Drewry's Container Capacity Insight showed 10 transpacific blank sailings announced for the following week versus 4 in the "
                "week of 19 November, and 4 Asia-Europe/Mediterranean blank sailings versus 5. Drewry expects transpacific rates to keep "
                "falling despite the extra blank sailings, and firmer demand and rates on Asia-Europe and Mediterranean routes approaching "
                "December. Carriers have announced Asia-Europe/Mediterranean peak-season surcharges of $1,000-1,600 per FEU; these are "
                "planned charges, not achieved spot rates.",
                "Port congestion: average vessel waiting time at Shanghai rose to 49 hours from 36 in mid-November 2026.",
                "Structural driver: the Cape of Good Hope diversion absorbs about 2 million TEU of capacity (Xeneta). A large-scale return "
                "to the Red Sea could cause rates to plummet unless carriers idle, scrap or slow-steam ships.",
                "For comparison, the composite was $1,859 on 13 November 2025 and $1,806 on 27 November 2025, before the 2026 Middle East "
                "crisis. It reached $2,557 on 8 January 2026 and was about $4,400-4,500 through September and October 2026.",
            ]),
            ("6. Other modes and labour", [
                "Air cargo: WorldACD reported average global air cargo pricing of $3.45 per kilogram for 2-8 November 2026, up 2% week on "
                "week, even as worldwide volumes softened. Labour: negotiations involving marine terminal watchmen at the Ports of Los "
                "Angeles and Long Beach were extended through 20 November 2026.",
            ]),
        ],
    )


def doc_bunker() -> dict:
    b = rows("bunker_energy_2026.csv")
    e = rows("eia_oil_chokepoint_flows.csv")
    bl = [f"- {r['date']}: {r['metric']} = {r['value']} {r['unit']} (source: {r['source']})" for r in b]
    el = [f"- {r['route']}: {r['flow_2023_mbd']} mb/d in 2023, {r['flow_2024_mbd']} mb/d in 2024, {r['flow_1h2025_mbd']} mb/d in the first half of 2025."
          for r in e]
    return dict(
        code="SCI-08", file="SCI-08_Bunker_Fuel_and_Energy_Cost_Bulletin.txt", short="Bunker & Energy Bulletin",
        title="Bunker Fuel and Energy Cost Bulletin - November 2026",
        subtitle="Marine fuel prices, crude oil and oil flows through chokepoints. Sources: ENGINE bunker market updates, Ship & Bunker, "
                 "ShipUniverse, US Energy Information Administration (EIA) World Oil Transit Chokepoints (updated March 2026).",
        sections=[
            ("1. Why fuel matters to freight costs", [
                "Fuel is the largest variable cost of operating a ship. Carriers pass fuel cost changes to shippers through bunker "
                "adjustment factors (BAF) and emergency bunker surcharges, so bunker prices feed into the total landed cost of imports "
                "with a lag of weeks to months. Longer routings, such as the Cape of Good Hope detour, increase fuel burn per voyage.",
                "Main grades: VLSFO (very low sulphur fuel oil, 0.50% sulphur) is the standard bunker grade; HSFO (high sulphur fuel oil) "
                "is cheaper and used by ships fitted with exhaust scrubbers; LSMGO (low sulphur marine gasoil) is a distillate used in "
                "emission control areas.",
            ]),
            ("2. Price data, 2026", bl),
            ("3. Trend summary", [
                "Singapore VLSFO, the world's largest bunkering hub benchmark, rose four months in a row from a $725/mt monthly average in "
                "June to $926/mt in October 2026, the highest since July 2022, then eased to $867/mt in November to date (to 18 November). "
                "HSFO climbed every month from $550/mt in July to $883/mt in October. Singapore LSMGO peaked at a $1,604/mt monthly average "
                "in March 2026 and stood at $1,201/mt in November. Bunker availability in Singapore has been tight, with suppliers' loading "
                "schedules heavily booked through November and VLSFO lead times of 10-15 days advised in early October.",
                "Brent crude: about $72/bbl before the war (27 February 2026), above $115 in late April, Q2 2026 average $102.93/bbl (EIA). "
                "In November 2026 Brent has been supported by attacks on tankers in and around the Strait of Hormuz and strikes on Russian "
                "refineries, and capped by rising US crude inventories. Saudi Arabia resumed crude loadings at its Red Sea terminal of "
                "Yanbu in early October 2026.",
            ]),
            ("4. Oil flows through chokepoints (EIA, million barrels per day)", el + [
                "Reading the table: the Red Sea crisis shifted oil flows from Bab el-Mandeb and Suez to the Cape of Good Hope in 2024. "
                "Hormuz carried about a fifth of world oil consumption before the 2026 war, which is why its closure moved crude and "
                "bunker prices so sharply.",
            ]),
        ],
    )


def doc_gscpi() -> dict:
    g = rows("gscpi_readings.csv")
    gl = [f"- {r['month']}: GSCPI = {r['gscpi']}" + (f" ({r['note']})" if r["note"] else "") + f". Source: {r['source']}." for r in g]
    return dict(
        code="SCI-09", file="SCI-09_Global_Supply_Chain_Pressure_Index_Brief.txt", short="GSCPI Brief",
        title="Global Supply Chain Pressure Index (GSCPI) Brief - November 2026",
        subtitle="What the New York Fed's GSCPI measures, how to read it, and the 2025-2026 readings. Sources: Federal Reserve Bank of "
                 "New York (Benigno, di Giovanni, Groen and Noble, Staff Report 1017), Reuters, MacroMicro, Trading Economics, SAP Community.",
        sections=[
            ("1. What the index measures", [
                "The GSCPI was developed by economists at the Federal Reserve Bank of New York to give a single gauge of global supply "
                "chain conditions. It combines 27 monthly variables: transportation cost data (including the Baltic Dry Index for bulk "
                "shipping, the Harpex container ship charter index, and air freight costs between the US, Europe and Asia) and supply chain "
                "subcomponents of manufacturing PMI surveys (delivery times, backlogs and purchased stocks) for seven economies: China, "
                "the euro area, Japan, Korea, Taiwan, the United Kingdom and the United States. The delivery-times component is inverted "
                "so that higher readings mean longer delivery times.",
                "The index is the first principal component of these series after removing the part explained by demand. It is measured in "
                "standard deviations from its historical average: 0 means average pressure, +1 means one standard deviation above average, "
                "and negative readings mean below-average pressure. It is not a percentage. Data go back to 1997, and the NY Fed began "
                "publishing it monthly in May 2022.",
                "Release schedule: 10:00 a.m. Eastern Time on the fourth business day of each month. The next release is scheduled for "
                "4 December 2026 (November data).",
            ]),
            ("2. Readings, 2025-2026", gl),
            ("3. Interpretation", [
                "Through 2025 the GSCPI sat close to or below zero, meaning normal or below-normal supply chain pressure. It turned "
                "positive in December 2025 (0.54) and rose through 2026 as the Iran war, the Hormuz closure and the renewed Red Sea "
                "attacks disrupted shipping. Pressure reached a high around May 2026, eased, and then climbed again: August 1.20, "
                "September 1.36 (revised up from an initial 1.28), October 1.26. Readings above 1 indicate pressure more than one standard "
                "deviation above normal - elevated, but far below the record pandemic-era peaks of 2021.",
                "The NY Fed did not explain the October easing, but noted the index had been under modest pressure in recent months amid "
                "supply disruptions tied to the Middle East war.",
                "How to use it: the GSCPI is a lagging, global summary. It is useful for setting the overall risk posture (see the risk "
                "tiers in SCI-11) but does not show lane-specific problems; combine it with chokepoint traffic (SCI-01), freight rates "
                "(SCI-07) and war-risk premiums (SCI-05).",
            ]),
        ],
    )


def doc_lpi() -> dict:
    lp = rows("worldbank_lpi_2023_overall.csv")
    countries = sorted([r for r in lp if r["entity_type"] == "country"], key=lambda r: -float(r["lpi_overall_score"]))
    aggs = [r for r in lp if r["entity_type"] == "aggregate"]
    top = ", ".join(f"{r['entity']} ({float(r['lpi_overall_score']):.1f})" for r in countries[:15])
    bottom = ", ".join(f"{r['entity']} ({float(r['lpi_overall_score']):.1f})" for r in countries[-12:])
    agg = [f"- {r['entity']}: {float(r['lpi_overall_score']):.2f}" for r in aggs]
    bands = {"4.0 and above (top tier)": [], "3.5 to 3.9 (strong)": [], "3.0 to 3.4 (moderate)": [],
             "2.5 to 2.9 (weak)": [], "below 2.5 (very weak)": []}
    for r in countries:
        s = float(r["lpi_overall_score"])
        k = ("4.0 and above (top tier)" if s >= 4 else "3.5 to 3.9 (strong)" if s >= 3.5 else
             "3.0 to 3.4 (moderate)" if s >= 3.0 else "2.5 to 2.9 (weak)" if s >= 2.5 else "below 2.5 (very weak)")
        bands[k].append(f"{r['entity']} ({r['iso3']}) {float(r['lpi_overall_score']):.1f}")
    band_blocks = [f"- LPI score {k}: " + "; ".join(sorted(v)) + "." for k, v in bands.items()]
    return dict(
        code="SCI-10", file="SCI-10_Country_Logistics_Performance_Scorecard.pdf", short="Country Logistics Scorecard",
        title="Country Logistics Performance Scorecard - World Bank LPI 2023",
        subtitle="Overall Logistics Performance Index scores for 139 economies and regional aggregates. Source: World Bank, Connecting to "
                 "Compete 2023 (indicator LP.LPI.OVRL.XQ, retrieved from api.worldbank.org; stored under year 2022 in the WDI database). "
                 "Licence CC BY-4.0.",
        sections=[
            ("1. About the LPI", [
                "The World Bank's Logistics Performance Index (LPI) scores countries from 1 (low) to 5 (high) on the efficiency of their "
                "trade logistics. The overall score combines six components: efficiency of customs and border clearance; quality of trade "
                "and transport infrastructure; ease of arranging competitively priced international shipments; competence and quality of "
                "logistics services; ability to track and trace consignments; and timeliness of shipments reaching the consignee. The "
                "2023 edition is the latest survey-based release; the World Bank's database files the 2023 scores under the year 2022.",
                "In 2026 the World Bank introduced LPI 2.0, moving from perception surveys to shipment-level tracking data across maritime, "
                "aviation and postal networks. Scores in this scorecard are from the 2023 survey-based LPI.",
            ]),
            ("2. Top and bottom performers", [
                f"Highest overall scores: {top}. Singapore (4.3) is the top-ranked economy, followed by Finland (4.2).",
                f"Lowest overall scores in the dataset: {bottom}.",
                "Major Asian sourcing hubs: China 3.7, Japan 3.9, Korea 3.8, Taiwan is not separately reported, Hong Kong SAR 4.0, India 3.4, "
                "Viet Nam 3.3, Malaysia 3.6, Thailand 3.5, Indonesia 3.0, Philippines 3.3, Bangladesh 2.6, Cambodia 2.4. Middle East: "
                "United Arab Emirates 4.0, Saudi Arabia (not in this extract), Oman 3.3, Qatar 3.5, Egypt 3.1. North America: Canada 4.0, "
                "United States 3.8, Mexico 2.9.",
            ]),
            ("3. Regional and income-group averages", agg),
            ("4. All economies by score band", band_blocks),
            ("5. How to use the scorecard in sourcing decisions", [
                "LPI scores proxy the reliability of a country's ports, customs and logistics services. Lower scores typically mean longer "
                "and less predictable lead times and higher buffer-stock needs. The scorecard should be combined with route exposure "
                "(SCI-01) and war-risk listed areas (SCI-06): for example, a supplier in a country with a strong LPI score can still face "
                "disruption if its export route runs through a listed area or a closed chokepoint.",
            ]),
        ],
    )


def doc_playbook() -> dict:
    return dict(
        code="SCI-11", file="SCI-11_Supply_Chain_Risk_Playbook.pdf", short="Supply Chain Risk Playbook",
        title="Supply Chain Risk Playbook (v3.2)",
        subtitle="Policy for logistics, procurement and risk teams. The thresholds are illustrative and reference the real market "
                 "data in SCI-01 to SCI-10.",
        sections=[
            ("1. Purpose and scope", [
                "This playbook covers containerized consumer and industrial goods imported from suppliers in China, Viet Nam, India, "
                "Malaysia and Turkiye into distribution centres in Rotterdam, Genoa, Los Angeles, New York/New Jersey and Montreal. About "
                "9,000 FEU per year move on Asia-North Europe, Asia-Mediterranean, transpacific and Asia-US East Coast lanes. It defines how "
                "supply chain risk is monitored, how routings are chosen, how insurance is bought and how disruptions are escalated.",
            ]),
            ("2. Risk tiers", [
                "The Global Risk Tier is reviewed every Monday by the Logistics Risk Lead using the indicators below. The highest triggered tier applies.",
                "- Tier 1 (Normal): GSCPI below 0.5; no chokepoint on an active lane down more than 20% year on year; WCI composite "
                "below $3,000 per FEU.",
                "- Tier 2 (Elevated): GSCPI between 0.5 and 1.5; OR any chokepoint on an active lane down 20-50% year on year; OR WCI composite "
                "between $3,000 and $5,000 per FEU; OR any new JWC listed-area circular affecting an active lane.",
                "- Tier 3 (Severe): GSCPI above 1.5; OR any chokepoint on an active lane down more than 50% year on year; OR WCI composite above "
                "$5,000 per FEU; OR hull war-risk AWRP above 1% of hull value on an active lane.",
                "Current assessment (week of 23 November 2026): Tier 2 Elevated. GSCPI 1.26 (October), WCI composite $4,176, Bab el-Mandeb "
                "-31% year on year. Hormuz (-96%) is in Tier 3 territory, but no active lane currently routes through Hormuz.",
            ]),
            ("3. Routing rules: Suez versus Cape of Good Hope", [
                "Asia-North Europe and Asia-Mediterranean cargo may be booked on services transiting the Suez Canal only when ALL of the "
                "following hold: (a) the carrier has publicly confirmed a Suez routing for the service; (b) the Red Sea AWRP quoted to the "
                "carrier is at or below 0.5% of hull value; (c) no confirmed attack on a merchant vessel in the Bab el-Mandeb in the "
                "previous 14 days; and (d) the cargo insurance broker confirms war cover for the voyage.",
                "Otherwise cargo must be booked on Cape of Good Hope services. Planners must add at least 10 days to Asia-Europe transit "
                "time assumptions when the Cape routing is used, and increase safety stock at Rotterdam and Genoa by two weeks of demand.",
                "Under the current assessment the Suez condition (c) is not met (Houthi attacks in the Bab el-Mandeb continued in November "
                "2026), so Cape routing is the default.",
                "Persian Gulf: no direct calls at Persian Gulf ports while Hormuz AWRP exceeds 1% of hull value. Middle East customers are "
                "served via Red Sea or Omani ports outside the Gulf where the carrier and broker confirm cover, or by transshipment.",
                "Panama: Asia-US East Coast cargo may use all-water Panama services. If the Panama Canal Authority cuts daily transits below "
                "32, shift up to 40% of East Coast volume to transpacific services with rail intermodal from Los Angeles/Long Beach.",
            ]),
            ("4. Insurance procurement", [
                "All imports are covered under the marine cargo open policy on Institute Cargo Clauses (A) terms, insured at CIF "
                "value plus 10%. War and strikes cover is included worldwide except in JWC listed areas, where cover is held subject to prior "
                "notice and an additional premium.",
                "Procedure for listed-area voyages: (1) the Logistics team checks every port of call and transit against the current JWC "
                "circular (SCI-06); (2) at least 5 business days before cargo loading, the Risk Lead sends the broker the vessel name, routing "
                "and declared value; (3) cargo may not load until the broker confirms cover and the additional premium in writing.",
                "Budget guardrail: if the quoted cargo war premium exceeds 0.5% of cargo value, the shipment needs approval from the VP "
                "Supply Chain; above 1.5% it needs CFO approval, and alternative routing must be evaluated first.",
            ]),
            ("5. Freight procurement", [
                "Contract freight: 70% of annual volume is under 12-month contracts, of which half is index-linked to the Drewry WCI lane "
                "assessments with a quarterly adjustment. 30% is bought on the spot market.",
                "Budget triggers: if the WCI composite moves more than 25% from the budget assumption ($3,800 per FEU for 2026) for four "
                "consecutive weeks, Finance reforecasts landed costs. Peak-season and war-risk surcharges must be reported separately from "
                "base freight in all cost reports.",
                "Fuel: bunker adjustment factors are accepted only when tied to a published bunker index (Singapore VLSFO for Asia-origin services).",
            ]),
            ("6. Supplier and country selection", [
                "New suppliers should be located in countries with a World Bank LPI score of 3.0 or higher (SCI-10). Suppliers in countries "
                "below 3.0 require a dual-source plan and four weeks of additional buffer stock. No more than 40% of any product category may "
                "depend on suppliers whose export route passes through a single chokepoint other than Malacca.",
            ]),
            ("7. Escalation and review", [
                "- Logistics Risk Lead: monitors indicators weekly and publishes the Global Risk Tier every Monday.",
                "- VP Supply Chain: approves routing exceptions, Tier 3 response plans and cargo war premiums above 0.5%.",
                "- CFO: approves cargo war premiums above 1.5% of cargo value and any landed-cost reforecast above $2 million.",
                "- Tier 3 triggers a crisis call within 24 hours, daily status updates, and customer notification for affected orders within 48 hours.",
                "This playbook is reviewed every quarter and after any new JWC listed-area circular.",
            ]),
        ],
    )


DOCS = [doc_chokepoints, doc_hormuz, doc_redsea, doc_panama, doc_insurance, doc_jwc,
        doc_freight, doc_bunker, doc_gscpi, doc_lpi, doc_playbook]


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("SCI-*"):
        old.unlink()
    for fn in DOCS:
        d = fn()
        (build_txt if d["file"].endswith(".txt") else build_pdf)(d)
        print("built", d["file"])


if __name__ == "__main__":
    main()
