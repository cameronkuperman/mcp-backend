# Doctor Visit Enhancement Prompt

## Context
You are tasked with implementing intelligent, contextual actions throughout a health tracking application that help users prepare for doctor visits. The goal is to surface relevant "Add to Doctor Report" actions at the exact moment users encounter information their doctor should know about.

## Core Principle
Every piece of health data that could influence medical decisions should have a frictionless path to inclusion in a doctor's report. Think of this as "Pinterest for medical data" - users should be able to "pin" any insight, symptom, or pattern for their next appointment.

## Implementation Requirements

### 1. Identify Pinnable Moments
Analyze the codebase to find all locations where medically relevant information appears:
- Symptom entries
- Pattern discoveries  
- Concerning trends
- Medication changes
- Photo documentation
- Test results
- AI-generated insights

### 2. Contextual Pin Actions
For each pinnable moment, implement:
```javascript
// Every medical data point should be pinnable
const PinnableInsight = ({ data, context }) => {
  const isPinned = useDoctorReport(data.id);
  
  return (
    <div className="insight-container">
      <InsightContent {...data} />
      <PinButton
        isPinned={isPinned}
        onClick={() => toggleDoctorReport(data.id)}
        tooltip={isPinned ? "Remove from doctor report" : "Add to doctor report"}
      >
        <Icon name={isPinned ? "bookmark-filled" : "bookmark-outline"} />
      </PinButton>
    </div>
  );
};
```

### 3. Smart Suggestions
Proactively suggest items for doctor reports based on:
- Severity thresholds (pain > 7, symptoms > 3 days)
- Pattern significance (recurring symptoms)
- Red flags (sudden changes, concerning combinations)
- Time sensitivity (new symptoms since last visit)

### 4. Report Building Interface
Create a dedicated "Doctor Visit Prep" section that:
- Shows all pinned items organized by category
- Generates a chronological narrative
- Highlights changes since last visit
- Exports as PDF or shareable link
- Includes relevant visualizations

### 5. Cross-Component Intelligence
When implementing, ensure:
- Pinned items persist across sessions
- Related items are automatically suggested
- Temporal relationships are preserved
- Context is maintained (when, where, severity)

## Expected Outcome
Users should be able to walk into any doctor's appointment with a comprehensive, organized report that captures every relevant health event, pattern, and concern - without having to manually compile it at the last minute.

## Code Quality Standards
- Every pin action should complete in < 100ms
- All pinned data must be encrypted at rest
- Include undo functionality for accidental pins
- Maintain audit trail of what was shared with which doctor
- Support multiple concurrent doctor reports (specialist vs GP)

## Extension Opportunities
Consider how this pattern could extend to:
- Insurance claim documentation
- Clinical trial participation
- Second opinion preparation  
- Emergency medical information
- Family health history sharing