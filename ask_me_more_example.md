# Real Example: What Ask Me More Actually Does 🔥

## Initial Deep Dive Session:
```
Body Part: Left Shoulder
Symptoms: Sharp pain when lifting arm, worse at night
Q1-6 Asked → Confidence: 70%
Diagnosis: Rotator Cuff Tendinitis
```

## User Clicks "Ask Me More" (wants 90% confidence)

### What Happens Behind the Scenes:

#### 1. AI Gets This Context:
```
Current Diagnosis: Rotator Cuff Tendinitis (70% confidence)
Need to reach: 90% confidence
Differentials: 
- Impingement Syndrome (25%)
- Partial Tear (15%)
Questions already asked: 6
Patient data: All previous Q&A
```

#### 2. AI Thinks:
"I need to differentiate between tendinitis and a partial tear. The key difference is mechanical symptoms like clicking/popping"

#### 3. AI Generates:
```json
{
  "question": "Do you hear or feel any clicking, popping, or catching sensations when you move your shoulder?",
  "question_category": "differential_diagnosis",
  "reasoning": "Mechanical symptoms suggest structural damage (tear) vs inflammation alone",
  "expected_confidence_gain": 15,
  "targets_condition": "Partial Rotator Cuff Tear"
}
```

## If User Says "Yes, clicking sounds":
- Confidence might jump to 85%
- Diagnosis might change to "Partial Rotator Cuff Tear"
- Next question targets imaging needs

## If User Says "No clicking":
- Confidence increases to 85% for Tendinitis
- Next question might be about response to anti-inflammatories

## The AI Adapts Each Question Based On:
- Previous answers
- Remaining diagnostic uncertainty
- Most likely differentials
- Red flags not yet checked

## Real Questions It Might Ask:
1. "Have you tried anti-inflammatory medication? If yes, did it help?"
2. "Can you sleep on the affected side without pain?"
3. "Is the pain worse with overhead activities or behind-the-back movements?"
4. "Have you noticed any weakness when trying to hold objects at arm's length?"
5. "Does the pain radiate down your arm past the elbow?"

Each question is specifically chosen to:
- Rule in/out specific conditions
- Increase diagnostic confidence
- Guide treatment recommendations

## It's NOT Generic!
The AI analyzes your specific case and generates targeted diagnostic questions, just like a real doctor would ask follow-up questions to narrow down the diagnosis.

That's why Ask Me More can take you from 70% → 90% confidence with smart, targeted questions! 🎯