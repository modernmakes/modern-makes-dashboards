window.CONTENT_TRACKER = {
  "generated_at": "2026-07-28",
  "source": "Content Tracker.md + Strategy.md",
  "stats": [
    { "key": "idea", "label": "Idea", "count": 15 },
    { "key": "backlog", "label": "Backlog", "count": 4 },
    { "key": "drafted", "label": "Drafted", "count": 1 },
    { "key": "verify", "label": "Verify", "count": 1 },
    { "key": "published", "label": "Published", "count": 2 },
    { "key": "killed", "label": "Killed", "count": 1 }
  ],
  "board": {
    "idea": [
      { "title": "Desktop Metal Printer Buying Guide (Scrap One)", "pillar": "Hardware / Gear" },
      { "title": "Self-Hosting Bambu Print Cloud (Bambuddy)", "pillar": "Tuning Lab" },
      { "title": "Voron Toolhead Landscape", "pillar": "The Build" },
      { "title": "StealthChanger vs. FlashForge", "pillar": "The Build" },
      { "title": "Micro-Nozzle Printing Limits", "pillar": "Tuning Lab" },
      { "title": "OrcaSlicer Setup Guide", "pillar": "Tuning Lab" },
      { "title": "A Short History of Desktop FDM", "pillar": "State of the Layer" },
      { "title": "CoreXY vs Cartesian vs Delta", "pillar": "Hardware / Gear" },
      { "title": "Hotend Anatomy 101", "pillar": "Hardware / Gear" },
      { "title": "Slicing Settings That Matter", "pillar": "Tuning Lab" },
      { "title": "Filament Materials Baseline", "pillar": "Hardware / Gear" },
      { "title": "VzBot AWD CoreXY Explained", "pillar": "The Build" },
      { "title": "HevORT Triple-Z Self-Leveling", "pillar": "The Build" },
      { "title": "Inside the Voron Community Model", "pillar": "Community Spotlight" },
      { "title": "Prosumer FDM Market 2026", "pillar": "State of the Layer" }
    ],
    "backlog": [
      { "title": "RatRig Pre-Assembled Kit Coverage", "pillar": "The Build" },
      { "title": "Bambu neXt", "pillar": "State of the Layer" },
      { "title": "Prusa HT Hotend", "pillar": "Hardware / Gear" },
      { "title": "AtomForm Palette 300", "pillar": "Hardware / Gear" }
    ],
    "drafted": [
      {
        "title": "Force-Based PA Calibration Roundup",
        "pillar": "Tuning Lab",
        "note": "2 individual hardware drafts exist — no combined roundup yet"
      }
    ],
    "verify": [
      {
        "title": "Self-Build CoreXY Landscape (Voron/RatRig/VzBot/HevORT)",
        "pillar": "The Build",
        "note": "Cornerstone piece — confirm live status before drafting"
      }
    ],
    "published": [
      { "title": "Voron Phoenix Dev Status (corrected)", "pillar": "The Build" },
      { "title": "News Accuracy Audit (6 articles)", "pillar": "State of the Layer" }
    ],
    "killed": [
      {
        "title": "Bambu AGPLv3 Investigation",
        "pillar": "State of the Layer",
        "note": "Deleted 2026-07-28 — stale. Check site repo for a live copy."
      }
    ]
  },
  "pillar_coverage": [
    { "name": "The Build", "count": 7, "pct": 100 },
    { "name": "Hardware / Gear", "count": 6, "pct": 85 },
    { "name": "Tuning Lab", "count": 5, "pct": 71 },
    { "name": "State of the Layer", "count": 4, "pct": 57 },
    { "name": "Community Spotlight", "count": 1, "pct": 14 }
  ],
  "strategy": {
    "pillars": [
      {
        "name": "The Build",
        "description": "Self-build CoreXY from first bolt to first print — Voron, RatRig, VzBot, HevORT.",
        "why": "Highest affiliate value — BOM $800–2,000"
      },
      {
        "name": "Hardware / Gear",
        "description": "Prosumer hotends, extruders, toolheads, probes, boards — fed by the Hardware DB.",
        "why": "Direct affiliate intent"
      },
      {
        "name": "Tuning Lab",
        "description": "Calibration, slicer settings, materials, benchmarks. Data-driven, verdict-first.",
        "why": "High affiliate intent, strong evergreen search"
      },
      {
        "name": "Community Spotlight",
        "description": "Best mods, print farms, build logs curated from Reddit/Printables/Discord.",
        "why": "Audience growth + goodwill"
      },
      {
        "name": "State of the Layer",
        "description": "Recurring roundup of what shipped / what's coming in the self-build ecosystem.",
        "why": "Newsletter growth driver"
      }
    ],
    "open_decisions": [
      "Final logo mark (dark-first, works at 16px favicon)",
      "Custom domain vs. modernmakes.github.io",
      "Newsletter growth cadence / lead magnet on Beehiiv",
      "Which build series anchors next quarter (Voron / RatRig / VzBot / HevORT)"
    ],
    "systems_of_record": [
      { "tag": "live", "label": "Hardware DB (Airtable) — feeds site build nightly" },
      { "tag": "live", "label": "Content Tracker.md — pipeline status (this dashboard's source)" },
      { "tag": "mothballed", "label": "Editorial DB (Airtable) — unused since creation, revisit once articles generate real SEO/revenue data" }
    ]
  }
}
;
