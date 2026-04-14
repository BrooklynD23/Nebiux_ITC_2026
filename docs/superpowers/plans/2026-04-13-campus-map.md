# Campus Map Visualization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When the Bronco Assistant answers a question that references a CPP building, a persistent side panel slides in to the left of the chat modal showing a greyscale campus map with a drop-pin marker on that building.

**Architecture:** Backend regex-scans `answer_markdown` after `run_tool_loop()` returns, looks up the building number in a static JSON file, and attaches a `BuildingLocation` to `ChatResponse.map_data`. The frontend's `useChat` hook derives `lastMapData` from messages and exposes it alongside an `onCloseMap` callback. `App.tsx` passes both to `FloatingChatPanel`, which conditionally renders a new `MapPanel` (Leaflet + OSM tiles, CSS greyscale) to the left of the chat modal.

**Tech Stack:** Python/FastAPI (backend), Pydantic v2, pytest, React 18/TypeScript (frontend), Leaflet.js, Vite

**Spec:** `docs/superpowers/specs/2026-04-13-campus-map-design.md`

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `data/building_coords.json` | Static lat/lng lookup per CPP building number |
| Modify | `src/models.py` | Add `BuildingLocation` model; add `map_data` to `ChatResponse` |
| Create | `src/api/building_coords.py` | `extract_map_data()` utility + `get_building_coords` dependency |
| Modify | `src/api/main.py` | Load `building_coords.json` into `app.state` during lifespan |
| Modify | `src/api/routes.py` | Call extraction after `run_tool_loop()`; add `coords` dependency |
| Create | `tests/test_building_detection.py` | Unit tests for extraction utility |
| Modify | `tests/test_api.py` | Integration tests — `map_data` presence/absence in chat responses |
| Modify | `frontend/src/types.ts` | Add `BuildingLocation`; extend `Message` and `ChatResponse` |
| Modify | `frontend/src/hooks/useChat.ts` | Derive `lastMapData`; add `onCloseMap`; extend return type |
| Modify | `frontend/src/api/mock.ts` | Add `LOCATION_RESPONSE` with `map_data` for location queries |
| Create | `frontend/src/components/MapPanel.tsx` | Leaflet map panel component |
| Create | `frontend/src/components/MapPanel.css` | Panel styles matching design system |
| Modify | `frontend/src/components/FloatingChatPanel.tsx` | Accept `lastMapData`/`onCloseMap`; render `<MapPanel>` |
| Modify | `frontend/src/App.tsx` | Wire `lastMapData`/`onCloseMap` from `useChat`; add `aria-live` region |

---

## Task 1: Building Coordinates Data File

**Files:**
- Create: `data/building_coords.json`

The lat/lng values below are the approximate centroids of each CPP building. Verify against Google Maps satellite view before shipping — these seed values are close but should be confirmed.

- [ ] **Step 1: Create the file**

```json
{
  "2":   { "lat": 34.0578, "lng": -117.8225, "name": "Administration",               "label": "Building 2" },
  "3":   { "lat": 34.0582, "lng": -117.8219, "name": "Student Services",             "label": "Building 3" },
  "4":   { "lat": 34.0585, "lng": -117.8212, "name": "Social Sciences",              "label": "Building 4" },
  "5":   { "lat": 34.0590, "lng": -117.8205, "name": "Science",                      "label": "Building 5" },
  "6":   { "lat": 34.0575, "lng": -117.8208, "name": "Kinesiology",                  "label": "Building 6" },
  "7":   { "lat": 34.0580, "lng": -117.8200, "name": "Business Administration",      "label": "Building 7" },
  "8":   { "lat": 34.0568, "lng": -117.8215, "name": "Agricultural Sciences",        "label": "Building 8" },
  "9":   { "lat": 34.0573, "lng": -117.8213, "name": "College of Engineering",       "label": "Building 9" },
  "10":  { "lat": 34.0565, "lng": -117.8207, "name": "Mechanical Engineering",       "label": "Building 10" },
  "13":  { "lat": 34.0561, "lng": -117.8220, "name": "Civil Engineering",            "label": "Building 13" },
  "15":  { "lat": 34.0581, "lng": -117.8198, "name": "University Library",           "label": "Building 15" },
  "16":  { "lat": 34.0592, "lng": -117.8218, "name": "Chemistry",                    "label": "Building 16" },
  "17":  { "lat": 34.0596, "lng": -117.8210, "name": "Education",                    "label": "Building 17" },
  "24":  { "lat": 34.0554, "lng": -117.8230, "name": "Student Union",                "label": "Building 24" },
  "26":  { "lat": 34.0560, "lng": -117.8235, "name": "Recreation Center",            "label": "Building 26" },
  "35":  { "lat": 34.0545, "lng": -117.8215, "name": "Dining Hall",                  "label": "Building 35" },
  "121": { "lat": 34.0570, "lng": -117.8195, "name": "College of Business",          "label": "Building 121" },
  "164": { "lat": 34.0588, "lng": -117.8228, "name": "Environmental Design",         "label": "Building 164" }
}
```

Save to `data/building_coords.json`. This is a seed — expand to all ~80 CPP buildings by cross-referencing the campus map at cpp.edu/map and the cleaned corpus files in `data/cleaned/`.

- [ ] **Step 2: Commit**

```bash
git add data/building_coords.json
git commit -m "feat: add CPP building coordinates lookup table"
```

---

## Task 2: Backend Models

**Files:**
- Modify: `src/models.py`
- Create: `tests/test_building_detection.py` (scaffold only — full tests in Task 3)

- [ ] **Step 1: Write the failing model test**

Create `tests/test_building_detection.py`:

```python
"""Unit tests for BuildingLocation model validation."""
from __future__ import annotations
import pytest
from pydantic import ValidationError
from src.models import BuildingLocation


def test_building_location_valid() -> None:
    loc = BuildingLocation(
        building_id="9",
        label="Building 9",
        name="College of Engineering",
        lat=34.0573,
        lng=-117.8213,
    )
    assert loc.building_id == "9"
    assert loc.room is None


def test_building_location_with_room() -> None:
    loc = BuildingLocation(
        building_id="9",
        label="Building 9",
        name="College of Engineering",
        lat=34.0573,
        lng=-117.8213,
        room="227",
    )
    assert loc.room == "227"


def test_building_location_invalid_lat() -> None:
    with pytest.raises(ValidationError):
        BuildingLocation(
            building_id="x",
            label="X",
            name="X",
            lat=999.0,
            lng=-117.0,
        )


def test_building_location_invalid_lng() -> None:
    with pytest.raises(ValidationError):
        BuildingLocation(
            building_id="x",
            label="X",
            name="X",
            lat=34.0,
            lng=999.0,
        )
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
pytest tests/test_building_detection.py -v
```

Expected: `ImportError: cannot import name 'BuildingLocation' from 'src.models'`

- [ ] **Step 3: Add `BuildingLocation` and `map_data` to `src/models.py`**

Add this block **before** the `ChatResponse` class:

```python
from pydantic import field_validator

class BuildingLocation(BaseModel):
    """A CPP campus building identified in an answer."""

    building_id: str = Field(..., description="Building number as a string, e.g. '9'.")
    label: str = Field(..., description="Human-readable label, e.g. 'Building 9'.")
    name: str = Field(..., description="Building name, e.g. 'College of Engineering'.")
    lat: float = Field(..., description="Latitude of building centroid.")
    lng: float = Field(..., description="Longitude of building centroid.")
    room: str | None = Field(default=None, description="Room number if mentioned in answer.")

    @field_validator("lat")
    @classmethod
    def valid_lat(cls, v: float) -> float:
        if not -90 <= v <= 90:
            raise ValueError(f"lat {v} out of range [-90, 90]")
        return v

    @field_validator("lng")
    @classmethod
    def valid_lng(cls, v: float) -> float:
        if not -180 <= v <= 180:
            raise ValueError(f"lng {v} out of range [-180, 180]")
        return v
```

Then add `map_data` to `ChatResponse`:

```python
class ChatResponse(BaseModel):
    """Response payload for POST /chat."""

    conversation_id: str = Field(..., description="UUID for this conversation.")
    status: ChatStatus = Field(..., description="Outcome of the request.")
    answer_markdown: str = Field(..., description="Answer text in Markdown format.")
    citations: list[Citation] = Field(
        default_factory=list,
        description="Sources backing the answer (empty for not_found/error).",
    )
    debug_info: ChatDebugInfo | None = Field(
        default=None,
        description="Privileged debug details for authorized callers.",
    )
    map_data: "BuildingLocation | None" = Field(  # noqa: F821
        default=None,
        description="Building location if the answer references a CPP building.",
    )
```

Note: `BuildingLocation` must be defined before `ChatResponse` in the file.

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/test_building_detection.py -v
```

Expected: 4 tests PASS

- [ ] **Step 5: Verify existing tests still pass**

```bash
pytest tests/test_api.py -v
```

Expected: all existing tests PASS (`map_data=None` is additive, not breaking)

- [ ] **Step 6: Commit**

```bash
git add src/models.py tests/test_building_detection.py
git commit -m "feat: add BuildingLocation model and map_data field to ChatResponse"
```

---

## Task 3: Extraction Utility + Dependency

**Files:**
- Create: `src/api/building_coords.py`
- Modify: `tests/test_building_detection.py`

- [ ] **Step 1: Write failing extraction tests**

Append to `tests/test_building_detection.py`:

```python
"""Tests for extract_map_data utility."""
import pytest
from src.api.building_coords import extract_map_data

SAMPLE_COORDS = {
    "9":  {"lat": 34.0573, "lng": -117.8213, "name": "College of Engineering", "label": "Building 9"},
    "15": {"lat": 34.0581, "lng": -117.8198, "name": "University Library",     "label": "Building 15"},
}


def test_extract_building_number() -> None:
    result = extract_map_data("The Dean's office is in Building 9, Room 227.", SAMPLE_COORDS)
    assert result is not None
    assert result.building_id == "9"
    assert result.room == "227"
    assert result.name == "College of Engineering"


def test_extract_bldg_abbreviation() -> None:
    result = extract_map_data("Visit Bldg 15 for library services.", SAMPLE_COORDS)
    assert result is not None
    assert result.building_id == "15"


def test_extract_no_building_returns_none() -> None:
    result = extract_map_data("Check the graduation requirements online.", SAMPLE_COORDS)
    assert result is None


def test_extract_unknown_building_returns_none() -> None:
    result = extract_map_data("Head over to Building 99.", SAMPLE_COORDS)
    assert result is None


def test_extract_room_alphanumeric() -> None:
    result = extract_map_data("Building 9, Room 155A", SAMPLE_COORDS)
    assert result is not None
    assert result.room == "155A"


def test_extract_no_room() -> None:
    result = extract_map_data("Located in Building 9.", SAMPLE_COORDS)
    assert result is not None
    assert result.room is None


def test_extract_malformed_coords_returns_none() -> None:
    bad_coords = {"9": {"lat": 999.0, "lng": -117.0, "name": "Bad", "label": "Building 9"}}
    result = extract_map_data("Building 9, Room 1.", bad_coords)
    assert result is None
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/test_building_detection.py::test_extract_building_number -v
```

Expected: `ImportError: cannot import name 'extract_map_data'`

- [ ] **Step 3: Create `src/api/building_coords.py`**

```python
"""Building coordinates lookup and extraction for map panel feature."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from fastapi import Request

from src.models import BuildingLocation

logger = logging.getLogger(__name__)

_BUILDING_RE = re.compile(r'\b[Bb]uilding\s+(\d+)\b|\b[Bb]ldg\.?\s+(\d+)\b')
_ROOM_RE = re.compile(r'\b[Rr]oom\s+([\w-]+)\b')

COORDS_PATH = Path("data/building_coords.json")


def load_building_coords() -> dict[str, dict]:
    """Load building coordinates from JSON file.

    Returns an empty dict (feature disabled) if the file is missing.
    """
    if not COORDS_PATH.exists():
        logger.warning(
            "data/building_coords.json not found — map panel feature disabled"
        )
        return {}
    try:
        return json.loads(COORDS_PATH.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed to load building_coords.json")
        return {}


def extract_map_data(text: str, coords: dict[str, dict]) -> BuildingLocation | None:
    """Return a BuildingLocation if *text* mentions a known CPP building number.

    Returns None if no building is found, the building is unknown, or the
    coords entry is malformed (fails Pydantic validation).
    First match wins — deliberate v0.1 simplification.
    """
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
        logger.warning("Malformed coords entry for building %s — skipping", building_id)
        return None


def get_building_coords(request: Request) -> dict[str, dict]:
    """FastAPI dependency: return app-scoped building coords dict."""
    return getattr(request.app.state, "building_coords", {})
```

- [ ] **Step 4: Run extraction tests — expect PASS**

```bash
pytest tests/test_building_detection.py -v
```

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/api/building_coords.py tests/test_building_detection.py
git commit -m "feat: add building coords extraction utility and dependency"
```

---

## Task 4: Lifespan + Route Integration

**Files:**
- Modify: `src/api/main.py`
- Modify: `src/api/routes.py`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Write failing integration tests**

Append to the `TestChatEndpoint` class in `tests/test_api.py`:

```python
    @pytest.mark.asyncio
    async def test_chat_map_data_present_for_location_query(self) -> None:
        """map_data is populated when the answer mentions a building."""
        import json
        from pathlib import Path
        from unittest.mock import patch

        sample_coords = {
            "9": {
                "lat": 34.0573,
                "lng": -117.8213,
                "name": "College of Engineering",
                "label": "Building 9",
            }
        }

        # Fake LLM runner that always returns a building-mention answer
        async def building_llm_runner(messages, tools, settings):
            from src.models import ChatResponse, ChatStatus
            return ChatResponse(
                conversation_id="test-123",
                status=ChatStatus.ANSWERED,
                answer_markdown="The Dean's office is in Building 9, Room 227.",
                citations=[],
            )

        response = await chat(
            ChatRequest(message="Where is the engineering dean?"),
            store=None,
            retriever=FakeRetriever(),
            llm_runner=building_llm_runner,
            coords=sample_coords,
        )
        assert response.map_data is not None
        assert response.map_data.building_id == "9"
        assert response.map_data.room == "227"

    @pytest.mark.asyncio
    async def test_chat_map_data_none_for_non_location_query(self) -> None:
        """map_data is None when the answer has no building reference."""
        response = await chat(
            ChatRequest(message="What are graduation requirements?"),
            store=None,
            retriever=FakeRetriever(),
            llm_runner=fake_llm_runner,
            coords={},
        )
        assert response.map_data is None
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/test_api.py::TestChatEndpoint::test_chat_map_data_present_for_location_query -v
```

Expected: `TypeError: chat() got an unexpected keyword argument 'coords'`

- [ ] **Step 3: Add `building_coords` to lifespan in `src/api/main.py`**

Inside the `lifespan` function, after `app.state.llm_runner = None`, add:

```python
    from src.api.building_coords import load_building_coords
    app.state.building_coords = load_building_coords()
```

- [ ] **Step 4: Wire extraction into the chat handler in `src/api/routes.py`**

Add the import at the top of `routes.py`:

```python
from src.api.building_coords import extract_map_data, get_building_coords
```

Update the `chat` handler signature and body:

```python
@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    store: ConversationStore | None = Depends(get_conversation_store),
    retriever: object | None = Depends(get_retriever),
    llm_runner: object | None = Depends(get_llm_runner),
    coords: dict = Depends(get_building_coords),
) -> ChatResponse:
    """Handle a user chat message and return a grounded answer."""
    try:
        response = await run_tool_loop(
            message=request.message,
            conversation_id=(
                str(request.conversation_id)
                if request.conversation_id is not None
                else None
            ),
            store=store,
            max_turns=get_settings().conversation_history_max_turns,
            retriever=retriever,
            llm_runner=llm_runner,
        )
        response.map_data = extract_map_data(response.answer_markdown, coords)
        return response
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error in chat handler")
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred. Please try again later.",
        ) from None
```

- [ ] **Step 5: Run new tests — expect PASS**

```bash
pytest tests/test_api.py -v
```

Expected: all tests PASS including the two new ones

- [ ] **Step 6: Full test suite**

```bash
pytest -v
```

Expected: all tests PASS

- [ ] **Step 7: Commit**

```bash
git add src/api/main.py src/api/routes.py tests/test_api.py
git commit -m "feat: wire building extraction into chat route"
```

---

## Task 5: Frontend Types

**Files:**
- Modify: `frontend/src/types.ts`

- [ ] **Step 1: Add `BuildingLocation` interface and extend `Message` and `ChatResponse`**

Open `frontend/src/types.ts` and apply these changes:

```typescript
/** A CPP campus building location returned by the backend. */
export interface BuildingLocation {
  readonly building_id: string;
  readonly label: string;
  readonly name: string;
  readonly lat: number;
  readonly lng: number;
  readonly room: string | null;
}

/** Response body from POST /chat. */
export interface ChatResponse {
  readonly conversation_id: string;
  readonly status: MessageStatus;
  readonly answer_markdown: string;
  readonly citations: readonly Citation[];
  readonly map_data?: BuildingLocation;   // ← new
}

/** A single message displayed in the chat window. */
export interface Message {
  readonly id: string;
  readonly role: MessageRole;
  readonly content: string;
  readonly status?: MessageStatus;
  readonly citations?: readonly Citation[];
  readonly timestamp: number;
  readonly mapData?: BuildingLocation;    // ← new
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types.ts
git commit -m "feat: add BuildingLocation type and mapData to Message"
```

---

## Task 6: useChat Hook

**Files:**
- Modify: `frontend/src/hooks/useChat.ts`

- [ ] **Step 1: Update `UseChatReturn` and hook implementation**

Replace the entire `useChat.ts` with the updated version:

```typescript
import { useCallback, useMemo, useState } from 'react';
import { sendMessage } from '../api/client';
import type { BuildingLocation, Message } from '../types';

interface UseChatReturn {
  readonly messages: readonly Message[];
  readonly conversationId: string | undefined;
  readonly isLoading: boolean;
  readonly error: string | null;
  readonly lastMapData: BuildingLocation | null;
  readonly send: (text: string) => Promise<void>;
  readonly resetConversation: () => void;
  readonly onCloseMap: () => void;
}

function createId(): string {
  return crypto.randomUUID();
}

/**
 * Custom hook that manages the full conversation lifecycle.
 *
 * Handles sending messages, tracking loading/error state,
 * and building the message history for display.
 * Also derives lastMapData from the most recent assistant message
 * that contains a building location.
 */
export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<readonly Message[]>([]);
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mapDismissed, setMapDismissed] = useState(false);

  // Derive lastMapData from the most recent assistant message with mapData.
  // If the user has dismissed the panel (mapDismissed), return null.
  const lastMapData = useMemo<BuildingLocation | null>(() => {
    if (mapDismissed) return null;
    const assistantMessages = messages.filter((m) => m.role === 'assistant');
    for (let i = assistantMessages.length - 1; i >= 0; i--) {
      const m = assistantMessages[i];
      if (m.mapData && (m.mapData.lat !== 0 || m.mapData.lng !== 0)) {
        return m.mapData;
      }
    }
    return null;
  }, [messages, mapDismissed]);

  const send = useCallback(
    async (text: string): Promise<void> => {
      const trimmed = text.trim();
      if (trimmed.length === 0) return;

      setError(null);
      // Re-show map panel if new message arrives
      setMapDismissed(false);

      const userMessage: Message = {
        id: createId(),
        role: 'user',
        content: trimmed,
        timestamp: Date.now(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);

      try {
        const response = await sendMessage(conversationId, trimmed);

        if (!conversationId) {
          setConversationId(response.conversation_id);
        }

        const assistantMessage: Message = {
          id: createId(),
          role: 'assistant',
          content: response.answer_markdown,
          status: response.status,
          citations: response.citations,
          timestamp: Date.now(),
          mapData: response.map_data ?? undefined,
        };

        setMessages((prev) => [...prev, assistantMessage]);
      } catch (err) {
        const errorMsg =
          err instanceof Error ? err.message : 'An unexpected error occurred';
        setError(errorMsg);

        const errorMessage: Message = {
          id: createId(),
          role: 'assistant',
          content: 'Sorry, something went wrong. Please try again.',
          status: 'error',
          citations: [],
          timestamp: Date.now(),
        };

        setMessages((prev) => [...prev, errorMessage]);
      } finally {
        setIsLoading(false);
      }
    },
    [conversationId],
  );

  const resetConversation = useCallback((): void => {
    setMessages([]);
    setConversationId(undefined);
    setIsLoading(false);
    setError(null);
    setMapDismissed(false);
  }, []);

  const onCloseMap = useCallback((): void => {
    setMapDismissed(true);
  }, []);

  return {
    messages,
    conversationId,
    isLoading,
    error,
    lastMapData,
    send,
    resetConversation,
    onCloseMap,
  };
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/useChat.ts
git commit -m "feat: derive lastMapData in useChat and add onCloseMap"
```

---

## Task 7: Mock Update

**Files:**
- Modify: `frontend/src/api/mock.ts`

- [ ] **Step 1: Add `LOCATION_RESPONSE` and wire into `selectMockResponse`**

Add this constant after `FOLLOW_UP_RESPONSE`:

```typescript
const LOCATION_RESPONSE: ChatResponse = {
  conversation_id: '',
  status: 'answered',
  answer_markdown:
    'The Engineering Dean\'s office is located in **Building 9, Room 227** at Cal Poly Pomona. ' +
    'The College of Engineering administrative offices are on the second floor.',
  citations: [
    {
      title: 'College of Engineering — Contact & Location',
      url: 'https://www.cpp.edu/engineering/contact.shtml',
      snippet: 'Dean\'s Office: Building 9, Room 227. Phone: (909) 869-2472.',
    },
  ],
  map_data: {
    building_id: '9',
    label: 'Building 9',
    name: 'College of Engineering',
    lat: 34.0573,
    lng: -117.8213,
    room: '227',
  },
};
```

Update `selectMockResponse` — add before the "Default: factual response" return:

```typescript
  // Location triggers
  if (
    lower.includes('where') ||
    lower.includes('location') ||
    lower.includes('building') ||
    lower.includes('office') ||
    lower.includes('room') ||
    lower.includes('find') ||
    lower.includes('map')
  ) {
    return LOCATION_RESPONSE;
  }
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/mock.ts
git commit -m "feat: add location mock response with map_data for frontend testing"
```

---

## Task 8: MapPanel Component

**Files:**
- Create: `frontend/src/components/MapPanel.tsx`
- Create: `frontend/src/components/MapPanel.css`

- [ ] **Step 1: Install Leaflet**

```bash
cd frontend && npm install leaflet @types/leaflet
```

Expected: `leaflet` and `@types/leaflet` appear in `package.json` dependencies.

- [ ] **Step 2: Create `MapPanel.css`**

```css
/* === Map Panel === */

.map-panel {
  width: 26rem;
  height: 34rem;
  border-radius: 1.5rem;
  background: var(--panel-strong);
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
  backdrop-filter: blur(20px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

@media (prefers-reduced-motion: no-preference) {
  .map-panel {
    animation: map-panel-slide-in 0.28s cubic-bezier(0.22, 1, 0.36, 1);
  }
}

@keyframes map-panel-slide-in {
  from {
    opacity: 0;
    transform: translateY(16px) scale(0.97);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.map-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.9rem 1rem 0.75rem;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.map-panel__header-left {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.map-panel__icon {
  width: 2rem;
  height: 2rem;
  border-radius: 0.6rem;
  background: rgba(15, 95, 79, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.95rem;
}

.map-panel__eyebrow {
  margin: 0 0 0.15rem;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--brand);
}

.map-panel__title {
  margin: 0;
  font-family: 'Outfit', sans-serif;
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text);
}

.map-panel__close {
  border: 1px solid var(--border);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  color: var(--muted);
  padding: 0.3rem 0.65rem;
  font-size: 0.82rem;
  cursor: pointer;
  font-family: inherit;
}

.map-panel__close:hover {
  background: #fff;
}

/* The Leaflet map container — fills available space */
.map-panel__map {
  flex: 1;
  min-height: 0;
  position: relative;
}

/* Apply greyscale only to tile images, not the pin */
.map-panel__map .leaflet-tile-pane {
  filter: grayscale(1);
}

.map-panel__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border-top: 1px solid var(--border);
  flex-shrink: 0;
  background: var(--panel-strong);
}

.map-panel__footer-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.map-panel__building-badge {
  background: rgba(15, 95, 79, 0.1);
  color: var(--brand);
  font-weight: 700;
  font-size: 0.78rem;
  padding: 0.25rem 0.6rem;
  border-radius: 999px;
  font-family: 'Outfit', sans-serif;
  letter-spacing: 0.04em;
}

.map-panel__footer-text {
  font-size: 0.85rem;
  color: var(--muted);
}

.map-panel__directions {
  border: 1px solid var(--border);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  color: var(--brand);
  font-weight: 700;
  font-size: 0.82rem;
  padding: 0.35rem 0.8rem;
  cursor: pointer;
  font-family: inherit;
  text-decoration: none;
}

.map-panel__directions:hover {
  background: #fff;
}
```

- [ ] **Step 3: Create `MapPanel.tsx`**

```tsx
import 'leaflet/dist/leaflet.css';
import './MapPanel.css';

import L from 'leaflet';
import { useEffect, useRef } from 'react';
import type { BuildingLocation } from '../types';

// CPP campus bounding box — users cannot pan outside this area.
const CPP_BOUNDS = L.latLngBounds(
  L.latLng(34.049, -117.832),
  L.latLng(34.066, -117.812),
);
const CPP_CENTER: L.LatLngExpression = [34.0575, -117.8212];
const DEFAULT_ZOOM = 17;

// Custom brand-green SVG pin wrapped in a keyboard-focusable button.
// The button lets keyboard users open the popup via Enter/Space.
// aria-label is set dynamically per building in the useEffect below.
function buildPinIcon(ariaLabel: string): L.DivIcon {
  return L.divIcon({
    html: `
      <button
        class="map-pin-btn"
        tabindex="0"
        aria-label="${ariaLabel}"
        style="background:none;border:none;padding:0;cursor:pointer;display:block;"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="28" height="36" viewBox="0 0 28 36" aria-hidden="true">
          <path d="M14 0C6.27 0 0 6.27 0 14c0 9.63 14 22 14 22S28 23.63 28 14C28 6.27 21.73 0 14 0z"
                fill="#0f5f4f"/>
          <circle cx="14" cy="14" r="5" fill="white"/>
        </svg>
      </button>`,
    className: '',
    iconSize: [28, 36],
    iconAnchor: [14, 36],
    popupAnchor: [0, -38],
  });
}

function prefersReducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

interface MapPanelProps {
  readonly building: BuildingLocation;
  readonly onClose: () => void;
}

export function MapPanel({ building, onClose }: MapPanelProps): JSX.Element {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markerRef = useRef<L.Marker | null>(null);

  // Initialize Leaflet map once on mount
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current, {
      center: CPP_CENTER,
      zoom: DEFAULT_ZOOM,
      maxBounds: CPP_BOUNDS,
      maxBoundsViscosity: 1.0,
      minZoom: 15,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map);

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Update pin whenever building changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    // Remove previous marker
    if (markerRef.current) {
      markerRef.current.remove();
    }

    const latlng: L.LatLngExpression = [building.lat, building.lng];
    const popupContent = building.room
      ? `<strong>${building.label}</strong><br>${building.name}<br>Room ${building.room}`
      : `<strong>${building.label}</strong><br>${building.name}`;

    const ariaLabel = building.room
      ? `${building.label}, ${building.name}, Room ${building.room}`
      : `${building.label}, ${building.name}`;

    const marker = L.marker(latlng, { icon: buildPinIcon(ariaLabel) })
      .addTo(map)
      .bindPopup(popupContent, { offset: [0, -36] })
      .openPopup();

    // Allow keyboard users to open the popup via the focusable button inside the marker
    marker.on('add', () => {
      const el = marker.getElement();
      const btn = el?.querySelector<HTMLButtonElement>('.map-pin-btn');
      if (btn) {
        btn.addEventListener('click', () => marker.openPopup());
        btn.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            marker.openPopup();
          }
        });
      }
    });

    markerRef.current = marker;

    map.flyTo(latlng, DEFAULT_ZOOM, { animate: !prefersReducedMotion(), duration: 0.6 });
  }, [building]);

  const footerText = building.room
    ? `Room ${building.room} · ${building.name}`
    : building.name;

  const directionsUrl = `https://www.google.com/maps/search/?api=1&query=${building.lat},${building.lng}`;

  return (
    <section
      className="map-panel"
      role="complementary"
      aria-label={`Campus map showing ${building.label}`}
    >
      <div className="map-panel__header">
        <div className="map-panel__header-left">
          <div className="map-panel__icon" aria-hidden="true">📍</div>
          <div>
            <p className="map-panel__eyebrow">Location</p>
            <h3 className="map-panel__title">Cal Poly Pomona Campus</h3>
          </div>
        </div>
        <button
          className="map-panel__close"
          onClick={onClose}
          aria-label="Close map panel"
          type="button"
        >
          ✕
        </button>
      </div>

      <div className="map-panel__map" ref={containerRef} />

      <div className="map-panel__footer">
        <div className="map-panel__footer-info">
          <span className="map-panel__building-badge">{building.label}</span>
          <span className="map-panel__footer-text">{footerText}</span>
        </div>
        <a
          className="map-panel__directions"
          href={directionsUrl}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={`Open directions to ${building.label} in Google Maps`}
        >
          Directions ↗
        </a>
      </div>
    </section>
  );
}
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/MapPanel.tsx frontend/src/components/MapPanel.css
git commit -m "feat: add MapPanel component with Leaflet greyscale map and branded pin"
```

---

## Task 9: FloatingChatPanel Integration

**Files:**
- Modify: `frontend/src/components/FloatingChatPanel.tsx`

- [ ] **Step 1: Update `FloatingChatPanel` to accept map props and render `MapPanel`**

Replace `frontend/src/components/FloatingChatPanel.tsx`:

```tsx
import { ChatWindow } from './ChatWindow';
import { ErrorBanner } from './ErrorBanner';
import { MapPanel } from './MapPanel';
import type { BuildingLocation, Message } from '../types';

interface FloatingChatPanelProps {
  readonly error: string | null;
  readonly isLoading: boolean;
  readonly isOpen: boolean;
  readonly lastMapData: BuildingLocation | null;
  readonly messages: readonly Message[];
  readonly onClose: () => void;
  readonly onCloseMap: () => void;
  readonly onReset: () => void;
  readonly onSend: (message: string) => void;
}

export function FloatingChatPanel({
  error,
  isLoading,
  isOpen,
  lastMapData,
  messages,
  onClose,
  onCloseMap,
  onReset,
  onSend,
}: FloatingChatPanelProps): JSX.Element | null {
  if (!isOpen) {
    return null;
  }

  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: '0.75rem' }}>
      {lastMapData && (
        <MapPanel building={lastMapData} onClose={onCloseMap} />
      )}

      <div className="chat-modal" role="dialog" aria-modal="true">
        <div className="chat-modal__header">
          <div>
            <p className="chat-modal__eyebrow">Student support popup</p>
            <h3 className="chat-modal__title">Bronco Assistant</h3>
          </div>

          <div className="chat-modal__actions">
            <button className="button button--ghost" onClick={onReset} type="button">
              Reset
            </button>
            <button className="button button--ghost" onClick={onClose} type="button">
              Close
            </button>
          </div>
        </div>

        {error && <ErrorBanner message={error} />}

        <ChatWindow isLoading={isLoading} messages={messages} onSend={onSend} />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/FloatingChatPanel.tsx
git commit -m "feat: render MapPanel in FloatingChatPanel when lastMapData is set"
```

---

## Task 10: App.tsx Wiring + Accessibility

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Wire `lastMapData` and `onCloseMap` into `FloatingChatPanel`; add `aria-live` region**

In `App.tsx`, find the `useChat` destructuring (currently around line 22) and add the new fields:

```typescript
const { messages, isLoading, error, send, resetConversation, lastMapData, onCloseMap } = useChat();
```

Find the `<FloatingChatPanel>` JSX (around line 271) and add the new props:

```tsx
<FloatingChatPanel
  error={error}
  isLoading={isLoading}
  isOpen={isChatOpen}
  lastMapData={lastMapData}
  messages={messages}
  onClose={() => setIsChatOpen(false)}
  onCloseMap={onCloseMap}
  onReset={resetConversation}
  onSend={(text) => { void send(text); }}
/>
```

Add the `aria-live` region **adjacent to** `<FloatingChatPanel>` (above or below, in the same parent):

```tsx
{/* Screen reader announcement for map updates */}
<div
  aria-live="polite"
  aria-atomic="true"
  style={{ position: 'absolute', width: '1px', height: '1px', overflow: 'hidden', clip: 'rect(0,0,0,0)', whiteSpace: 'nowrap' }}
>
  {lastMapData ? `Map updated: ${lastMapData.label}` : ''}
</div>
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: wire map panel into App and add aria-live announcement"
```

---

## Task 11: End-to-End Verification

- [ ] **Step 1: Run full backend test suite**

```bash
pytest -v
```

Expected: all tests PASS

- [ ] **Step 2: Start backend and frontend**

```bash
# Terminal 1
uvicorn src.api.main:app --reload

# Terminal 2
cd frontend && npm run dev
```

- [ ] **Step 3: Test location query**

Open the app, open the chat. Ask: `"Where is the library?"`

Expected:
- Assistant answer mentions Building 15
- Map panel slides in to the left of the chat modal
- Greyscale OSM tiles visible, custom green pin on Building 15
- Popup shows "Building 15 / University Library"
- Footer shows `Building 15` badge + room (if any)

- [ ] **Step 4: Test building change**

Ask: `"Where is the Engineering Dean's office?"`

Expected: map panel flies smoothly to Building 9, popup updates.

- [ ] **Step 5: Test non-location query**

Ask: `"What are the graduation requirements?"`

Expected: map panel stays showing last building (Building 9), no crash, no new pin.

- [ ] **Step 6: Test panel close**

Click ✕ on map panel.

Expected: panel unmounts, chat modal expands back to its normal position.

- [ ] **Step 7: Test mock mode**

```bash
cd frontend && VITE_USE_MOCK=true npm run dev
```

Ask: `"Where is the office?"`

Expected: `LOCATION_RESPONSE` fires, map panel appears with Building 9 pin.

- [ ] **Step 8: Keyboard accessibility**

Tab through the UI with only the keyboard. Confirm:
- Map panel close button is reachable and activatable
- Directions link is reachable
- Screen reader (or DevTools accessibility tree) shows `aria-live` region updating on location answers

- [ ] **Step 9: Reduced motion**

Enable OS reduced-motion setting (Windows: Settings → Ease of Access → Display → Show animations). Reload the page.

Expected: map panel appears instantly (no slide animation), `flyTo` is instant.

- [ ] **Step 10: Final commit**

```bash
git add .
git commit -m "feat: campus map visualization complete (issue #30)"
```
