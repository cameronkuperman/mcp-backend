# Category-Specific Form Questions - Maximally Leveraged Edition

This document lists all the unique form fields/questions for each General Assessment category. These questions are designed to cast a wide diagnostic net and capture maximum clinical information while remaining user-friendly.

**Note**: Base fields that all categories share (symptoms, duration, impactLevel, aggravatingFactors, triedInterventions) are not included here.

---

## 🔋 Energy & Fatigue

### fatigueSeverity
- **Type**: Select one (Required)
- **Question**: "How would you describe your tiredness/fatigue?"
- **Options**:
  - `"normal_tired"` - Normal tired - better with rest
  - `"exhausted_after_sleep"` - Exhausted even after sleeping
  - `"sudden_crashes"` - Sudden energy crashes during day
  - `"constant_drain"` - Constant drain, never refreshed
  - `"not_tired"` - Not tired, other symptoms
- **Clinical Value**: Differentiates sleep debt from pathological fatigue (CFS, thyroid, anemia)

### activityCapacity
- **Type**: Select one (Required)
- **Question**: "Compared to your normal self, you can do:"
- **Options**:
  - `"0-25%"` - 0-25% of usual activities
  - `"25-50%"` - 25-50% of usual activities
  - `"50-75%"` - 50-75% of usual activities
  - `"75-100%"` - 75-100% but struggling
- **Clinical Value**: Quantifies functional impairment for disability assessment

### associatedSymptoms
- **Type**: Multi-select
- **Question**: "Along with fatigue, experiencing:"
- **Options**:
  - `"muscle_weakness"` - Muscle weakness
  - `"brain_fog"` - Brain fog/memory issues
  - `"unrefreshing_sleep"` - Unrefreshing sleep
  - `"body_aches"` - Body aches
  - `"none"` - None of these
- **Clinical Value**: Identifies CFS/ME patterns, fibromyalgia, or systemic conditions

### specificActivitiesAffected
- **Type**: Text (Optional)
- **Question**: "What specific activities are most affected by fatigue?"
- **Placeholder**: "e.g., Can't climb stairs, can't concentrate at work"
- **Clinical Value**: Helps differentiate physical vs mental fatigue

---

## 🧠 Mental Health

### mainDifficulty
- **Type**: Multi-select (Required)
- **Question**: "What aspect of daily life is most affected?"
- **Options**:
  - `"energy_motivation"` - Energy and motivation
  - `"mood_emotions"` - Mood and emotions
  - `"worry_thoughts"` - Worry and racing thoughts
  - `"sleep_appetite"` - Sleep and appetite
  - `"memory_concentration"` - Memory and concentration
  - `"physical_symptoms"` - Physical symptoms (headaches, chest pain, etc.)
  - `"relationships"` - Relationships and social life
- **Clinical Value**: Maps to DSM-5 domains, helps differentiate depression vs anxiety vs other

### symptomDescription
- **Type**: Text (Required)
- **Question**: "Briefly describe what you're experiencing"
- **Placeholder**: "1-2 sentences about your main concerns"
- **Clinical Value**: Unstructured data reveals thought patterns, severity

### mainStruggle
- **Type**: Multi-select
- **Question**: "What's hardest right now?"
- **Options**:
  - `"getting_through_day"` - Getting through the day
  - `"controlling_worry"` - Controlling worry/fear
  - `"feeling_happy"` - Feeling happy or motivated
  - `"sleeping_eating"` - Sleeping or eating normally
  - `"focusing"` - Focusing or remembering
  - `"relationships"` - Managing relationships
- **Clinical Value**: Functional impact assessment for treatment planning

### durationPattern
- **Type**: Select one
- **Question**: "This has been going on:"
- **Options**:
  - `"days"` - Days
  - `"weeks"` - Weeks
  - `"months"` - Months
  - `"years"` - Years
  - `"episodic"` - Comes and goes
- **Clinical Value**: Distinguishes acute vs chronic, screens for bipolar patterns

---

## 🤒 Feeling Sick

### onsetSpeed
- **Type**: Select one (Required)
- **Question**: "Your symptoms started:"
- **Options**:
  - `"sudden_hours"` - Suddenly (hours)
  - `"quick_days"` - Quickly (1-2 days)
  - `"gradual_week"` - Gradually (days-week)
  - `"slow_weeks"` - Slowly (weeks+)
- **Clinical Value**: Acute infections vs chronic conditions vs gradual onset

### mainSymptoms
- **Type**: Multi-select (Required)
- **Question**: "Main symptoms include:"
- **Options**:
  - `"fever_chills"` - Fever/chills
  - `"cough_congestion"` - Cough/congestion
  - `"sore_throat"` - Sore throat
  - `"body_aches"` - Body aches
  - `"stomach_issues"` - Stomach issues
  - `"headache"` - Headache
  - `"fatigue"` - Fatigue
  - `"other"` - Other → [text box appears]
- **Clinical Value**: Syndrome recognition (flu vs cold vs GI vs other)

### severityProgression
- **Type**: Select one
- **Question**: "Over time, symptoms are:"
- **Options**:
  - `"worse_quickly"` - Getting worse quickly
  - `"worse_slowly"` - Slowly worsening
  - `"stable"` - Staying the same
  - `"improving"` - Starting to improve
  - `"fluctuating"` - Going up and down
- **Clinical Value**: Identifies need for urgent care vs watchful waiting

### riskFactors
- **Type**: Multi-select
- **Question**: "In past 2 weeks have you:"
- **Options**:
  - `"traveled"` - Traveled
  - `"sick_contact"` - Been around sick people
  - `"new_medication"` - Started new medication
  - `"unusual_food"` - Eaten unusual food
  - `"high_stress"` - Been very stressed
  - `"none"` - None of these
- **Clinical Value**: Exposure history for infectious vs non-infectious causes

### additionalDetails
- **Type**: Text (Optional)
- **Question**: "Any other symptoms or details?"
- **Placeholder**: "Anything else that might be relevant"

---

## 💊 Medication Side Effects

### whichMedications
- **Type**: Multi-select (Required)
- **Question**: "Experiencing side effects from:"
- **Options**:
  - `"new_med"` - New medication (< 1 month)
  - `"dose_change"` - Recent dose change
  - `"long_term"` - Long-term medication
  - `"multiple"` - Multiple medications
  - `"stopped"` - Stopped a medication
  - `"unsure"` - Unsure which one
- **Clinical Value**: Temporal relationship to medication changes

### systemAffected
- **Type**: Multi-select (Required)
- **Question**: "Main side effect involves:"
- **Options**:
  - `"stomach"` - Stomach/digestion
  - `"dizzy_balance"` - Dizziness/balance
  - `"mood_sleep"` - Mood/sleep changes
  - `"skin_allergic"` - Skin/allergic
  - `"sexual_urinary"` - Sexual/urinary
  - `"other"` - Other system
- **Clinical Value**: Identifies drug class effects and severity

### effectOnLife
- **Type**: Select one
- **Question**: "Side effects are:"
- **Options**:
  - `"tolerable"` - Tolerable, minor annoyance
  - `"affecting_daily"` - Affecting daily activities
  - `"unbearable"` - Unbearable, need alternative
  - `"dangerous"` - Dangerous/concerning
- **Clinical Value**: Determines urgency of medication adjustment

### medicationHistory
- **Type**: Multi-select
- **Question**: "History with medications:"
- **Options**:
  - `"sensitive"` - Sensitive to many medications
  - `"low_doses"` - Need lower doses than typical
  - `"allergic"` - Had allergic reactions
  - `"first_time"` - First time with side effects
- **Clinical Value**: Identifies drug-sensitive patients

### managementAttempts
- **Type**: Multi-select
- **Question**: "To manage side effects, tried:"
- **Options**:
  - `"with_food"` - Taking with food
  - `"timing_change"` - Different time of day
  - `"split_dose"` - Splitting dose
  - `"skipping"` - Skipping doses
  - `"nothing"` - Nothing yet
  - `"other"` - Other → [text box]

### timingDescription
- **Type**: Text (Optional)
- **Question**: "Describe the timing and nature of side effects"
- **Placeholder**: "When do they occur, how long do they last?"

---

## 🔄 Multiple Issues

### symptomTimeline
- **Type**: Select one (Required)
- **Question**: "Did symptoms start simultaneously?"
- **Options**:
  - `"yes_simultaneous"` - Yes - all at once
  - `"no_sequential"` - No - at different times
- **Clinical Value**: Single systemic cause vs multiple conditions

### symptomOrder
- **Type**: Text (Conditional - if no_sequential)
- **Question**: "Which symptoms came first? List in order:"
- **Placeholder**: "1st: [symptom], Then: [symptom], Then: [symptom]"
- **Clinical Value**: Identifies primary condition and cascading effects

### timingRelationship
- **Type**: Select one
- **Question**: "Your various symptoms:"
- **Options**:
  - `"all_together"` - All started together
  - `"cascade"` - One led to others
  - `"independent"` - Independent timing
  - `"flare_together"` - Flare up together
- **Clinical Value**: Autoimmune vs multiple separate conditions

### patternRecognition
- **Type**: Multi-select
- **Question**: "Symptoms are worse:"
- **Options**:
  - `"morning"` - Morning
  - `"evening"` - Evening
  - `"with_stress"` - With stress
  - `"with_activity"` - With activity
  - `"with_foods"` - With certain foods
  - `"no_pattern"` - No pattern
- **Clinical Value**: Identifies triggers and circadian patterns

### systemsInvolved
- **Type**: Multi-select
- **Question**: "Symptoms involve:"
- **Options**:
  - `"energy_joints"` - Energy + joint pain
  - `"gut_skin_joints"` - Gut + skin + joints
  - `"everything_hurts"` - Everything hurts
  - `"neuro_fatigue"` - Neurological + fatigue
  - `"random"` - Random/no pattern
- **Clinical Value**: Screens for systemic conditions (autoimmune, fibromyalgia, MS)

---

## ❓ Unsure

### functionalTrigger
- **Type**: Select one
- **Question**: "I'm seeking help because:"
- **Options**:
  - `"others_noticed"` - Others say I'm different
  - `"cant_do_activities"` - Can't do usual activities
  - `"worried"` - Worried about symptoms
  - `"prevent_worsening"` - Want to prevent worsening
- **Clinical Value**: Objective vs subjective concerns

### subtleChanges
- **Type**: Multi-select
- **Question**: "Have you noticed:"
- **Options**:
  - `"need_stimulants"` - Need more coffee/stimulants
  - `"clothes_fit"` - Clothes fit differently
  - `"people_asking"` - People asking if I'm OK
  - `"forgetful"` - More forgetful
  - `"none"` - None really
- **Clinical Value**: Early detection of systemic changes

### currentActivity
- **Type**: Text
- **Question**: "What made you decide to seek help today?"
- **Placeholder**: "What prompted this visit?"

### recentChanges
- **Type**: Text
- **Question**: "Any recent changes in your life or routine?"
- **Placeholder**: "New job, diet, stress, medications, etc."

---

## 💪 Physical/Body

### bodyRegion
- **Type**: Select one (Required)
- **Question**: "What area of your body is affected?"
- **Options**: [Keep existing - head_neck, chest, abdomen, back, arms, legs, joints, skin, multiple]

### issueType
- **Type**: Select one (Required)
- **Question**: "What type of issue are you experiencing?"
- **Options**: [Keep existing - pain, injury, weakness, numbness, swelling, rash, other]

### issueCharacteristics
- **Type**: Dynamic based on issueType
- **Question & Options**: Varies by issue type:

#### If issueType = "pain":
- **Question**: "Pain pattern:"
- **Options**:
  - `"sharp_movement"` - Sharp with specific movements
  - `"constant_ache"` - Constant ache
  - `"throbbing"` - Throbbing/pulsing
  - `"burning_tingling"` - Burning/tingling
  - `"wave_pattern"` - Comes in waves
  - `"moving"` - Changes location
  - `"other"` - Other → [text box]

#### If issueType = "weakness":
- **Question**: "Weakness pattern:"
- **Options**:
  - `"cant_lift"` - Can't lift/grip things
  - `"legs_give_out"` - Legs give out
  - `"general_weak"` - Generally feel weak
  - `"one_side"` - One side weaker
  - `"worse_with_use"` - Gets worse with use

#### If issueType = "numbness":
- **Question**: "Numbness/tingling:"
- **Options**:
  - `"complete_loss"` - Complete loss of feeling
  - `"pins_needles"` - Pins and needles
  - `"intermittent"` - Comes and goes
  - `"spreading"` - Spreading/getting worse
  - `"positional"` - With position changes

#### If issueType = "swelling":
- **Question**: "Swelling pattern:"
- **Options**:
  - `"worse_evening"` - Worse by end of day
  - `"constant"` - Constant
  - `"intermittent"` - Comes and goes
  - `"one_side"` - One side only
  - `"multiple_areas"` - Multiple areas

#### If issueType = "rash":
- **Question**: "Rash characteristics:"
- **Options**:
  - `"itchy"` - Itchy
  - `"painful"` - Painful/burning
  - `"spreading"` - Spreading
  - `"intermittent"` - Comes and goes
  - `"with_symptoms"` - With other symptoms

### mechanicalBehavior
- **Type**: Select one
- **Question**: "Issue behavior:"
- **Options**:
  - `"predictable_movement"` - Predictable with specific movements
  - `"constant_position"` - Constant regardless of position
  - `"worse_rest"` - Worse at night/rest
  - `"wave_attacks"` - Comes in waves/attacks
- **Clinical Value**: Mechanical vs inflammatory vs neuropathic

### redFlagScreen
- **Type**: Multi-select
- **Question**: "Any of these with your symptoms?"
- **Options**:
  - `"bladder_bowel"` - Loss of bladder/bowel control
  - `"groin_numbness"` - Numbness in groin/buttocks
  - `"fever_pain"` - Fever with back pain
  - `"night_pain"` - Pain waking from sleep
  - `"none"` - None of these
- **Clinical Value**: Emergency screening for cauda equina, infection, tumor

### whatHelped
- **Type**: Multi-select
- **Question**: "Has anything helped temporarily?"
- **Options**:
  - `"rest"` - Rest
  - `"movement"` - Movement/stretching
  - `"heat"` - Heat
  - `"ice"` - Ice
  - `"medication"` - Medication
  - `"massage"` - Massage
  - `"nothing"` - Nothing helps
  - `"other"` - Other → [text box]

### previousEpisodes
- **Type**: Select one
- **Question**: "Have you had this before?"
- **Options**:
  - `"first_time"` - First time
  - `"resolved_before"` - Had it, fully resolved
  - `"recurring"` - Recurring problem
  - `"chronic"` - Chronic/ongoing
- **Clinical Value**: Acute vs chronic patterns

---

## Implementation Notes

### Conditional Logic Examples
```javascript
// Physical - Show characteristics based on issue type
if (formData.issueType === 'pain') {
  showPainCharacteristics()
} else if (formData.issueType === 'weakness') {
  showWeaknessCharacteristics()
}

// Show text box when "Other" selected
if (selectedOptions.includes('other')) {
  showTextField('other_description')
}

// Multiple Issues - show order question
if (symptomTimeline === 'no_sequential') {
  showSymptomOrderField()
}
```

### Field Naming Convention
- Use snake_case for option values
- Use camelCase for field names
- Keep values short but descriptive

### Validation Rules
- Required fields must be answered before submission
- Multi-select fields should have at least one selection
- Text fields should have character limits (e.g., 500 chars)
- Conditional fields only required when shown

### Data Structure
All responses should be stored in `form_data` object with clear field names matching this document.

---

## 🍽️ Digestive Issues

### primarySymptom
- **Type**: Select one (Required)
- **Question**: "What's your main digestive concern?"
- **Options**:
  - `"pain_cramping"` - Pain or cramping
  - `"nausea_vomiting"` - Nausea or vomiting
  - `"bowel_changes"` - Bowel habit changes
  - `"bloating_gas"` - Bloating or gas
  - `"swallowing_issues"` - Difficulty swallowing
  - `"appetite_changes"` - Appetite changes
- **Clinical Value**: Differentiates upper GI (nausea, swallowing) from lower GI (bowel) from functional (bloating)

### bowelPattern
- **Type**: Select one
- **Question**: "Current bowel habits:"
- **Options**:
  - `"diarrhea_frequent"` - Diarrhea (>3/day)
  - `"constipation"` - Constipation (<3/week)
  - `"alternating"` - Alternating diarrhea/constipation
  - `"normal_painful"` - Normal frequency but painful
  - `"blood_mucus"` - Blood or mucus present
- **Clinical Value**: IBS patterns vs IBD vs infection vs malignancy screening

### timingRelationToFood
- **Type**: Select one
- **Question**: "Symptoms in relation to eating:"
- **Options**:
  - `"immediately_during"` - While eating or immediately after
  - `"30min_2hrs"` - 30 minutes to 2 hours after
  - `"hours_later"` - Several hours after eating
  - `"empty_stomach"` - Worse on empty stomach
  - `"no_relation"` - No relation to meals
- **Clinical Value**: Gastric (immediate) vs small bowel (30-120min) vs colon (hours) localization

### foodTriggers
- **Type**: Multi-select
- **Question**: "Which foods make it worse?"
- **Options**:
  - `"dairy"` - Dairy products
  - `"gluten_wheat"` - Gluten/wheat
  - `"fatty_fried"` - Fatty or fried foods
  - `"spicy"` - Spicy foods
  - `"alcohol_caffeine"` - Alcohol or caffeine
  - `"no_pattern"` - No clear pattern
- **Clinical Value**: Lactose intolerance, celiac, gallbladder, GERD patterns

### associatedGISymptoms
- **Type**: Multi-select
- **Question**: "Also experiencing:"
- **Options**:
  - `"weight_loss"` - Unintended weight loss
  - `"night_symptoms"` - Symptoms waking you at night
  - `"fever"` - Fever
  - `"fatigue"` - Extreme fatigue
  - `"joint_pain"` - Joint pain
- **Clinical Value**: Red flags for IBD, malignancy, systemic disease

---

## 🫁 Breathing & Chest

### breathingPattern
- **Type**: Select one (Required)
- **Question**: "How is your breathing affected?"
- **Options**:
  - `"cant_catch_breath"` - Can't catch my breath
  - `"rapid_shallow"` - Rapid, shallow breathing
  - `"wheezing"` - Wheezing or whistling
  - `"tight_chest"` - Chest feels tight
  - `"worse_lying_down"` - Worse when lying down
- **Clinical Value**: Asthma vs COPD vs heart failure vs anxiety patterns

### exertionImpact
- **Type**: Select one
- **Question**: "Breathing difficulty occurs:"
- **Options**:
  - `"at_rest"` - Even at rest
  - `"minimal_activity"` - With minimal activity (dressing, bathing)
  - `"moderate_activity"` - With moderate activity (walking)
  - `"strenuous_only"` - Only with strenuous activity
- **Clinical Value**: NYHA/MRC dyspnea scale for severity assessment

### chestSymptoms
- **Type**: Multi-select
- **Question**: "Chest symptoms include:"
- **Options**:
  - `"sharp_pain"` - Sharp, stabbing pain
  - `"pressure_squeezing"` - Pressure or squeezing
  - `"burning"` - Burning sensation
  - `"palpitations"` - Heart racing/skipping
  - `"cough"` - Cough (dry or productive)
- **Clinical Value**: Cardiac vs pulmonary vs GI vs musculoskeletal differentiation

### breathingTriggers
- **Type**: Multi-select
- **Question**: "Breathing worse with:"
- **Options**:
  - `"allergens"` - Dust, pollen, pets
  - `"cold_air"` - Cold air
  - `"stress_anxiety"` - Stress or anxiety
  - `"position_change"` - Position changes
  - `"no_trigger"` - No clear trigger
- **Clinical Value**: Allergic asthma vs exercise-induced vs panic disorder

### urgentScreen
- **Type**: Multi-select
- **Question**: "Any of these symptoms?"
- **Options**:
  - `"chest_pressure_pain"` - Chest pressure with sweating
  - `"blue_lips"` - Blue lips or fingernails
  - `"coughing_blood"` - Coughing up blood
  - `"leg_swelling"` - Leg swelling
  - `"none"` - None of these
- **Clinical Value**: MI, PE, pneumonia, heart failure red flags

---

## 🌸 Skin & Hair

### primaryConcern
- **Type**: Select one (Required)
- **Question**: "Main skin/hair issue:"
- **Options**:
  - `"rash"` - Rash or skin irritation
  - `"hair_loss"` - Hair loss or thinning
  - `"color_changes"` - Skin color changes
  - `"texture_changes"` - Texture changes (dry, scaly)
  - `"growths"` - New growths or moles
  - `"wounds_not_healing"` - Wounds not healing
- **Clinical Value**: Inflammatory vs infectious vs neoplastic vs systemic manifestation

### distribution
- **Type**: Select one
- **Question**: "Where is it located?"
- **Options**:
  - `"localized_one_area"` - One specific area
  - `"symmetric_both_sides"` - Both sides of body equally
  - `"spreading"` - Started small, now spreading
  - `"random_patches"` - Random patches
  - `"face_visible_areas"` - Face/visible areas mainly
- **Clinical Value**: Contact dermatitis vs psoriasis vs systemic patterns

### skinCharacteristics
- **Type**: Multi-select
- **Question**: "The affected area is:"
- **Options**:
  - `"itchy"` - Itchy
  - `"painful"` - Painful or tender
  - `"raised"` - Raised or bumpy
  - `"flaky_scaly"` - Flaky or scaly
  - `"oozing_crusting"` - Oozing or crusting
  - `"changing_size"` - Changing in size/color
- **Clinical Value**: Eczema vs psoriasis vs infection vs malignancy features

### hairSpecific
- **Type**: Select one (Conditional - if hair_loss selected)
- **Question**: "Hair loss pattern:"
- **Options**:
  - `"patches"` - Circular patches
  - `"overall_thinning"` - Overall thinning
  - `"receding"` - Receding hairline
  - `"sudden_clumps"` - Sudden loss in clumps
  - `"with_scalp_symptoms"` - With scalp itching/pain
- **Clinical Value**: Alopecia areata vs androgenic vs telogen effluvium

### skinTriggers
- **Type**: Multi-select
- **Question**: "Started after or worse with:"
- **Options**:
  - `"new_product"` - New product/cosmetic
  - `"sun_exposure"` - Sun exposure
  - `"stress"` - Stress period
  - `"medication"` - New medication
  - `"unknown"` - No clear trigger
- **Clinical Value**: Contact vs photosensitive vs drug reaction vs stress-related

---

## 🔄 Hormonal/Cycles

### biologicalSex
- **Type**: Select one (Required - determines next questions)
- **Question**: "Biological sex at birth:"
- **Options**:
  - `"female"` - Female
  - `"male"` - Male
  - `"prefer_not_say"` - Prefer not to say
- **Clinical Value**: Determines relevant hormonal questions and normal ranges

### FOR FEMALE/PREFER NOT TO SAY:

#### primaryHormonalConcernFemale
- **Type**: Select one
- **Question**: "Main hormonal concern:"
- **Options**:
  - `"irregular_periods"` - Irregular periods
  - `"heavy_painful_periods"` - Heavy or painful periods
  - `"no_periods"` - Missed/absent periods
  - `"menopause_symptoms"` - Menopause symptoms
  - `"pms_pmdd"` - PMS/PMDD symptoms
  - `"fertility_issues"` - Fertility concerns
  - `"other_hormonal"` - Other hormonal symptoms
- **Clinical Value**: PCOS vs thyroid vs prolactinoma vs menopause differentiation

#### cyclePattern
- **Type**: Select one
- **Question**: "Menstrual pattern:"
- **Options**:
  - `"regular_21_35"` - Regular (21-35 days)
  - `"irregular_unpredictable"` - Irregular/unpredictable
  - `"frequent_under21"` - Too frequent (<21 days)
  - `"infrequent_over35"` - Too infrequent (>35 days)
  - `"absent_3months"` - Absent for 3+ months
  - `"postmenopausal"` - Postmenopausal
- **Clinical Value**: Anovulation vs pregnancy vs hyperprolactinemia patterns

#### femaleHormonalSymptoms
- **Type**: Multi-select
- **Question**: "Experiencing:"
- **Options**:
  - `"hot_flashes"` - Hot flashes
  - `"night_sweats"` - Night sweats
  - `"mood_swings"` - Severe mood swings
  - `"breast_tenderness"` - Breast tenderness
  - `"pelvic_pain"` - Pelvic pain
  - `"vaginal_changes"` - Vaginal dryness/changes
  - `"weight_gain"` - Unexplained weight gain
  - `"acne"` - Hormonal acne
  - `"excess_hair"` - Excess facial/body hair
- **Clinical Value**: Estrogen deficiency vs excess, androgen excess patterns

#### femaleRelevantFactors
- **Type**: Multi-select
- **Question**: "Relevant factors:"
- **Options**:
  - `"pregnancy_possible"` - Could be pregnant
  - `"breastfeeding"` - Currently breastfeeding
  - `"birth_control"` - On birth control
  - `"trying_conceive"` - Trying to conceive
  - `"recent_pregnancy"` - Recent pregnancy/miscarriage
  - `"pcos_diagnosis"` - PCOS diagnosis
  - `"thyroid_issues"` - Thyroid problems
- **Clinical Value**: Pregnancy vs medication effect vs underlying condition

### FOR MALE:

#### primaryHormonalConcernMale
- **Type**: Select one
- **Question**: "Main concern:"
- **Options**:
  - `"low_energy"` - Low energy/fatigue
  - `"libido_changes"` - Low libido
  - `"erectile_issues"` - Erectile dysfunction
  - `"mood_changes"` - Mood changes/irritability
  - `"body_changes"` - Body composition changes
  - `"fertility"` - Fertility concerns
  - `"other_hormonal"` - Other hormonal symptoms
- **Clinical Value**: Hypogonadism vs metabolic vs psychological differentiation

#### maleHormonalSymptoms
- **Type**: Multi-select
- **Question**: "Experiencing:"
- **Options**:
  - `"decreased_muscle"` - Decreased muscle mass
  - `"increased_fat"` - Increased body fat
  - `"breast_tissue"` - Breast tissue development
  - `"hot_flashes"` - Hot flashes
  - `"decreased_body_hair"` - Decreased body/facial hair
  - `"testicular_changes"` - Testicular size changes
  - `"sleep_issues"` - Sleep disturbances
  - `"concentration"` - Poor concentration
  - `"depression"` - Depression
- **Clinical Value**: Primary vs secondary hypogonadism patterns

#### onsetPattern
- **Type**: Select one
- **Question**: "These changes:"
- **Options**:
  - `"gradual_months"` - Gradual over months
  - `"sudden_weeks"` - Sudden over weeks
  - `"years_slow"` - Very slow over years
  - `"after_event"` - After specific event/illness
- **Clinical Value**: Acute vs chronic, primary vs secondary causes

#### maleRelevantFactors
- **Type**: Multi-select
- **Question**: "Relevant factors:"
- **Options**:
  - `"testosterone_therapy"` - On testosterone therapy
  - `"anabolic_steroids"` - History of steroid use
  - `"testicular_injury"` - Previous testicular injury
  - `"chemotherapy"` - Previous chemotherapy
  - `"obesity"` - Significant weight gain
  - `"diabetes"` - Diabetes diagnosis
  - `"opioid_use"` - Chronic opioid use
- **Clinical Value**: Iatrogenic vs organic causes

### SHARED (Both sexes):

#### impactOnLife
- **Type**: Select one
- **Question**: "These symptoms:"
- **Options**:
  - `"mild_manageable"` - Mild, manageable
  - `"affecting_work"` - Affecting work/daily life
  - `"affecting_relationships"` - Affecting relationships
  - `"severe_disabling"` - Severe, disabling
- **Clinical Value**: Treatment urgency and approach determination

---

## 🧠 Neurological

### primaryNeuroSymptom
- **Type**: Select one (Required)
- **Question**: "Main neurological issue:"
- **Options**:
  - `"headaches"` - Headaches
  - `"dizziness"` - Dizziness/vertigo
  - `"numbness_tingling"` - Numbness or tingling
  - `"vision_changes"` - Vision changes
  - `"balance_coordination"` - Balance/coordination issues
  - `"seizure_fainting"` - Seizures or fainting
  - `"tremor"` - Tremor or shaking
- **Clinical Value**: Central vs peripheral, vascular vs structural differentiation

### headachePattern
- **Type**: Select one (Conditional - if headaches selected)
- **Question**: "Headache characteristics:"
- **Options**:
  - `"throbbing_one_side"` - Throbbing, one side (migraine)
  - `"band_around_head"` - Band around head (tension)
  - `"stabbing_ice_pick"` - Stabbing/ice pick
  - `"pressure_sinus"` - Pressure in face/sinuses
  - `"cluster_eye"` - Severe around one eye
  - `"thunderclap"` - Sudden, severe onset
- **Clinical Value**: Primary headache classification, red flag identification

### neurologicalTiming
- **Type**: Select one
- **Question**: "Symptoms occur:"
- **Options**:
  - `"constant"` - Constant
  - `"episodes_minutes"` - Episodes lasting minutes
  - `"episodes_hours"` - Episodes lasting hours
  - `"episodes_days"` - Episodes lasting days
  - `"specific_triggers"` - With specific triggers
  - `"random"` - Randomly
- **Clinical Value**: Episodic vs chronic, trigger identification

### associatedNeuroSymptoms
- **Type**: Multi-select
- **Question**: "Also experiencing:"
- **Options**:
  - `"weakness"` - Weakness
  - `"speech_changes"` - Speech changes
  - `"memory_confusion"` - Memory issues/confusion
  - `"vision_changes"` - Vision changes
  - `"sensitivity"` - Light/sound sensitivity
  - `"nausea"` - Nausea with symptoms
- **Clinical Value**: Migraine vs stroke vs MS vs tumor patterns

### neuroRedFlags
- **Type**: Multi-select
- **Question**: "Any of these symptoms?"
- **Options**:
  - `"worst_headache_ever"` - Worst headache of life
  - `"sudden_weakness"` - Sudden one-sided weakness
  - `"speech_difficulty"` - Difficulty speaking
  - `"vision_loss"` - Sudden vision loss
  - `"confusion"` - New confusion
  - `"seizure"` - Seizure activity
  - `"none"` - None of these
- **Clinical Value**: Stroke, SAH, status epilepticus emergency screening