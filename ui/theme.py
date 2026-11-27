"""Visual language: "white city in fog".

Two references, used as mood only (no logos, characters or artwork copied):

* Mirror's Edge (2008) concept art - near-white architecture, controlled palette,
  cool blue shadows, ONE saturated red used as a wayfinding signal ("runner
  vision"), hard geometry, big confident type.
* Purelink album covers - hazy, silvery, glassy, soft-focus atmosphere, mist,
  grain and quiet negative space.

Design rules applied throughout:
- Off-white base, cool grey-blue shadows, ink for text. Red is reserved for the
  path: citations, the active state, the route line. Never decorative fills.
- Zero border radius; chamfered corners via clip-path; hairline 1px rules.
- Haze: large blurred radial gradients + film grain behind frosted panels.
- Type: Barlow Condensed (display, DIN-like), Barlow (text), Martian Mono (data).
"""

PALETTE = {
    "paper": "#F3F4F2",
    "white": "#FBFBFA",
    "fog": "#E3E8EA",
    "shadow": "#C3CFD6",
    "steel": "#7D93A0",
    "slate": "#4E6270",
    "ink": "#15191C",
    "red": "#E2231A",
    "red_soft": "rgba(226,35,26,.08)",
}

# Film grain as an inline SVG (feTurbulence) - no external assets needed.
_GRAIN = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='220' height='220'>"
          "<filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3' stitchTiles='stitch'/>"
          "<feColorMatrix values='0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 .55 0'/></filter>"
          "<rect width='100%25' height='100%25' filter='url(%23n)'/></svg>")

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@300;500;600;700&family=Barlow:wght@300;400;500;600&family=Martian+Mono:wght@300;400;500&display=swap');

:root {{
  --paper:{PALETTE['paper']}; --white:{PALETTE['white']}; --fog:{PALETTE['fog']};
  --shadow:{PALETTE['shadow']}; --steel:{PALETTE['steel']}; --slate:{PALETTE['slate']};
  --ink:{PALETTE['ink']}; --red:{PALETTE['red']}; --red-soft:{PALETTE['red_soft']};
  --display:'Barlow Condensed', 'Arial Narrow', sans-serif;
  --text:'Barlow', 'Helvetica Neue', Arial, sans-serif;
  --mono:'Martian Mono', ui-monospace, 'SFMono-Regular', Menlo, monospace;
  --chamfer: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 14px 100%, 0 calc(100% - 14px));
}}

/* ---------- canvas: fog + grain ---------- */
html, body, [data-testid="stAppViewContainer"], .stApp {{
  background: var(--paper) !important; color: var(--ink); font-family: var(--text);
}}
[data-testid="stAppViewContainer"]::before {{
  content:""; position:fixed; inset:-20%; z-index:0; pointer-events:none;
  background:
    radial-gradient(38% 30% at 82% 8%, rgba(190,214,226,.55), transparent 70%),
    radial-gradient(30% 26% at 6% 42%, rgba(214,222,228,.70), transparent 72%),
    radial-gradient(36% 30% at 70% 88%, rgba(203,220,230,.45), transparent 70%),
    radial-gradient(22% 18% at 40% 60%, rgba(255,255,255,.65), transparent 70%);
  filter: blur(20px);
}}
[data-testid="stAppViewContainer"]::after {{
  content:""; position:fixed; inset:0; z-index:0; pointer-events:none;
  background-image:url("{_GRAIN}"); opacity:.07; mix-blend-mode:multiply;
}}
[data-testid="stMain"], [data-testid="stSidebar"] > div {{ position:relative; z-index:1; }}
[data-testid="stHeader"] {{ background: transparent !important; }}
[data-testid="stToolbar"] {{ right: 1rem; }}
.block-container {{ max-width: 1120px !important; padding-top: 2.2rem !important; padding-bottom: 7rem !important; }}

h1,h2,h3,h4 {{ font-family: var(--display) !important; color: var(--ink); letter-spacing:.02em; }}
p, li, label, .stMarkdown {{ font-family: var(--text); color: var(--ink); }}
a {{ color: var(--ink) !important; text-decoration-color: var(--red) !important; }}
::selection {{ background: var(--red); color: white; }}

/* ---------- hero ---------- */
.cp-hero {{ position:relative; height: 300px; overflow:hidden; clip-path: var(--chamfer);
  border:1px solid rgba(21,25,28,.12); background: var(--white); }}
.cp-hero svg {{ position:absolute; inset:0; width:100%; height:100%; }}
.cp-hero-copy {{ position:absolute; left:34px; bottom:26px; right:34px; }}
.cp-kicker {{ font-family: var(--mono); font-size:10.5px; letter-spacing:.18em; text-transform:uppercase; color: var(--slate); }}
.cp-kicker b {{ color: var(--red); font-weight:500; }}
.cp-title {{ font-family: var(--display); font-weight:700; font-size: 92px; line-height:.86; letter-spacing:.015em;
  color: var(--ink); margin: 8px 0 10px; text-transform: uppercase; }}
.cp-title span {{ color: transparent; -webkit-text-stroke: 1.4px var(--ink); }}
.cp-lede {{ font-family: var(--text); font-weight:400; font-size:16px; max-width: 560px; color: var(--slate); line-height:1.45; }}

.cp-spec {{ display:grid; grid-template-columns: 1.25fr 1fr 1fr 1fr; border:1px solid rgba(21,25,28,.12); border-top:none;
  background: rgba(251,251,250,.62); backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px); }}
.cp-spec > div {{ padding: 14px 18px 16px; border-left:1px solid rgba(21,25,28,.09); }}
.cp-spec > div:first-child {{ border-left:none; }}
.cp-spec .k {{ font-family: var(--mono); font-size:9.5px; letter-spacing:.16em; text-transform:uppercase; color: var(--steel); }}
.cp-spec .v {{ font-family: var(--text); font-size:13.5px; line-height:1.4; margin-top:6px; color: var(--ink); }}

/* compact header once the conversation has started */
.cp-bar {{ display:flex; align-items:baseline; justify-content:space-between; gap:16px; flex-wrap:wrap;
  padding: 0 0 12px; border-bottom: 1px solid rgba(21,25,28,.14); }}
.cp-bar .cp-title {{ font-size: 40px; margin: 0; }}
.cp-bar .cp-kicker {{ font-size: 9.5px; }}

/* ---------- section labels ---------- */
.cp-label {{ display:flex; align-items:center; gap:12px; margin: 30px 0 12px; font-family: var(--mono);
  font-size:10.5px; letter-spacing:.2em; text-transform:uppercase; color: var(--slate); }}
.cp-label::after {{ content:""; flex:1; height:1px; background: linear-gradient(90deg, rgba(21,25,28,.25), transparent); }}
.cp-label i {{ width:18px; height:2px; background: var(--red); display:inline-block; }}

/* ---------- starter tiles (st.button) ---------- */
div[data-testid="stButton"] > button {{
  width:100%; min-height: 96px; text-align:left; justify-content:flex-start; align-items:flex-start;
  border-radius:0 !important; border:1px solid rgba(21,25,28,.14) !important;
  background: rgba(251,251,250,.66) !important; backdrop-filter: blur(10px);
  color: var(--ink) !important; padding: 12px 14px !important; transition: all .18s ease;
  clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%);
}}
div[data-testid="stButton"] > button p {{ font-family: var(--text) !important; font-size: 14px !important; line-height:1.35; text-align:left;
  white-space: normal !important; overflow: visible !important; text-overflow: clip !important; }}
div[data-testid="stButton"] > button div, div[data-testid="stButton"] > button span {{ white-space: normal !important; overflow: visible !important;
  text-overflow: clip !important; max-width:100%; }}
div[data-testid="stButton"] > button:hover {{ border-color: var(--ink) !important; background: var(--white) !important;
  box-shadow: inset 3px 0 0 var(--red); }}
div[data-testid="stButton"] > button:focus:not(:active) {{ border-color: var(--ink) !important; }}
.cp-tile-idx {{ font-family: var(--mono); font-size:10px; letter-spacing:.16em; color: var(--steel); margin: 0 0 -6px 2px; }}
.cp-tile-idx b {{ color: var(--red); font-weight:500; }}

/* ---------- chat ---------- */
[data-testid="stChatMessage"] {{ background: transparent !important; padding: 0 !important; gap: 0 !important; margin: 18px 0 !important; }}
[data-testid="stChatMessageAvatarUser"], [data-testid="stChatMessageAvatarAssistant"],
[data-testid="stChatMessage"] img, [data-testid="chatAvatarIcon-user"], [data-testid="chatAvatarIcon-assistant"] {{ display:none !important; }}
[data-testid="stChatMessageContent"] {{ width:100%; margin:0 !important; padding:0 !important; }}

.cp-msg-head {{ display:flex; justify-content:space-between; align-items:baseline; font-family: var(--mono); font-size:10px;
  letter-spacing:.18em; text-transform:uppercase; color: var(--steel); margin-bottom:8px; }}
.cp-msg-head b {{ color: var(--ink); font-weight:500; }}
.cp-q {{ font-family: var(--display); font-weight:500; font-size: 27px; line-height:1.12; color: var(--ink);
  padding: 4px 0 6px 18px; border-left: 2px solid var(--ink); letter-spacing:.005em; }}

.cp-a {{ position:relative; background: rgba(251,251,250,.78); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
  border:1px solid rgba(21,25,28,.11); padding: 20px 24px 18px 26px; clip-path: var(--chamfer); }}
.cp-a::before {{ content:""; position:absolute; left:0; top:0; bottom:0; width:3px; background: var(--red); }}
.cp-a.fallback::before {{ background: var(--steel); }}
.cp-a.error::before {{ background: repeating-linear-gradient(180deg, var(--red) 0 6px, transparent 6px 10px); }}
.cp-a-body, .cp-a-body p, .cp-a-body li {{ font-size: 15.5px; line-height:1.62; color: var(--ink); }}
.cp-a-body ul {{ margin: 6px 0 4px 2px; padding-left: 18px; }}
.cp-a-body li::marker {{ color: var(--red); }}
.cp-a-body strong {{ font-weight:600; }}
.cp-cite {{ display:inline-block; font-family: var(--mono); font-size: 9.5px; letter-spacing:.06em; line-height:1;
  padding: 3px 5px 2px; margin: 0 1px 0 3px; vertical-align: 2px; color: var(--red); border:1px solid rgba(226,35,26,.45);
  background: var(--red-soft); white-space:nowrap; cursor:help; }}
.cp-a-foot {{ display:flex; gap:18px; flex-wrap:wrap; margin-top:14px; padding-top:10px; border-top:1px dashed rgba(21,25,28,.15);
  font-family: var(--mono); font-size:9.5px; letter-spacing:.12em; text-transform:uppercase; color: var(--steel); }}
.cp-a-foot b {{ color: var(--ink); font-weight:500; }}
.cp-srcline {{ font-family: var(--mono); font-size: 10.5px; color: var(--slate); margin-top:8px; line-height:1.7; }}
.cp-srcline span {{ color: var(--red); }}

/* ---------- source viewer ---------- */
[data-testid="stExpander"] {{ border:none !important; margin-top: 6px; }}
[data-testid="stExpander"] details {{ border-radius:0 !important; border:1px solid rgba(21,25,28,.12) !important;
  background: rgba(243,244,242,.7) !important; }}
[data-testid="stExpander"] summary {{ font-family: var(--mono) !important; }}
[data-testid="stExpander"] summary p {{ font-family: var(--mono) !important; font-size: 10.5px !important; letter-spacing:.16em;
  text-transform: uppercase; color: var(--slate) !important; }}
[data-testid="stExpander"] summary:hover p {{ color: var(--red) !important; }}
.cp-src {{ display:grid; grid-template-columns: 92px 1fr; gap: 0; border:1px solid rgba(21,25,28,.1); background: var(--white); margin-bottom:10px; }}
.cp-src-code {{ padding: 12px 10px; border-right:1px solid rgba(21,25,28,.1); background:
  linear-gradient(160deg, rgba(227,232,234,.9), rgba(251,251,250,.4)); }}
.cp-src-code .c {{ font-family: var(--display); font-weight:700; font-size: 26px; line-height:1; color: var(--ink); }}
.cp-src-code .s {{ font-family: var(--mono); font-size:9px; letter-spacing:.14em; color: var(--steel); margin-top:6px; }}
.cp-src-main {{ padding: 12px 16px 14px; }}
.cp-src-title {{ font-family: var(--text); font-weight:600; font-size: 14px; color: var(--ink); }}
.cp-src-meta {{ font-family: var(--mono); font-size: 9.5px; letter-spacing:.08em; color: var(--steel); margin: 4px 0 8px; text-transform:uppercase; }}
.cp-src-text {{ font-size: 13px; line-height:1.55; color: #3a464e; white-space: pre-wrap; border-left: 1px solid var(--shadow); padding-left:12px; }}
.cp-meter {{ display:flex; align-items:center; gap:10px; margin-top:10px; font-family: var(--mono); font-size:9.5px; letter-spacing:.1em; color: var(--slate); text-transform:uppercase; }}
.cp-meter .bar {{ flex: 0 0 150px; height:4px; background: var(--fog); position:relative; }}
.cp-meter .bar i {{ position:absolute; left:0; top:0; bottom:0; background: var(--ink); }}
.cp-meter .tier-strong {{ color: var(--red); }} .cp-meter .tier-potential {{ color: var(--ink); }}
.cp-meter .tier-weak {{ color: var(--steel); }} .cp-meter .tier-irrelevant {{ color: #a7b3ba; text-decoration: line-through; }}
.cp-table {{ width:100%; border-collapse: collapse; font-family: var(--mono); font-size: 10.5px; }}
.cp-table th {{ text-align:left; font-weight:500; letter-spacing:.12em; text-transform:uppercase; color: var(--steel); padding:6px 8px; border-bottom:1px solid rgba(21,25,28,.2); }}
.cp-table td {{ padding:6px 8px; border-bottom:1px solid rgba(21,25,28,.07); color: var(--ink); }}
.cp-table tr.rej td {{ color:#9aa7ae; }}

/* tabs inside the source viewer */
[data-testid="stTabs"] button p {{ font-family: var(--mono) !important; font-size:10px !important; letter-spacing:.14em; text-transform:uppercase; }}
[data-baseweb="tab-highlight"] {{ background: var(--red) !important; height:2px !important; }}
[data-baseweb="tab-border"] {{ background: rgba(21,25,28,.12) !important; }}

/* ---------- chat input ---------- */
[data-testid="stBottom"] > div, [data-testid="stBottomBlockContainer"] {{ background: transparent !important; }}
[data-testid="stBottom"] {{ background: var(--paper) !important; border-top: 1px solid rgba(21,25,28,.1); }}
[data-testid="stBottomBlockContainer"] {{ max-width: 1120px !important; padding-top: 14px !important; padding-bottom: 18px !important; }}
[data-testid="stChatInput"] {{ border-radius:0 !important; border: 1px solid var(--ink) !important; background: var(--white) !important; }}
[data-testid="stChatInput"] > div {{ border-radius:0 !important; background: transparent !important; border:none !important; }}
[data-testid="stChatInput"] textarea {{ font-family: var(--text) !important; font-size: 15.5px !important; color: var(--ink) !important; }}
[data-testid="stChatInput"] textarea::placeholder {{ color: var(--steel) !important; }}
[data-testid="stChatInputSubmitButton"] {{ border-radius:0 !important; background: var(--red) !important; color:white !important; }}
[data-testid="stChatInputSubmitButton"]:disabled {{ background: var(--shadow) !important; }}

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {{ background: rgba(236,239,239,.92) !important; border-right: 1px solid rgba(21,25,28,.1); }}
.cp-side-mark {{ font-family: var(--display); font-weight:700; font-size: 30px; letter-spacing:.04em; line-height:1; color: var(--ink); }}
.cp-side-mark i {{ display:inline-block; width:22px; height:3px; background: var(--red); margin: 0 0 6px 8px; transform: skewX(-30deg); }}
.cp-side-sub {{ font-family: var(--mono); font-size:9.5px; letter-spacing:.18em; color: var(--steel); text-transform:uppercase; margin-top:6px; }}
.cp-stat {{ display:grid; grid-template-columns: repeat(3, 1fr); border:1px solid rgba(21,25,28,.12); margin: 16px 0 6px; background: rgba(251,251,250,.7); }}
.cp-stat > div {{ padding: 10px 10px 9px; border-left:1px solid rgba(21,25,28,.1); }}
.cp-stat > div:first-child {{ border-left:none; }}
.cp-stat .n {{ font-family: var(--display); font-weight:600; font-size: 26px; line-height:1; color: var(--ink); }}
.cp-stat .l {{ font-family: var(--mono); font-size: 8.5px; letter-spacing:.14em; color: var(--steel); text-transform:uppercase; margin-top:4px; }}
.cp-state {{ font-family: var(--mono); font-size:9.5px; letter-spacing:.1em; color: var(--slate); text-transform:uppercase; }}
.cp-state .dot {{ display:inline-block; width:7px; height:7px; background: var(--red); margin-right:6px; vertical-align:1px; }}
.cp-doc {{ display:grid; grid-template-columns: 54px 1fr; gap: 8px; padding: 8px 0; border-bottom:1px solid rgba(21,25,28,.08); }}
.cp-doc .c {{ font-family: var(--mono); font-size: 10px; color: var(--red); letter-spacing:.04em; padding-top:2px; }}
.cp-doc .t {{ font-size: 12.5px; line-height:1.3; color: var(--ink); }}
.cp-doc .f {{ font-family: var(--mono); font-size: 8.5px; color: var(--steel); letter-spacing:.06em; margin-top:2px; text-transform:uppercase; }}
[data-testid="stSidebar"] div[data-testid="stButton"] > button {{ min-height: 40px; clip-path:none; justify-content:center; align-items:center;
  background: var(--ink) !important; color: var(--white) !important; border-color: var(--ink) !important; }}
[data-testid="stSidebar"] div[data-testid="stButton"] > button p {{ font-family: var(--mono) !important; font-size: 10.5px !important; letter-spacing:.18em; text-transform:uppercase; color: var(--white) !important; }}
[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {{ background: var(--red) !important; border-color: var(--red) !important; box-shadow:none; }}
[data-testid="stSlider"] [role="slider"] {{ background: var(--ink) !important; border-radius:0 !important; box-shadow:none !important; }}
[data-testid="stSlider"] [data-testid="stThumbValue"] {{ font-family: var(--mono); color: var(--ink) !important; }}

/* ---------- status / alerts ---------- */
[data-testid="stStatusWidget"], [data-testid="stAlert"], [data-testid="stExpander"] details[open] {{ border-radius:0 !important; }}
[data-testid="stAlert"] {{ border-radius:0 !important; }}
.cp-notice {{ border:1px solid rgba(21,25,28,.14); background: rgba(251,251,250,.82); backdrop-filter: blur(12px);
  padding: 18px 22px; margin-top: 18px; clip-path: var(--chamfer); position:relative; }}
.cp-notice::before {{ content:""; position:absolute; left:0; top:0; bottom:0; width:3px; background: var(--red); }}
.cp-notice h4 {{ margin:0 0 6px !important; font-size: 22px !important; text-transform: uppercase; }}
.cp-notice p, .cp-notice li {{ font-size: 14px; color: var(--slate); }}
.cp-notice code {{ font-family: var(--mono); font-size: 12px; background: var(--fog); padding: 1px 5px; border-radius:0; color: var(--ink); }}
.cp-foot {{ margin-top: 42px; font-family: var(--mono); font-size: 9.5px; letter-spacing:.14em; color: var(--steel); text-transform:uppercase; }}
@media (max-width: 1100px) {{
  .cp-spec {{ grid-template-columns: 1fr 1fr; }}
  .cp-spec > div:nth-child(3) {{ border-left:none; }}
  .cp-spec > div:nth-child(n+3) {{ border-top:1px solid rgba(21,25,28,.09); }}
}}
@media (max-width: 760px) {{
  .cp-title {{ font-size: 58px; }} .cp-hero {{ height: 260px; }}
}}
</style>
"""


def hero_svg() -> str:
    """Original illustration: white rooftops/container-stacks in fog, cool blue
    shadows, one red route line ("runner vision") running across the roofs."""
    def block(x, y, w, d, h, top="#FBFBFA", left="#E6EBEE", right="#C9D5DC"):
        # simple oblique projection: depth goes up-right
        dx, dy = d * 0.62, -d * 0.36
        return (f'<polygon points="{x},{y} {x+w},{y} {x+w+dx},{y+dy} {x+dx},{y+dy}" fill="{top}"/>'
                f'<polygon points="{x},{y} {x+w},{y} {x+w},{y+h} {x},{y+h}" fill="{left}"/>'
                f'<polygon points="{x+w},{y} {x+w+dx},{y+dy} {x+w+dx},{y+dy+h} {x+w},{y+h}" fill="{right}"/>')

    blocks = "".join([
        block(470, 168, 120, 70, 200), block(600, 120, 90, 60, 260, right="#BFCCD4"),
        block(700, 150, 150, 80, 230), block(862, 96, 70, 50, 300, right="#B8C7D0"),
        block(940, 138, 170, 90, 240), block(1118, 172, 90, 60, 200),
        block(540, 228, 90, 40, 130, left="#EDF1F2"), block(760, 214, 110, 46, 140, left="#EEF1F2"),
    ])
    # thin container-like stripes on two facades
    stripes = "".join(f'<line x1="{700}" y1="{170+i*14}" x2="{850}" y2="{170+i*14}" stroke="#D7DFE3" stroke-width="1"/>'
                      for i in range(9))
    stripes += "".join(f'<line x1="{x}" y1="138" x2="{x}" y2="378" stroke="#DCE3E6" stroke-width="1"/>' for x in range(952, 1110, 16))
    route = ("M 470 168 L 589 168 L 626 147 L 690 120 L 727 120 L 762 103 L 850 103 "
             "L 880 85 L 932 85 L 963 96 L 1110 96 L 1150 80 L 1240 80")
    return f"""
<svg viewBox="0 0 1200 300" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#EAF0F2"/><stop offset=".7" stop-color="#F7F8F7"/><stop offset="1" stop-color="#FBFBFA"/>
    </linearGradient>
    <filter id="haze" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="38"/></filter>
    <filter id="soft"><feGaussianBlur stdDeviation="1.1"/></filter>
    <filter id="glow" x="-10%" y="-50%" width="120%" height="200%"><feGaussianBlur stdDeviation="3"/></filter>
    <linearGradient id="fadeL" x1="0" x2="1"><stop offset="0" stop-color="#FBFBFA"/><stop offset=".48" stop-color="#FBFBFA" stop-opacity=".92"/><stop offset=".62" stop-color="#FBFBFA" stop-opacity="0"/></linearGradient>
  </defs>
  <rect width="1200" height="300" fill="url(#sky)"/>
  <ellipse cx="980" cy="40" rx="260" ry="90" fill="#CFE0E8" filter="url(#haze)" opacity=".9"/>
  <ellipse cx="640" cy="250" rx="280" ry="70" fill="#FFFFFF" filter="url(#haze)"/>
  <g filter="url(#soft)" opacity=".38" transform="translate(-60,-30) scale(1.08)">{block(820,150,60,40,260,"#F4F6F6","#E3E9EC","#D3DDE2")}{block(1040,120,80,50,280,"#F4F6F6","#E3E9EC","#D3DDE2")}</g>
  <g>{blocks}{stripes}</g>
  <path d="{route}" fill="none" stroke="#E2231A" stroke-width="5" opacity=".35" filter="url(#glow)"/>
  <path d="{route}" fill="none" stroke="#E2231A" stroke-width="2.4" stroke-linejoin="miter"/>
  <g fill="#E2231A"><rect x="586" y="164" width="7" height="7"/><rect x="846" y="99" width="7" height="7"/><rect x="1106" y="92" width="7" height="7"/></g>
  <g font-family="Martian Mono, monospace" font-size="8.5" letter-spacing="1.6" fill="#7D93A0">
    <text x="598" y="186">HORMUZ  -96%</text><text x="858" y="121">BAB EL-MANDEB  -31%</text><text x="1050" y="114">CAPE  +40% TKR</text>
  </g>
  <rect width="1200" height="300" fill="url(#fadeL)"/>
  <ellipse cx="300" cy="300" rx="420" ry="60" fill="#FFFFFF" filter="url(#haze)" opacity=".85"/>
</svg>"""
