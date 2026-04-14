import type { ChatResponse } from '../types';

/**
 * Simulated latency range in milliseconds.
 * Adds realism to mock responses during Sprint 1 development.
 */
const MOCK_DELAY_MS = 800;

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function generateId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  // Fallback for non-secure contexts (plain HTTP)
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

const FACTUAL_RESPONSE: ChatResponse = {
  conversation_id: '',
  status: 'answered',
  answer_markdown:
    'The University Library at Cal Poly Pomona is open **Monday through Thursday from 7:30 AM to 10:00 PM**, ' +
    'Friday from 7:30 AM to 5:00 PM, Saturday from 10:00 AM to 5:00 PM, and Sunday from 12:00 PM to 10:00 PM. ' +
    'Hours may vary during holidays and finals week.',
  citations: [
    {
      title: 'University Library - Hours & Locations',
      url: 'https://www.cpp.edu/library/hours.shtml',
      snippet:
        'The University Library is open Monday-Thursday 7:30am-10pm, Friday 7:30am-5pm...',
    },
    {
      title: 'Library Services',
      url: 'https://www.cpp.edu/library/services.shtml',
      snippet:
        'Visit the University Library for study rooms, printing, and research assistance.',
    },
  ],
};

const FOLLOW_UP_RESPONSE: ChatResponse = {
  conversation_id: '',
  status: 'answered',
  answer_markdown:
    'Yes, the library offers **study room reservations** for groups of 2-8 students. ' +
    'You can reserve a room online through the library website up to 7 days in advance. ' +
    'Each reservation is limited to 2 hours.',
  citations: [
    {
      title: 'Study Room Reservations',
      url: 'https://www.cpp.edu/library/study-rooms.shtml',
      snippet:
        'Reserve a group study room for 2-8 students. Reservations can be made up to 7 days in advance.',
    },
  ],
};

const NOT_FOUND_RESPONSE: ChatResponse = {
  conversation_id: '',
  status: 'not_found',
  answer_markdown:
    "I don't have information about that in my campus knowledge base. " +
    'Try asking about campus services, academic programs, or student resources at Cal Poly Pomona.',
  citations: [],
};

const ERROR_RESPONSE: ChatResponse = {
  conversation_id: '',
  status: 'error',
  answer_markdown:
    'Sorry, something went wrong while processing your request. Please try again.',
  citations: [],
};

/**
 * Select a mock response based on the query content.
 * Provides deterministic responses for different query categories
 * so the UI can be tested against all status states.
 */
function selectMockResponse(message: string): ChatResponse {
  const lower = message.toLowerCase();

  // Out-of-scope / adversarial triggers
  if (
    lower.includes('ignore') ||
    lower.includes('pretend') ||
    lower.includes('forget your instructions') ||
    lower.includes('weather in tokyo') ||
    lower.includes('recipe')
  ) {
    return NOT_FOUND_RESPONSE;
  }

  // Error trigger for testing
  if (lower.includes('trigger error') || lower.includes('break')) {
    return ERROR_RESPONSE;
  }

  // Follow-up triggers
  if (
    lower.includes('also') ||
    lower.includes('follow up') ||
    lower.includes('study room') ||
    lower.includes('more about')
  ) {
    return FOLLOW_UP_RESPONSE;
  }

  // Default: factual response
  return FACTUAL_RESPONSE;
}

/**
 * Send a mock chat message and return a simulated API response.
 * Used in Sprint 1 when the backend is not yet available.
 */
export async function sendMockMessage(
  conversationId: string | undefined,
  message: string,
): Promise<ChatResponse> {
  await delay(MOCK_DELAY_MS);

  const response = selectMockResponse(message);

  return {
    ...response,
    conversation_id: conversationId ?? generateId(),
  };
}
