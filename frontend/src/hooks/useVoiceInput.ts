import { useCallback, useMemo, useRef, useState } from 'react';
import { transcribeAudio } from '../api/client';
import {
  VoiceInputError,
  type VoiceCaptureSession,
  type VoiceInputStatus,
  createNativeRecognitionSession,
  createRecordedTranscriptionSession,
  getVoiceInputCapability,
  shouldFallbackToRecording,
} from '../services/voiceInputService';

interface UseVoiceInputOptions {
  readonly disabled?: boolean;
  readonly onTranscript: (transcript: string) => void;
}

interface UseVoiceInputReturn {
  readonly helperText: string | null;
  readonly isSupported: boolean;
  readonly status: VoiceInputStatus;
  readonly toggleCapture: () => Promise<void>;
}

function getDisplayMessage(
  error: unknown,
  fallbackMessage: string,
): string {
  if (error instanceof VoiceInputError) {
    return error.message;
  }

  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message;
  }

  return fallbackMessage;
}

export function useVoiceInput({
  disabled = false,
  onTranscript,
}: UseVoiceInputOptions): UseVoiceInputReturn {
  const capability = useMemo(() => getVoiceInputCapability(), []);
  const [status, setStatus] = useState<VoiceInputStatus>('idle');
  const [helperText, setHelperText] = useState<string | null>(
    capability.unavailableReason,
  );
  const sessionRef = useRef<VoiceCaptureSession | null>(null);
  const startFallbackCaptureRef = useRef<(() => Promise<void>) | null>(null);

  const runSession = useCallback(
    (session: VoiceCaptureSession): void => {
      sessionRef.current = session;
      setStatus('listening');
      setHelperText(
        session.mode === 'native'
          ? 'Listening. Tap stop when you are done speaking.'
          : 'Recording your question. Tap stop when you are done speaking.',
      );

      session.promise
        .then((transcript) => {
          const trimmed = transcript.trim();
          if (trimmed.length === 0) {
            throw new VoiceInputError(
              'no-speech',
              'No speech was detected. Try again, or type your question instead.',
            );
          }

          onTranscript(trimmed);
          setStatus('idle');
          setHelperText('Transcript ready to review before sending.');
        })
        .catch((error: unknown) => {
          if (
            session.mode === 'native' &&
            shouldFallbackToRecording(error, capability) &&
            startFallbackCaptureRef.current
          ) {
            void startFallbackCaptureRef.current();
            return;
          }

          setStatus('error');
          setHelperText(
            getDisplayMessage(
              error,
              'Voice input is unavailable right now. You can keep typing instead.',
            ),
          );
        })
        .finally(() => {
          sessionRef.current = null;
        });
    },
    [capability, onTranscript],
  );

  const startFallbackCapture = useCallback(async (): Promise<void> => {
    setStatus('processing');
    setHelperText('Preparing the microphone and transcription fallback...');
    const session = await createRecordedTranscriptionSession(transcribeAudio);
    runSession(session);
  }, [runSession]);

  startFallbackCaptureRef.current = startFallbackCapture;

  const startCapture = useCallback(async (): Promise<void> => {
    if (disabled) {
      return;
    }

    if (!capability.supported) {
      setStatus('error');
      setHelperText(capability.unavailableReason);
      return;
    }

    try {
      if (capability.supportsNativeRecognition) {
        runSession(createNativeRecognitionSession());
        return;
      }

      await startFallbackCapture();
    } catch (error: unknown) {
      if (shouldFallbackToRecording(error, capability)) {
        try {
          await startFallbackCapture();
          return;
        } catch (fallbackError: unknown) {
          setStatus('error');
          setHelperText(
            getDisplayMessage(
              fallbackError,
              'Voice input failed before the transcript was ready.',
            ),
          );
          return;
        }
      }

      setStatus('error');
      setHelperText(
        getDisplayMessage(
          error,
          'Voice input failed before the transcript was ready.',
        ),
      );
    }
  }, [capability, disabled, runSession, startFallbackCapture]);

  const toggleCapture = useCallback(async (): Promise<void> => {
    const activeSession = sessionRef.current;
    if (activeSession) {
      setStatus('processing');
      setHelperText('Processing your audio...');
      activeSession.stop();
      return;
    }

    await startCapture();
  }, [startCapture]);

  return {
    helperText,
    isSupported: capability.supported,
    status,
    toggleCapture,
  };
}
