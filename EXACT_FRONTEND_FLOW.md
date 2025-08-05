# EXACT Frontend Flow - NO BULLSHIT

## What Frontend MUST Do - Step by Step

### STEP 1: User Selection Screen
```typescript
// User sees their assessments grouped by type
interface AssessmentDisplay {
  quickScans: Array<{
    id: string;
    body_part: string;  // "chest", "arm", "lesion", etc.
    created_at: string;
    urgency: string;
  }>;
  deepDives: Array<{
    id: string;
    body_part: string;
    status: "active" | "analysis_ready" | "completed";
    created_at: string;
  }>;
  // ... other types
}

// User clicks checkboxes to select SPECIFIC assessments
// DO NOT AUTO-SELECT ANYTHING
```

### STEP 2: Collect the EXACT IDs Selected
```typescript
// WRONG - Don't do this shit:
const selectedIds = getAllUserAssessments();  // NO!

// RIGHT - Only what they clicked:
const selectedData = {
  quick_scan_ids: [],  // Empty if none selected
  deep_dive_ids: [],   // Empty if none selected
  general_assessment_ids: [],
  general_deep_dive_ids: [],
  photo_session_ids: []
};

// When user checks a box:
function onQuickScanSelected(scanId: string, isChecked: boolean) {
  if (isChecked) {
    selectedData.quick_scan_ids.push(scanId);
  } else {
    selectedData.quick_scan_ids = selectedData.quick_scan_ids.filter(id => id !== scanId);
  }
}
```

### STEP 3: Call Triage (REQUIRED - DON'T SKIP)
```typescript
// You MUST call triage first to know which specialist endpoint to use
const triageResponse = await fetch('/api/report/specialty-triage', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: currentUserId,
    ...selectedData  // Spread the exact selections
  })
});

const triage = await triageResponse.json();

// CHECK FOR ERRORS
if (triage.status === 'error') {
  console.error('Triage failed:', triage);
  return;
}

const specialty = triage.triage_result.primary_specialty;
console.log('Specialty determined:', specialty);
```

### STEP 4: Create Analysis Record (REQUIRED)
```typescript
// You MUST create this record or the report generation will fail
const analysisId = crypto.randomUUID();

const analysisRecord = {
  id: analysisId,
  user_id: currentUserId,
  created_at: new Date().toISOString(),
  purpose: 'Specialist report',
  recommended_type: specialty,
  confidence: triage.triage_result.confidence,
  report_config: {
    time_range: {
      start: '2025-01-01',  // Optional
      end: '2025-01-31'     // Optional
    }
  },
  // Store the selected IDs for reference
  quick_scan_ids: selectedData.quick_scan_ids,
  deep_dive_ids: selectedData.deep_dive_ids
};

// INSERT INTO DATABASE
const { error } = await supabase
  .from('report_analyses')
  .insert(analysisRecord);

if (error) {
  console.error('Failed to create analysis:', error);
  return;
}
```

### STEP 5: Generate the Report
```typescript
// Map specialty to endpoint
const endpoints = {
  'cardiology': '/api/report/cardiology',
  'neurology': '/api/report/neurology',
  'psychiatry': '/api/report/psychiatry',
  'dermatology': '/api/report/dermatology',
  'gastroenterology': '/api/report/gastroenterology',
  'endocrinology': '/api/report/endocrinology',
  'pulmonology': '/api/report/pulmonology',
  'primary-care': '/api/report/primary-care',
  'orthopedics': '/api/report/orthopedics',
  'rheumatology': '/api/report/rheumatology'
};

const endpoint = endpoints[specialty] || '/api/report/specialist';

// Call the specialist endpoint with EXACT SAME IDs
const reportResponse = await fetch(endpoint, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    analysis_id: analysisId,  // From step 4
    user_id: currentUserId,
    ...selectedData  // EXACT same IDs from step 2
  })
});

const report = await reportResponse.json();

if (report.status === 'error') {
  console.error('Report generation failed:', report);
  return;
}
```

### STEP 6: Display the Report
```typescript
// The report structure is ALWAYS the same
const reportData = report.report_data;

// Display these sections IN ORDER:
displayExecutiveSummary(reportData.executive_summary);
displayClinicalSummary(reportData.clinical_summary);

// Specialty section name varies
const specialtySection = reportData[`${specialty}_assessment`];
if (specialtySection) {
  displaySpecialtyAssessment(specialtySection);
}

displayDiagnosticPriorities(reportData.diagnostic_priorities);
displayTreatmentRecommendations(reportData.treatment_recommendations);
displayFollowUpPlan(reportData.follow_up_plan);
```

---

## CRITICAL RULES - BREAK THESE AND IT WON'T WORK

### RULE 1: Only Send What's Selected
```typescript
// If user selects ONE lesion scan, send ONLY that ID
{
  quick_scan_ids: ["lesion-scan-id-123"],  // ONLY THIS
  deep_dive_ids: [],  // EMPTY if not selected
  // ... rest empty
}
```

### RULE 2: Always Create Analysis Record
```typescript
// This WILL fail:
const report = await fetch('/api/report/cardiology', {
  body: JSON.stringify({
    analysis_id: "some-random-id",  // Doesn't exist in DB = FAIL
    // ...
  })
});
```

### RULE 3: Use Triage Result for Endpoint
```typescript
// DON'T hardcode the specialty
// DON'T guess based on symptoms
// USE what triage tells you:
const specialty = triage.triage_result.primary_specialty;
const endpoint = `/api/report/${specialty}`;
```

---

## DEBUG CHECKLIST

If reports show wrong data:

1. **Check what IDs you're sending:**
```typescript
console.log('Sending these IDs:', {
  quick_scan_ids: selectedData.quick_scan_ids,
  deep_dive_ids: selectedData.deep_dive_ids
});
```

2. **Verify the analysis record exists:**
```typescript
const { data } = await supabase
  .from('report_analyses')
  .select('*')
  .eq('id', analysisId);
console.log('Analysis record:', data);
```

3. **Check the actual report request:**
```typescript
console.log('Report request body:', JSON.stringify({
  analysis_id: analysisId,
  user_id: currentUserId,
  ...selectedData
}, null, 2));
```

4. **Inspect what came back:**
```typescript
console.log('Report response:', report);
// Look at executive_summary.chief_complaints
// Should ONLY mention the selected assessments
```

---

## COMMON FUCKUPS

### Fuckup 1: Sending All User Data
```typescript
// WRONG - This sends everything
const allScans = await getUserQuickScans(userId);
const report = await generateReport({
  quick_scan_ids: allScans.map(s => s.id)  // NO!
});
```

### Fuckup 2: Not Creating Analysis Record
```typescript
// WRONG - Skipping analysis creation
const report = await fetch('/api/report/cardiology', {
  body: JSON.stringify({
    analysis_id: generateUUID(),  // Not in DB!
    user_id: userId
  })
});
// Returns: {"error": "Analysis not found"}
```

### Fuckup 3: Wrong Specialty Endpoint
```typescript
// WRONG - Hardcoding endpoint
const endpoint = '/api/report/cardiology';  // What if it's neuro?

// RIGHT - Use triage result
const endpoint = `/api/report/${triage.triage_result.primary_specialty}`;
```

### Fuckup 4: Mixing IDs from Different Users
```typescript
// WRONG - Don't mix data
{
  user_id: "user-123",
  quick_scan_ids: ["scan-from-user-456"]  // Different user!
}
```

---

## TEST YOUR SHIT

```typescript
// Test with ONE specific scan
async function testSingleScan() {
  const testScanId = "057447a9-3369-42b2-b683-778d10ae5c8b";
  const userId = "45b61b67-175d-48a0-aca6-d0be57609383";
  
  // 1. Triage
  const triage = await fetch('/api/report/specialty-triage', {
    method: 'POST',
    body: JSON.stringify({
      user_id: userId,
      deep_dive_ids: [testScanId]
    })
  }).then(r => r.json());
  
  console.log('Triage says:', triage.triage_result.primary_specialty);
  
  // 2. Create analysis
  const analysisId = crypto.randomUUID();
  await supabase.from('report_analyses').insert({
    id: analysisId,
    user_id: userId,
    created_at: new Date().toISOString(),
    recommended_type: triage.triage_result.primary_specialty,
    confidence: triage.triage_result.confidence,
    report_config: {}
  });
  
  // 3. Generate report
  const report = await fetch(`/api/report/${triage.triage_result.primary_specialty}`, {
    method: 'POST',
    body: JSON.stringify({
      analysis_id: analysisId,
      user_id: userId,
      deep_dive_ids: [testScanId]  // ONLY THIS ONE
    })
  }).then(r => r.json());
  
  // 4. Check it only has data from that ONE scan
  console.log('Chief complaints:', report.report_data.executive_summary.chief_complaints);
  // Should ONLY be about that specific assessment
}
```

---

That's it. Follow this EXACTLY or it won't work.