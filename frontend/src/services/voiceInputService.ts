export type VoiceInputStatus = 'idle' | 'listening' | 'processing' | 'error';

export interface VoiceInputCapability {
  readonly hasSecureContext: boolean;
  readonly supportsNativeRecognition: boolean;
  readonly supportsRecordingFallback: boolean;
  readonly supported: boolean;
  readonly unavailableReason: string | null;
}

export type VoiceInputErrorCode =
  | 'permission-denied'
  | 'secure-context-required'
  | 'unsupported'
  | 'no-speech'
  | 'upload-failed'
  | 'recording-failed'
  | 'recognition-failed';

export class VoiceInputError extends Error {
  readonly code: VoiceInputErrorCode;

  constructor(code: VoiceInputErrorCode, message: string) {
    super(message);
    this.code = code;
  }
}

export interface VoiceCaptureSession {
  readonly mode: 'native' | 'fallback';
  readonly promise: Promise<string>;
  stop: () => void;
}

interface NativeRecognitionResultEvent {
  readonly results: ArrayLike<ArrayLike<{ transcript: string }>>;
}

interface NativeRecognitionErrorEvent {
  readonly error: string;
}

interface NativeRecognitionInstance {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  maxAlternatives: number;
  onresult: ((event: NativeRecognitionResultEvent) => void) | null;
  onerror: ((event: NativeRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
}

interface NativeRecognitionConstructor {
  new (): NativeRecognitionInstance;
}

declare global {
  interface Window {
    SpeechRecognition?: NativeRecognitionConstructor;
    webkitSpeechRecognition?: NativeRecognitionConstructor;
  }
}

const LOCALHOST_HOSTNAMES = new Set(['localhost', '127.0.0.1', '::1']);
const RECORDING_CANDIDATE_TYPES = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/mp4',
];
const MAX_RECORDING_DURATION_MS = 30_000;

function canUseMicrophoneInCurrentContext(): boolean {
  if (typeof window === 'undefined') {
    return false;
  }

  if (window.isSecureContext) {
    return true;
  }

  return LOCALHOST_HOSTNAMES.has(window.location.hostname);
}

function getNativeRecognitionConstructor():
  | NativeRecognitionConstructor
  | undefined {
  if (typeof window === 'undefined') {
    return undefined;
  }

  return window.SpeechRecognition ?? window.webkitSpeechRecognition;
}

function pickRecordingMimeType(): string | undefined {
  if (typeof MediaRecorder === 'undefined') {
    return undefined;
  }

  for (const candidate of RECORDING_CANDIDATE_TYPES) {
    if (MediaRecorder.isTypeSupported(candidate)) {
      return candidate;
    }
  }

  return undefined;
}

function getAudioFileExtension(mimeType: string): string {
  if (mimeType.includes('mp4')) return 'mp4';
  return 'webm';
}

function coerceErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message;
  }

  return 'Voice input is unavailable right now.';
}

function isPermissionError(error: unknown): boolean {
  return (
    error instanceof DOMException &&
    (error.name === 'NotAllowedError' || error.name === 'SecurityError')
  );
}

export function getVoiceInputCapability(): VoiceInputCapability {
  const hasSecureContext = canUseMicrophoneInCurrentContext();
  const supportsNativeRecognition =
    typeof getNativeRecognitionConstructor() !== 'undefined';
  const supportsRecordingFallback =
    hasSecureContext &&
    typeof navigator !== 'undefined' &&
    typeof navigator.mediaDevices?.getUserMedia === 'function' &&
    typeof MediaRecorder !== 'undefined';

  if (!hasSecureContext) {
    return {
      hasSecureContext,
      supportsNativeRecognition,
      supportsRecordingFallback,
      supported: false,
      unavailableReason:
        'Voice input requires HTTPS on the hosted site. Text chat still works.',
    };
  }

  if (!supportsNativeRecognition && !supportsRecordingFallback) {
    return {
      hasSecureContext,
      supportsNativeRecognition,
      supportsRecordingFallback,
      supported: false,
      unavailableReason:
        'Voice input is unavailable in this browser. You can keep typing instead.',
    };
  }

  return {
    hasSecureContext,
    supportsNativeRecognition,
    supportsRecordingFallback,
    supported: true,
    unavailableReason: null,
  };
}

export function createNativeRecognitionSession(): VoiceCaptureSession {
  const Recognition = getNativeRecognitionConstructor();
  if (!Recognition) {
    throw new VoiceInputError(
      'unsupported',
      'Voice input is unavailable in this browser.',
    );
  }

  const recognition = new Recognition();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = 'en-US';
  recognition.maxAlternatives = 1;

  let isSettled = false;
  let transcript = '';

  const promise = new Promise<string>((resolve, reject) => {
    recognition.onresult = (event) => {
      transcript = Array.from(event.results)
        .map((result) => result[0]?.transcript ?? '')
        .join(' ')
        .trim();
      recognition.stop();
    };

    recognition.onerror = (event) => {
      if (isSettled) {
        return;
      }

      isSettled = true;
      const code =
        event.error === 'not-allowed' || event.error === 'service-not-allowed'
          ? 'permission-denied'
          : event.error === 'no-speech'
            ? 'no-speech'
            : 'recognition-failed';
      reject(
        new VoiceInputError(
          code,
          event.error === 'not-allowed' || event.error === 'service-not-allowed'
            ? 'Microphone access is blocked. You can keep typing, or enable mic access in your browser settings.'
            : event.error === 'no-speech'
              ? 'No speech was detected. Try again, or type your question instead.'
              : 'Browser speech recognition failed. Switching to upload fallback may help.',
        ),
      );
    };

    recognition.onend = () => {
      if (isSettled) {
        return;
      }

      isSettled = true;
      if (transcript.length === 0) {
        reject(
          new VoiceInputError(
            'no-speech',
            'No speech was detected. Try again, or type your question instead.',
          ),
        );
        return;
      }

      resolve(transcript);
    };

    recognition.start();
  });

  return {
    mode: 'native',
    promise,
    stop: () => recognition.stop(),
  };
}

export async function createRecordedTranscriptionSession(
  transcribe: (audioBlob: Blob, filename: string) => Promise<string>,
): Promise<VoiceCaptureSession> {
  if (!canUseMicrophoneInCurrentContext()) {
    throw new VoiceInputError(
      'secure-context-required',
      'Voice input requires HTTPS on the hosted site. Text chat still works.',
    );
  }

  if (
    typeof navigator === 'undefined' ||
    typeof navigator.mediaDevices?.getUserMedia !== 'function' ||
    typeof MediaRecorder === 'undefined'
  ) {
    throw new VoiceInputError(
      'unsupported',
      'Voice input is unavailable in this browser. You can keep typing instead.',
    );
  }

  let stream: MediaStream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (error: unknown) {
    if (isPermissionError(error)) {
      throw new VoiceInputError(
        'permission-denied',
        'Microphone access is blocked. You can keep typing, or enable mic access in your browser settings.',
      );
    }

    throw new VoiceInputError(
      'recording-failed',
      'Voice recording could not start in this browser.',
    );
  }

  const mimeType = pickRecordingMimeType();
  const recorder = mimeType
    ? new MediaRecorder(stream, { mimeType })
    : new MediaRecorder(stream);
  const chunks: BlobPart[] = [];
  const effectiveMimeType = recorder.mimeType || mimeType || 'audio/webm';

  const cleanup = (): void => {
    stream.getTracks().forEach((track) => track.stop());
  };

  let isSettled = false;
  let stopTimer: number | undefined;

  const promise = new Promise<string>((resolve, reject) => {
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunks.push(event.data);
      }
    };

    recorder.onerror = () => {
      if (isSettled) {
        return;
      }

      isSettled = true;
      cleanup();
      reject(
        new VoiceInputError(
          'recording-failed',
          'Voice recording failed before the upload could finish.',
        ),
      );
    };

    recorder.onstop = async () => {
      if (stopTimer) {
        window.clearTimeout(stopTimer);
      }

      cleanup();
      if (isSettled) {
        return;
      }

      isSettled = true;
      if (chunks.length === 0) {
        reject(
          new VoiceInputError(
            'no-speech',
            'No speech was detected. Try again, or type your question instead.',
          ),
        );
        return;
      }

      try {
        const blob = new Blob(chunks, { type: effectiveMimeType });
        const transcript = await transcribe(
          blob,
          `voice-input.${getAudioFileExtension(effectiveMimeType)}`,
        );
        resolve(transcript);
      } catch (error: unknown) {
        reject(
          new VoiceInputError('upload-failed', coerceErrorMessage(error)),
        );
      }
    };

    recorder.start();
    stopTimer = window.setTimeout(() => {
      if (recorder.state !== 'inactive') {
        recorder.stop();
      }
    }, MAX_RECORDING_DURATION_MS);
  });

  return {
    mode: 'fallback',
    promise,
    stop: () => {
      if (recorder.state !== 'inactive') {
        recorder.stop();
      }
    },
  };
}

export function shouldFallbackToRecording(
  error: unknown,
  capability: VoiceInputCapability,
): boolean {
  if (!capability.supportsRecordingFallback) {
    return false;
  }

  if (!(error instanceof VoiceInputError)) {
    return true;
  }

  return error.code === 'no-speech' || error.code === 'recognition-failed';
}
