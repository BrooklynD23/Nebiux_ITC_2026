# Voice Accessibility for Bronco Assistant

**Issue:** #25
**Date:** 2026-04-13
**Owner:** Contributor C (frontend lane) with Contributor B support for API fallback
**Status:** Approved for planning

---

## Context

The current app is a text-only web chat. The user enters plain text in the chat composer, the frontend sends `message` text to `POST /chat`, and assistant replies render as markdown with citations.

The team wants a distinctive accessibility-focused feature for the competition: let users speak a question into the chat, review the transcript before sending, and optionally have assistant replies read aloud. This should align with CSU and Cal Poly Pomona accessibility goals while staying lightweight enough for a judged demo on a hosted web app.

The repo already has:
- React + Vite frontend chat UI
- FastAPI backend with `POST /chat`
- hosted deployment guidance centered on a VM (`Google Cloud` or `AWS EC2`)
- OpenAI already present as a supported LLM provider in the backend stack

The design must respect web constraints:
- microphone capture requires a secure context in deployed environments
- browser speech recognition support is inconsistent across browsers
- automatic audio playback is blocked or discouraged by browser autoplay policies

---

## Goal

Add voice accessibility as a **hybrid progressive-enhancement layer** around the existing text chat flow.

Success means:
- users on supported browsers can tap a microphone control, speak a question, and see editable text inserted into the existing composer
- users can manually play assistant replies as speech with a clear, accessible control
- unsupported browsers still have a clean text-only experience with no broken UI
- the hosted judge-facing deployment supports microphone capture via HTTPS
- the first backend transcription fallback uses OpenAI audio transcription

Non-goals for this phase:
- changing the core `/chat` request or response contract
- auto-speaking every assistant answer
- multilingual voice support beyond English-first defaults
- Google Cloud STT integration in the first cut
- real-time bidirectional voice conversation

---

## Recommended Approach

Use a **hybrid design** with three layers:

1. **Browser-native first**
- Try browser speech recognition when available.
- This is the lightest path and gives the fastest perceived interaction.

2. **Backend transcription fallback**
- When browser speech recognition is unavailable, unsupported, or fails, record short audio in the browser and send it to a backend `POST /transcribe` route.
- The backend uses OpenAI audio transcription and returns plain text.

3. **Browser speech synthesis for output**
- Assistant answers remain text-first.
- Each assistant message gets a manual `Read aloud` / `Stop` control using browser text-to-speech.
- No autoplay.

This keeps the existing chat architecture stable while making voice available where it is realistic to support.

---

## Architecture

### Existing contracts that stay stable

`POST /chat` remains text-only:

```json
{
  "conversation_id": "optional",
  "message": "Where is the registrar office?"
}
```

The voice layer always converts speech into text before the normal send path. This avoids coupling the RAG and conversation logic to audio transport.

### New frontend units

Add focused frontend modules rather than expanding the chat input into a large mixed-responsibility component:

- `useVoiceInput` hook
  - owns browser capability detection
  - owns mic permission flow
  - chooses native recognition vs recorded-audio fallback
  - returns transcript text plus UI state

- `voiceInputService`
  - wraps browser APIs (`SpeechRecognition`, `MediaRecorder`, permission checks)
  - exposes a stable interface to the hook

- `useSpeechPlayback` hook
  - manages browser `speechSynthesis`
  - strips markdown into speech-friendly plain text
  - ensures only one reply is spoken at a time

- `AssistantAudioButton` component
  - per-message play/stop UI for assistant replies

### New backend unit

Add one narrow route:

`POST /transcribe`

Responsibilities:
- accept a short audio upload from the frontend
- validate content type and size
- pass audio to OpenAI transcription
- return normalized transcript text only
- return explicit error states for unsupported media, empty audio, upstream failure, or misconfiguration

This route does not create or mutate conversation state. It only returns text.

---

## Data Flow

### Voice input on a supported browser

1. User taps the microphone button beside the existing textarea.
2. Frontend requests microphone permission if needed.
3. If browser-native recognition is available, start recognition.
4. Recognized speech is inserted into the existing text area.
5. User can edit the transcript manually.
6. User taps `Send`, which calls the existing `send(text)` path and `POST /chat`.

### Voice input fallback path

1. User taps the microphone button.
2. Native speech recognition is unavailable or fails.
3. Frontend records a short clip with `MediaRecorder`.
4. Frontend uploads the clip to `POST /transcribe`.
5. Backend returns `{ "transcript": "..." }`.
6. Frontend inserts the transcript into the existing textarea for review before send.

### Reply playback

1. Assistant message renders normally as markdown and citations.
2. User taps `Read aloud` on one message.
3. Frontend converts markdown to speech-safe plain text.
4. Browser speech synthesis speaks the response.
5. UI changes to `Stop` while active.
6. Starting a new message playback cancels the previous one.

---

## UI and Interaction Design

### Chat input changes

Extend the existing composer with:
- microphone button next to the textarea
- visible state label or icon change for `idle`, `listening`, `processing`, and `error`
- small inline helper text for permission denial, unsupported browser, transcription failure, or HTTPS requirement

The textarea remains the primary control. Voice augments it; voice does not replace it.

### Assistant message changes

Each assistant message gains a compact secondary action:
- `Read aloud` when idle
- `Stop` when speaking

User messages do not need playback controls in v1.

### Accessibility requirements

- mic and playback buttons must be keyboard reachable
- controls must have explicit `aria-label`s
- state changes should be announced with accessible status text
- color should not be the sole way to indicate recording or errors
- if voice is unavailable, the control should explain why instead of silently failing

---

## Browser and Hosting Constraints

### Constraint 1: Speech recognition support is inconsistent

Browser-native speech recognition should be treated as an optimization, not the only path.

Design choice:
- detect support at runtime
- prefer native recognition when present
- fallback to backend transcription when native recognition is absent or errors out
- preserve text-only chat everywhere

### Constraint 2: Microphone access needs a secure context

For deployed voice support, the hosted app must run over HTTPS.

Design choice:
- update deployment guidance so the judge-facing VM path includes HTTPS termination
- local development may still use `localhost`, which browsers treat as secure enough for microphone APIs
- if the app is served on plain HTTP in a deployed environment, the UI should disable the mic path and explain the requirement

### Constraint 3: Autoplay policies and shared-space usability

Automatic reading of assistant messages is brittle and invasive.

Design choice:
- no autoplay for assistant replies
- manual per-message playback only

---

## API Contract Additions

### `POST /transcribe`

Request:
- `multipart/form-data`
- one audio file field, for example `audio`
- no additional metadata fields in the first cut

Response:

```json
{
  "transcript": "How do I apply for graduation?"
}
```

Error responses should be explicit and stable:
- `400` for empty or invalid uploads
- `413` for clips above the size limit
- `415` for unsupported media type
- `503` when transcription is unavailable because the server is not configured or the upstream provider is down

No conversation identifiers are involved in this route.

### Suggested guardrails

- short recording limit, e.g. 30-60 seconds
- limited accepted formats based on what `MediaRecorder` and the OpenAI transcription path can reliably handle
- transcript trimmed before returning
- empty transcript treated as a recoverable error, not a successful result

---

## Error Handling

### Frontend states

Handle these states explicitly:
- browser supports native recognition and it succeeds
- browser lacks native recognition but recording fallback succeeds
- microphone permission denied
- recording unsupported
- upload/transcription failed
- secure context missing on deployed host

User-facing guidance should stay short and actionable. Example:
- `Microphone access is blocked. You can keep typing, or enable mic access in your browser settings.`
- `Voice input requires HTTPS on the hosted site. Text chat still works.`

### Backend states

The backend should not leak upstream provider internals. Return stable errors and log the upstream details server-side.

If OpenAI credentials are missing, `POST /transcribe` should fail clearly with `503` and a message indicating transcription is unavailable.

---

## Implementation Notes by Surface

### Frontend

Expected touch points:
- `frontend/src/components/ChatInput.tsx`
- `frontend/src/components/MessageBubble.tsx`
- `frontend/src/hooks/useChat.ts` only if minor plumbing is needed
- new voice-specific hook/service/component files under `frontend/src/`

Design boundary:
- keep `useChat` responsible for conversation send/reset only
- keep voice capture logic out of message rendering
- keep playback logic independent from retrieval or chat networking

### Backend

Expected touch points:
- `src/api/routes.py` or a dedicated audio route module
- new transcription helper module for provider integration
- settings additions for audio limits and feature enablement

Design boundary:
- transcription helper returns plain text only
- `/chat` remains unaware of audio transport

### Deployment docs

Expected touch points:
- `README.md`
- `docs/judging-and-deployment.md`

Required update:
- the docs must no longer imply that plain HTTP hosting is sufficient for full feature parity; the hosted judge path needs HTTPS termination

---

## Testing Strategy

### Frontend tests

Add coverage for:
- mic button disabled/enabled behavior by capability state
- transcript insertion into the textarea
- fallback from native recognition to recorded-audio upload path
- playback control state transitions
- graceful handling of permission denial and server errors

### Backend tests

Add coverage for:
- valid audio upload returns transcript
- empty upload rejected
- unsupported media type rejected
- oversized upload rejected
- upstream transcription failure mapped to stable API error
- missing OpenAI configuration returns `503`

### Manual verification

Minimum manual matrix:
- Chrome on desktop over localhost
- Chrome or Edge on hosted HTTPS VM
- Safari on desktop if available
- unsupported or degraded browser path where text-only remains usable

Acceptance criteria:
- user can speak, review transcript, edit it, and send normally
- assistant reply playback is manual and stoppable
- no unsupported browser leaves the chat in a broken state
- hosted judge deployment supports mic access over HTTPS

---

## Phasing

### Phase 1: Demo-safe hybrid MVP

Ship:
- mic button in composer
- native speech recognition where available
- backend OpenAI transcription fallback
- manual text-to-speech playback on assistant replies
- HTTPS requirement documented for hosted voice support

### Phase 2: Future improvements

Defer until after the MVP is stable:
- Google Cloud STT option
- multilingual language selector
- transcript confidence indicators
- persistent user voice preferences
- richer audio controls like pause/resume or voice selection

---

## Recommendation

Implement the hybrid path now and keep the boundary strict:
- audio in the browser
- transcript as plain text before send
- existing `/chat` contract unchanged
- one narrow backend transcription route
- browser text-to-speech for manual reply playback

This is the simplest design that still tells a credible accessibility story in a hosted judge demo. It avoids overcommitting the backend, preserves the current RAG architecture, and gives the team a clear future branch for stronger speech infrastructure later.

---

## References

- MDN `SpeechRecognition`: https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition
- MDN `getUserMedia()`: https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia
- MDN autoplay guide: https://developer.mozilla.org/en-US/docs/Web/Media/Guides/Autoplay
- Can I Use `speech-recognition`: https://caniuse.com/speech-recognition
- Can I Use `speech-synthesis`: https://caniuse.com/speech-synthesis
- OpenAI speech-to-text guide: https://platform.openai.com/docs/guides/speech-to-text
