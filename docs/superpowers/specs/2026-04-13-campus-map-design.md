# Campus Map Visualization — Design Spec

**Issue:** #30 — Visualization as output: Map when query returns building locations  
**Date:** 2026-04-13  
**Status:** Approved

---

## Context

When a student asks the Bronco Assistant a location-based question (e.g., "Where is the Engineering Dean's office?"), the current response is plain text. Issue #30 requests a visual map output so students can immediately see *where* the referenced building is on the Cal Poly Pomona campus.

The goal is to add an accessible, lightweight map panel that automatically appears alongside the chat when the assistant's answer contains a building location, highlights that building with a drop-pin marker on a greyscale campus map, and disappears or updates as the conversation continues.

---

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Map placement | Persistent side panel (left of chat modal) | Larger map area, persists across messages, consistent with floating chat pattern |
| Building marker | Drop pin at lat/lng centroid | Simpler data model than GeoJSON polygons; easy to add buildings |
| Map tiles | Leaflet.js + OpenStreetMap, CSS `grayscale(1)` | No API key, Google Maps visual aesthetic, lightweight |
| Detection location | Backend (regex on `answer_markdown`) | Centralized, testable Python; no frontend bundle bloat |
| Campus bounds | CPP bounding box enforced | Users cannot pan outside campus |

---

## Architecture

```
POST /chat
  └── run_tool_loop() → answer_markdown
        └── extract_map_data(answer_markdown, coords)   ← new
              ├── regex: Building \d+ / Bldg \d+
              ├── lookup: data/building_coords.json
              └── returns BuildingLocation | None
  └── ChatResponse { ..., map_data: BuildingLocation | None }   ← extended

Frontend
  useChat → attaches mapData to assistant Message
  FloatingChatPanel → renders <MapPanel> to left of chat when mapData present
  MapPanel → Leaflet map, greyscale tiles, branded pin, aria-live announcement
```

---

## Data Layer

**`data/building_coords.json`**

Static lookup table — one entry per CPP building number. Adding or correcting a building requires only a JSON edit, no code change.

```json
{
  "9":  { "lat": 34.0573, "lng": -117.8213, "name": "College of Engineering", "label": "Building 9" },
  "15": { "lat": 34.0581, "lng": -117.8198, "name": "University Library",     "label": "Building 15" }
}
```

Covers all ~80 numbered CPP campus buildings at launch.

---

## Backend Changes

### `src/models.py`

Add `BuildingLocation` and extend `ChatResponse`:

```python
class BuildingLocation(BaseModel):
    building_id: str        # "9"
    label: str              # "Building 9"
    name: str               # "College of Engineering"
    lat: float
    lng: float
    room: str | None = None # "Room 227" if present in answer

class ChatResponse(BaseModel):
    conversation_id: str
    status: ChatStatus
    answer_markdown: str
    citations: list[Citation]
    debug_info: ChatDebugInfo | None = None
    map_data: BuildingLocation | None = None   # new
```

### `src/api/routes.py`

Add extraction utility and call it after `run_tool_loop()`:

```python
_BUILDING_RE = re.compile(r'\b[Bb]uilding\s+(\d+)\b|\b[Bb]ldg\.?\s+(\d+)\b')
_ROOM_RE     = re.compile(r'\b[Rr]oom\s+([\w-]+)\b')

def extract_map_data(text: str, coords: dict) -> BuildingLocation | None:
    m = _BUILDING_RE.search(text)
    if not m:
        return None
    building_id = m.group(1) or m.group(2)
    entry = coords.get(building_id)
    if not entry:
        return None
    room_m = _ROOM_RE.search(text)
    return BuildingLocation(
        building_id=building_id,
        room=room_m.group(1) if room_m else None,
        **entry,
    )
```

`coords` dict loaded once at app startup via FastAPI lifespan (same pattern as retriever init in `src/api/main.py`), injected as a dependency.

**No changes** to `tool_loop.py`, the retriever, or any LLM prompt.

---

## Frontend Changes

### New dependency

```
leaflet + @types/leaflet
```

### Files modified

| File | Change |
|---|---|
| `frontend/src/types.ts` | Add `BuildingLocation` interface; add `mapData?: BuildingLocation` to `Message` |
| `frontend/src/api/client.ts` | Add `map_data` field to `ChatResponse` type |
| `frontend/src/hooks/useChat.ts` | Attach `mapData: response.map_data ?? undefined` when building assistant message |
| `frontend/src/components/FloatingChatPanel.tsx` | Track `lastMapData` across messages; render `<MapPanel>` to left of chat when present |

### New files

| File | Purpose |
|---|---|
| `frontend/src/components/MapPanel.tsx` | Leaflet map panel component |
| `frontend/src/components/MapPanel.css` | Styles matching existing design system |

### `MapPanel` behaviour

- Initializes Leaflet with OpenStreetMap tiles, `filter: grayscale(1)` applied to the tile layer container
- Campus bounding box enforced: `map.setMaxBounds(CPP_BOUNDS)`, `minZoom` set so users cannot zoom out past campus
- On `building` prop mount/change: drops a custom SVG pin in brand green (`#0f5f4f`), opens tooltip showing `label` + `room`, flies map to pin with smooth animation
- Close button sets `lastMapData` back to `null` in `FloatingChatPanel`, panel unmounts

### Visual spec

Matches existing design system exactly:

- Background: `var(--panel-strong)` (`#fffaf1`)
- Border: `1px solid var(--border)` (`rgba(32,57,49,0.14)`)
- Border-radius: `1.5rem`
- Shadow: `var(--shadow)`
- Fonts: Outfit (header title), Source Sans 3 (footer)
- Brand pin color: `#0f5f4f`
- Building badge: `rgba(15,95,79,0.1)` background, `var(--brand)` text
- Panel width: `26rem`; height: `34rem`
- Slide-in animation: `translateY(16px) → 0`, `0.28s cubic-bezier(0.22,1,0.36,1)`

---

## Accessibility

- `MapPanel` root: `role="complementary"`, `aria-label="Campus map showing {label}"`
- `aria-live="polite"` region in `FloatingChatPanel` announces `"Map updated: {label}"` on each new `mapData` — screen readers receive location without map interaction
- Pin tooltip is keyboard-focusable via a visually-hidden `<button>` at the marker position
- Close button is labelled `aria-label="Close map panel"`
- Map tiles degrade gracefully to grey placeholders if tiles fail to load; pin still renders

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| `building_coords.json` missing at startup | Warning logged, `coords = {}`, feature silently disabled |
| Building number not in lookup (e.g., "Building 99") | `map_data = None`, no panel shown, no user-facing error |
| Multiple buildings in answer | First regex match wins |
| `lat`/`lng` are `0, 0` | `useChat` discards the `mapData`, panel does not open |
| Tile network failure | Tiles show as grey placeholders; pin and tooltip still render |
| Next answer has no building | Panel stays open showing last known building; user closes manually |
| Next answer has a different building | Panel flies smoothly to new pin |

---

## Testing

### Backend unit tests — `tests/test_building_detection.py`

- `"...Building 9, Room 227..."` → `BuildingLocation(building_id="9", room="227", ...)`
- `"...Bldg 15..."` → matches abbreviation form
- `"no location here"` → `None`
- `"Building 99"` → unknown building → `None`
- `"...Room 155A..."` → room extracted as `"155A"`

### Backend integration tests — `tests/test_routes.py`

- POST `/chat` `"Where is the Engineering Dean's office?"` → `response.map_data.building_id == "9"`
- POST `/chat` `"What are the graduation requirements?"` → `response.map_data is None`

### Frontend manual verification

1. Start backend + frontend (`uvicorn src.api.main:app --reload` + `cd frontend && npm run dev`)
2. Ask `"Where is the library?"` → map panel slides in left of chat, pin on Building 15
3. Ask question referencing a different building → panel flies to new pin
4. Ask a non-location question → panel stays with last pin, no crash
5. Close map panel → chat returns to normal width
6. DevTools: no console errors; confirm `aria-live` region fires on each location response
7. Keyboard-only navigation: tab to pin tooltip, confirm readable; tab to close button, confirm dismissal works
