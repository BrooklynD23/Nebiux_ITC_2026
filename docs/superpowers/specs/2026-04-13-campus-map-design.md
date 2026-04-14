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
| Multiple buildings | First match wins (v0.1) | Deliberate simplification; future iteration can return a list and show multi-pin view |

---

## Architecture

```
POST /chat
  └── run_tool_loop() → ChatResponse (answer_markdown, citations, ...)
  └── extract_map_data(response.answer_markdown, coords)   ← new, in route handler
        ├── regex: Building \d+ / Bldg \d+
        ├── lookup: data/building_coords.json
        └── returns BuildingLocation | None
  └── response.map_data = result                           ← mutate before return
  └── return response

Frontend
  useChat → owns lastMapData: BuildingLocation | null derived from messages
  useChat return → exposes lastMapData alongside messages, isLoading, error
  App.tsx / parent → passes lastMapData + onCloseMap down to FloatingChatPanel
  FloatingChatPanel → renders <MapPanel> to left of chat when lastMapData is set
  MapPanel → Leaflet map, greyscale tiles, branded pin, aria-live announcement
```

**Note:** `run_tool_loop()` constructs and returns the full `ChatResponse` internally. The route handler calls `extract_map_data` on the returned `response.answer_markdown` and mutates `response.map_data` before returning — no changes to `tool_loop.py`, the retriever, or any LLM prompt.

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

Covers all ~80 numbered CPP campus buildings at launch. Entries with `lat`/`lng` of `0, 0` are treated as invalid and discarded at the frontend guard (see Error Handling).

---

## Backend Changes

### `src/models.py`

Add `BuildingLocation` with coordinate validators, and extend `ChatResponse`:

```python
from pydantic import field_validator

class BuildingLocation(BaseModel):
    building_id: str        # "9"
    label: str              # "Building 9"
    name: str               # "College of Engineering"
    lat: float              # validated: -90 to 90
    lng: float              # validated: -180 to 180
    room: str | None = None # "Room 227" if present in answer

    @field_validator("lat")
    @classmethod
    def valid_lat(cls, v: float) -> float:
        if not -90 <= v <= 90:
            raise ValueError("lat out of range")
        return v

    @field_validator("lng")
    @classmethod
    def valid_lng(cls, v: float) -> float:
        if not -180 <= v <= 180:
            raise ValueError("lng out of range")
        return v

class ChatResponse(BaseModel):
    conversation_id: str
    status: ChatStatus
    answer_markdown: str
    citations: list[Citation]
    debug_info: ChatDebugInfo | None = None
    map_data: BuildingLocation | None = None   # new, defaults to None
```

Malformed `building_coords.json` entries (e.g., `"lat": null`) will fail Pydantic validation inside `extract_map_data` and be caught, returning `None` rather than propagating a 500.

### `src/api/main.py` — lifespan addition

Load `building_coords.json` once at startup, store in `app.state` (mirrors the existing retriever pattern):

```python
# inside the existing lifespan context manager, after retriever init:
coords_path = Path("data/building_coords.json")
if coords_path.exists():
    app.state.building_coords = json.loads(coords_path.read_text())
else:
    logger.warning("building_coords.json not found — map feature disabled")
    app.state.building_coords = {}
```

### `src/api/routes.py`

Add dependency, extraction utility, and post-processing call:

```python
import re, json
from pathlib import Path
from fastapi import Request

_BUILDING_RE = re.compile(r'\b[Bb]uilding\s+(\d+)\b|\b[Bb]ldg\.?\s+(\d+)\b')
_ROOM_RE     = re.compile(r'\b[Rr]oom\s+([\w-]+)\b')

def get_building_coords(request: Request) -> dict:
    return request.app.state.building_coords

def extract_map_data(text: str, coords: dict) -> BuildingLocation | None:
    m = _BUILDING_RE.search(text)
    if not m:
        return None
    building_id = m.group(1) or m.group(2)
    entry = coords.get(building_id)
    if not entry:
        return None
    try:
        room_m = _ROOM_RE.search(text)
        return BuildingLocation(
            building_id=building_id,
            room=room_m.group(1) if room_m else None,
            **entry,
        )
    except Exception:
        return None  # malformed entry in coords file

# In the chat() handler, after run_tool_loop():
async def chat(
    body: ChatRequest,
    coords: dict = Depends(get_building_coords),
    ...
) -> ChatResponse:
    response = await run_tool_loop(...)
    response.map_data = extract_map_data(response.answer_markdown, coords)
    return response
```

---

## Frontend Changes

### New dependency

```
leaflet + @types/leaflet
```

Import `leaflet/dist/leaflet.css` at the top of `MapPanel.tsx` (or in the app's top-level CSS entry point). Without this, tiles and map controls will not render correctly.

### Files modified

| File | Change |
|---|---|
| `frontend/src/types.ts` | Add `BuildingLocation` interface; add `mapData?: BuildingLocation` to `Message` |
| `frontend/src/api/client.ts` | Add `map_data?: BuildingLocation` field to frontend `ChatResponse` type |
| `frontend/src/hooks/useChat.ts` | Attach `mapData` to assistant message; derive and return `lastMapData`; add `onCloseMap` callback |
| `frontend/src/components/FloatingChatPanel.tsx` | Accept `lastMapData` + `onCloseMap` as props; render `<MapPanel>` left of chat when set |
| `frontend/src/api/mock.ts` | Add `map_data` to the location-based mock response so the panel is testable without the backend |

### State and data flow

`lastMapData` is owned by `useChat`. It is derived from the last assistant `Message` where `mapData` is non-null, and updated on every new assistant message. `useChat` returns it alongside `messages`, `isLoading`, and `error`. The parent that renders `FloatingChatPanel` passes it down as a prop, along with an `onCloseMap` callback that clears it.

```
useChat returns: { messages, isLoading, error, lastMapData, onCloseMap, send }
  ↓
App.tsx / parent destructures lastMapData, onCloseMap
  ↓
<FloatingChatPanel lastMapData={lastMapData} onCloseMap={onCloseMap} ...>
  ↓
{lastMapData && <MapPanel building={lastMapData} onClose={onCloseMap} />}
```

### `MapPanel` behaviour

- Imports `leaflet/dist/leaflet.css` at top of file
- Initializes Leaflet with OpenStreetMap tiles; the tile container receives `style="filter: grayscale(1)"` via a CSS class so only tiles are greyscale, not the pin
- Campus bounding box enforced: `map.setMaxBounds(CPP_BOUNDS)`, `minZoom` prevents zooming out past campus
- On `building` prop mount/change: drops a custom SVG pin in brand green (`#0f5f4f`), opens a popup showing `label` + `room`, calls `map.flyTo([lat, lng], zoom, { animate: !prefersReducedMotion })` — animation respects `prefers-reduced-motion`
- Close button calls `onClose` prop

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
- Slide-in animation wrapped in `@media (prefers-reduced-motion: no-preference)`: `translateY(16px) → 0`, `0.28s cubic-bezier(0.22,1,0.36,1)`

---

## Accessibility

- `MapPanel` root: `role="complementary"`, `aria-label="Campus map showing {label}"`
- `aria-live="polite"` region in `FloatingChatPanel` announces `"Map updated: {label}"` on each new `lastMapData` — screen readers receive location without map interaction
- Pin tooltip is keyboard-focusable via a visually-hidden `<button>` at the marker position
- Close button labelled `aria-label="Close map panel"`
- Map tiles degrade gracefully to grey placeholders if tiles fail to load; pin still renders
- `map.flyTo` animation disabled when `window.matchMedia('(prefers-reduced-motion: reduce)').matches`
- Slide-in CSS animation wrapped in `@media (prefers-reduced-motion: no-preference)`

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| `building_coords.json` missing at startup | Warning logged, `coords = {}`, feature silently disabled — chat works normally |
| Malformed coords entry (`lat: null`, out-of-range) | Pydantic validator raises inside `extract_map_data`, caught, returns `None` |
| Building number not in lookup (e.g., "Building 99") | `map_data = None`, no panel shown, no user-facing error |
| Multiple buildings in answer | First regex match wins (v0.1 deliberate simplification) |
| `lat`/`lng` are `0, 0` on frontend | `useChat` checks `mapData.lat !== 0 \|\| mapData.lng !== 0` before setting `lastMapData`; panel does not open |
| Tile network failure | Tiles show as grey placeholders; pin and popup still render |
| Next answer has no building | Panel stays showing last known building; user closes manually |
| Next answer has a different building | `lastMapData` updates, panel flies to new pin |

---

## Testing

### Backend unit tests — `tests/test_building_detection.py` (new file)

- `"...Building 9, Room 227..."` → `BuildingLocation(building_id="9", room="227", ...)`
- `"...Bldg 15..."` → matches abbreviation form
- `"no location here"` → `None`
- `"Building 99"` → unknown building → `None`
- `"...Room 155A..."` → room extracted as `"155A"`
- Malformed coords entry → `None`, no exception raised

### Backend integration tests — `tests/test_api.py` (existing file, add to `TestChatEndpoint`)

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
8. Enable OS reduced-motion setting → slide-in is instant, flyTo is instant
9. With `VITE_USE_MOCK=true`: location mock response shows map panel correctly
