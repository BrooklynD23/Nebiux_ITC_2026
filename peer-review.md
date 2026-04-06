Below is the consolidated feature inventory for the project so the team can align on one scope. It combines the MISSA brief, the browser-extension direction, the mascot/dashboard UI direction, the hybrid-RAG architecture discussion, and the public campus-assistant patterns we reviewed. The competition itself requires chat, corpus search through tool calling, grounded answers, source attribution, and multi-turn context; the strongest bonus directions are specialized tools, starter questions, retrieval quality improvements, and analytics. Public campus-assistant projects repeatedly converged on admin dashboards, personalized recommendations, contextual overlays, multi-agent routing, and citation-first grounded answers.

1. Core product features
Conversational campus knowledge assistant
Multi-turn chat memory within the session
Grounded answers from the CPP corpus only
Explicit refusal when the answer is not in the corpus
Source attribution for every answer
Tool calling for retrieval instead of pure prompting
Local runnable prototype with clear documentation/demo flow
2. Browser extension experience
Chrome extension instead of only a standalone web app
Floating assistant widget available on any CPP page
Minimized assistant state when not active
Expandable chat panel/sidebar when activated
Persistent on-screen mascot trigger
Billy Bronco themed visual identity for the assistant
Main dashboard/home panel inside the extension
Page-aware assistance based on what the student is currently viewing
Read current URL, page title, headings, and selected text
Contextual help without forcing the user to retype page details
One-click deep links from answers into the live CPP page or official service
3. Retrieval and intelligence layer
Hybrid retrieval as the baseline
lexical search
semantic search
reranking layer
Strong citation-first answer generation
Follow-up question handling with retained context
Query classification before retrieval
Intent routing to specialized tools
Optional graph or structured retrieval later for harder multi-hop cases
Confidence thresholding before answer generation
No-hallucination behavior
Semantic search tuning and relevance evaluation
Analytics on failed retrievals and zero-result questions
4. Specialized tools we have discussed
Corpus search tool
Page-context extraction tool
Contact finder tool
Office/location lookup tool
Deadline/date lookup tool
Campus map/navigation tool
Form/action detector
Appointment/resource handoff tool
Safety/emergency quick-action tool
Suggested-question generator based on page context
Recommender tool for events, opportunities, and resources
5. Contextual UX features
Page-specific starter questions instead of generic prompts
Suggested prompts based on page type
Citation drawer / evidence panel
“Why this answer” explanation via source snippets
Action cards under answers
Open official page button
Copy answer / copy citation
Quick follow-up chips
Recent questions/history view
Session resume behavior
Profile-aware prompt personalization
6. Student profile and memory features
Lightweight onboarding profile
Persistent memory across sessions
Major / program
year / class standing
transfer status
commuter vs housing
international student flag
preferred language
interests / goals
personalization of recommendations and prompts based on the stored profile
7. Campus workflows and action surfaces

These are especially valuable because CPP already exposes real service endpoints the extension can point students to, including safety escort, CPP Connect appointments, EH&S safety reporting, and the interactive campus map.

Map and location help
“Take me there” actions for campus buildings/services
Emergency and police quick links
Safety escort access
EH&S safety concern reporting
CPP Connect appointment routing
International Center advisor/contact routing
Visit-planning / directions support for places like BioTrek
Official office contact surfacing when the bot should hand off instead of answering
8. Personalized student-support features
Personalized resource recommendations
Clubs and event recommendations
Internship/opportunity recommendations
Study-abroad guidance
Milestone / checklist guidance
“What should I do next?” prompts based on profile and page context
Opportunity feed/dashboard inside the extension

Public student projects repeatedly used personalization for events, milestones, internships, and study-abroad support, which is why this stayed in scope in our discussion.

9. Accessibility and usability features
Voice input
Voice output / read-aloud mode
Multilingual support
Keyboard-friendly controls
Clean minimal UI
Mobile-like quick actions inside the extension
High-visibility emergency/help buttons

Voice and smart-dashboard patterns already show up in recent campus-assistant builds, so this is a credible stretch direction rather than a random add-on.

10. Admin, analytics, and team-facing features
Analytics dashboard
Top questions
Failed questions
Low-confidence answer rates
Most confusing pages on cpp.edu
Most-clicked resources/actions
Search quality diagnostics
Citation coverage tracking
Feedback collection
Admin insight panel for improvement priorities

Admin dashboards and analytics show up repeatedly in public campus-assistant submissions, especially where the product goes beyond Q&A into campus support workflows.

11. Multi-agent / council-of-agents direction

This is not mandatory for MVP, but it has been part of project discussion.

Hierarchical council of agents
Cheap retrieval/helper agents
Stronger reasoning/synthesis agent
Grounding/citation checker agent
Safety/policy gate agent
Router/triage agent
Optional specialist agents by domain
admissions
financial aid
safety
international
academic advising
campus life

That direction is consistent with the enterprise-agentic patterns in the deep-research report and with public campus multi-agent examples.

12. Trust, governance, and failure-handling features
Low-confidence refusal instead of guessing
Source-linked answers
Official-vs-unofficial distinction when applicable
Human handoff to the correct office
Auditability of answers and tool usage
Logging and observability
Retrieval evaluation set
Safety rules for sensitive topics
Privacy-conscious profile storage

Citation-backed low-confidence refusal is one of the clearest trust patterns in successful campus assistant deployments.

13. Recommended scope split for teammates
MVP
Chat assistant
Tool-called corpus search
Grounded answers
Source attribution
Multi-turn context
Floating browser extension UI
Page-context reading
Starter questions
Hybrid retrieval + reranking
Citation drawer
Action cards
Basic analytics
Strong stretch goals
Persistent student profile
Personalized recommendations
Voice
Multilingual support
Admin dashboard
Human handoff
More specialized tools
Ambitious stretch goals
Multi-agent council
Opportunity feed
Community-wisdom lane separate from official answers
Graph retrieval
Deeper workflow integrations
14. One-line product summary for teammates

A Billy Bronco-themed Chrome extension that reads the CPP page a student is on, retrieves grounded answers from the CPP corpus with citations, suggests context-aware next questions, and turns answers into direct actions such as maps, appointments, reporting, and safety/help workflows.