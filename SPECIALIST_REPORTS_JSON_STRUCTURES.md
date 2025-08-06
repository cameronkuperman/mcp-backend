# Exact JSON Response Structures for All Specialist Reports

## Cardiology Report `/api/report/cardiology`

```json
{
  "report_id": "uuid",
  "report_type": "cardiology",
  "specialty": "cardiology",
  "generated_at": "2025-01-01T00:00:00Z",
  "report_data": {
    "executive_summary": {
      "one_page_summary": "Comprehensive cardiovascular evaluation...",
      "key_findings": ["Chest pain with exertional pattern", "Multiple cardiac risk factors"],
      "patterns_identified": ["Stable angina pattern", "Metabolic syndrome features"],
      "chief_complaints": ["Chest pain", "Shortness of breath"],
      "urgency_indicators": ["Exertional chest pain", "New onset symptoms"],
      "action_items": ["Urgent cardiology referral", "ECG and troponins"],
      "specialist_focus": "cardiology",
      "target_audience": "cardiologist"
    },
    "clinical_summary": {
      "chief_complaint": "Chest pain with exertion",
      "hpi": "45-year-old male with 3-month history of exertional chest pain...",
      "cardiovascular_risk_factors": ["Hypertension", "Diabetes", "Smoking"],
      "current_medications": ["Metformin", "Lisinopril"],
      "family_history": ["Father with MI at age 55"]
    },
    "cardiology_assessment": {
      "chest_pain_characteristics": {
        "quality": "Pressure-like",
        "location": "Substernal",
        "radiation": "Left arm",
        "duration": "5-10 minutes",
        "triggers": ["Exertion", "Emotional stress"],
        "relieving_factors": ["Rest", "Sublingual nitroglycerin"]
      },
      "associated_symptoms": ["Dyspnea", "Diaphoresis", "Nausea"],
      "cardiac_risk_factors": {
        "modifiable": ["Smoking - 20 pack years", "Diabetes - HbA1c 8.2%", "Hypertension"],
        "non_modifiable": ["Age", "Male gender", "Family history"]
      },
      "functional_capacity": {
        "mets": "4-6",
        "limitation": "Moderate - symptoms with 2 flights of stairs"
      }
    },
    "cardiologist_specific_findings": {
      "vital_signs_review": {
        "blood_pressure": "145/90",
        "heart_rate": "88 regular",
        "respiratory_rate": "16"
      },
      "physical_exam_findings": {
        "cardiac": "Regular rhythm, no murmurs",
        "vascular": "Equal pulses, no bruits",
        "pulmonary": "Clear to auscultation"
      },
      "ecg_interpretation_needed": true,
      "rhythm_assessment": "Regular",
      "murmur_assessment": "None detected"
    },
    "diagnostic_recommendations": {
      "immediate": [
        {"test": "12-lead ECG", "urgency": "STAT", "rationale": "Evaluate for ischemia"},
        {"test": "Troponin I", "urgency": "STAT", "rationale": "Rule out ACS"},
        {"test": "Basic metabolic panel", "urgency": "Today", "rationale": "Baseline"}
      ],
      "short_term": [
        {"test": "Stress echocardiogram", "timeframe": "Within 1 week", "rationale": "Evaluate for inducible ischemia"},
        {"test": "Coronary CTA", "timeframe": "If stress test equivocal", "rationale": "Anatomical evaluation"}
      ],
      "additional": [
        {"test": "Lipid panel", "rationale": "Cardiovascular risk stratification"},
        {"test": "HbA1c", "rationale": "Diabetes control"}
      ]
    },
    "treatment_recommendations": {
      "immediate_interventions": [
        "Aspirin 81mg daily",
        "Sublingual nitroglycerin PRN",
        "Activity restriction pending evaluation"
      ],
      "medical_optimization": {
        "antiplatelet": "Start aspirin 81mg daily",
        "statin": "High-intensity statin indicated",
        "beta_blocker": "Consider if CAD confirmed",
        "ace_inhibitor": "Already on lisinopril"
      },
      "lifestyle_modifications": [
        "Smoking cessation counseling",
        "Cardiac diet education",
        "Cardiac rehabilitation referral"
      ],
      "follow_up": {
        "cardiology": "Within 1-2 weeks",
        "primary_care": "After cardiology evaluation"
      }
    },
    "risk_stratification": {
      "clinical_impression": "Intermediate to high risk",
      "reasoning": "Multiple risk factors with typical angina",
      "disposition": "Outpatient evaluation acceptable if stable"
    },
    "clinical_scales": {
      "HEART_Score": {
        "total_score": 6,
        "risk_category": "Moderate",
        "components": {
          "history": 2,
          "ecg": 0,
          "age": 1,
          "risk_factors": 2,
          "troponin": 0
        },
        "mace_risk": "16.6%",
        "confidence": 0.85,
        "recommendation": "Admission for observation and stress testing"
      },
      "CHA2DS2_VASc": {
        "total_score": 3,
        "components": {
          "chf": 0,
          "hypertension": 1,
          "age_75": 0,
          "diabetes": 1,
          "stroke": 0,
          "vascular": 0,
          "age_65_74": 0,
          "sex": 1
        },
        "annual_stroke_risk": "3.2%",
        "confidence": 0.9,
        "anticoagulation": "Consider if AFib detected"
      },
      "Framingham_Risk": {
        "ten_year_risk": "18%",
        "risk_category": "Intermediate-High",
        "confidence": 0.8,
        "statin_benefit": "High-intensity statin indicated"
      }
    }
  },
  "status": "success"
}
```

## Neurology Report `/api/report/neurology`

```json
{
  "report_id": "uuid",
  "report_type": "neurology",
  "specialty": "neurology",
  "generated_at": "2025-01-01T00:00:00Z",
  "report_data": {
    "executive_summary": {
      "one_page_summary": "Comprehensive neurological evaluation...",
      "key_findings": ["Chronic migraines with aura", "Cognitive complaints"],
      "patterns_identified": ["Classic migraine pattern", "Possible medication overuse"],
      "chief_complaints": ["Severe headaches", "Memory problems"],
      "urgency_indicators": ["Progressive symptoms", "Focal neurological signs"],
      "action_items": ["MRI brain", "Neurology referral"],
      "specialist_focus": "neurology",
      "target_audience": "neurologist"
    },
    "clinical_summary": {
      "chief_complaint": "Worsening headaches and memory issues",
      "hpi": "32-year-old female with 5-year history of migraines...",
      "neurological_review": {
        "headaches": "Throbbing, unilateral, with visual aura",
        "seizures": "None reported",
        "weakness": "Transient during migraines",
        "sensory": "Perioral tingling with aura"
      }
    },
    "neurology_assessment": {
      "headache_characteristics": {
        "frequency": "3-4 per week",
        "duration": "4-72 hours",
        "quality": "Throbbing, pulsatile",
        "location": "Unilateral, alternating sides",
        "severity": "8/10",
        "aura": {
          "present": true,
          "type": "Visual - scintillating scotoma",
          "duration": "20-30 minutes"
        }
      },
      "triggers": ["Stress", "Sleep deprivation", "Certain foods", "Hormonal"],
      "associated_symptoms": ["Photophobia", "Phonophobia", "Nausea", "Vomiting"],
      "neurological_symptoms": {
        "motor": ["Transient weakness during attacks"],
        "sensory": ["Perioral paresthesias"],
        "cognitive": ["Word-finding difficulty", "Short-term memory issues"],
        "coordination": ["Mild ataxia during severe attacks"]
      },
      "medication_use": {
        "abortive": ["Sumatriptan >10 days/month"],
        "preventive": ["None currently"],
        "overuse_concern": true
      }
    },
    "neurologist_specific_findings": {
      "focal_deficits": "None between attacks",
      "cognitive_screen": "Mild executive dysfunction noted",
      "red_flags_absent": ["No papilledema", "No meningismus", "No fever"],
      "concerning_features": ["Increasing frequency", "Cognitive complaints", "Medication overuse"]
    },
    "diagnostic_recommendations": {
      "neuroimaging": {
        "mri_brain": {
          "urgency": "Within 2 weeks",
          "protocol": "With and without contrast",
          "rationale": "Rule out secondary causes, evaluate for white matter changes"
        }
      },
      "laboratory": [
        {"test": "ESR, CRP", "rationale": "Inflammatory markers"},
        {"test": "TSH", "rationale": "Thyroid dysfunction"},
        {"test": "Vitamin B12, folate", "rationale": "Reversible causes"}
      ],
      "specialized": [
        {"test": "EEG", "indication": "If seizure activity suspected"},
        {"test": "Lumbar puncture", "indication": "If elevated ICP suspected"}
      ]
    },
    "treatment_recommendations": {
      "acute_management": {
        "abortive": ["Limit triptans to <10 days/month", "Consider gepants"],
        "rescue": ["Prochlorperazine", "Ketorolac"],
        "setting": "Outpatient unless status migrainosus"
      },
      "preventive_therapy": {
        "first_line": ["Topiramate 25mg BID, titrate slowly", "Propranolol 80mg daily"],
        "alternatives": ["Amitriptyline", "Valproic acid", "Candesartan"],
        "cgrp_antagonists": "Consider if first-line fails"
      },
      "non_pharmacologic": [
        "Sleep hygiene counseling",
        "Stress management techniques",
        "Dietary trigger identification",
        "Regular exercise program"
      ],
      "medication_overuse": {
        "plan": "Gradual taper of sumatriptan",
        "bridge_therapy": "Short course of steroids",
        "prevention": "Start preventive before taper"
      }
    },
    "follow_up_plan": {
      "neurology": "4-6 weeks after starting preventive",
      "headache_diary": "Track frequency, triggers, medication use",
      "imaging_review": "At neurology appointment",
      "medication_adjustment": "Based on response and side effects"
    },
    "clinical_scales": {
      "MIDAS_Score": {
        "total_score": 28,
        "grade": "IV - Severe disability",
        "days_missed": {
          "work": 8,
          "household": 12,
          "social": 15
        },
        "confidence": 0.9,
        "interpretation": "Significant functional impairment",
        "reasoning": "Based on reported activity limitations"
      },
      "HIT6_Score": {
        "total_score": 68,
        "severity": "Severe impact",
        "confidence": 0.85,
        "components": {
          "pain": "Always",
          "daily_activities": "Very often",
          "wish_to_lie_down": "Always",
          "fatigue": "Very often",
          "irritability": "Often",
          "concentration": "Very often"
        }
      },
      "Cognitive_Screen": {
        "moca_estimate": 24,
        "domains_affected": ["Executive function", "Delayed recall"],
        "confidence": 0.7,
        "reasoning": "Based on reported symptoms, formal testing needed"
      }
    }
  },
  "status": "success"
}
```

## Dermatology Report `/api/report/dermatology`

```json
{
  "report_id": "uuid",
  "report_type": "dermatology",
  "specialty": "dermatology",
  "generated_at": "2025-01-01T00:00:00Z",
  "report_data": {
    "executive_summary": {
      "one_page_summary": "Comprehensive dermatological evaluation...",
      "key_findings": ["Suspicious pigmented lesion", "Chronic eczema"],
      "patterns_identified": ["Asymmetric melanocytic lesion", "Atopic dermatitis pattern"],
      "chief_complaints": ["Changing mole", "Itchy rash"],
      "urgency_indicators": ["ABCDE positive lesion"],
      "action_items": ["Urgent dermatology referral", "Possible biopsy needed"],
      "specialist_focus": "dermatology",
      "target_audience": "dermatologist"
    },
    "clinical_summary": {
      "chief_complaint": "Changing mole on back",
      "hpi": "45-year-old male noticed mole changing over 3 months...",
      "skin_history": {
        "previous_skin_cancer": "None",
        "sun_exposure": "Significant - outdoor worker",
        "sunburn_history": "Multiple blistering sunburns in childhood",
        "tanning_bed_use": "Never"
      }
    },
    "dermatology_assessment": {
      "primary_lesion": {
        "location": "Central back",
        "morphology": "Asymmetric pigmented macule",
        "size": "8mm x 6mm",
        "color": "Variegated brown and black",
        "borders": "Irregular",
        "symptoms": ["Occasional itching"]
      },
      "secondary_findings": [
        {
          "diagnosis": "Atopic dermatitis",
          "location": "Flexural areas",
          "severity": "Moderate",
          "duration": "Since childhood"
        }
      ],
      "skin_type": "Fitzpatrick type II",
      "total_body_nevus_count": ">50",
      "atypical_nevi": "Multiple"
    },
    "dermatologist_specific_findings": {
      "dermoscopy_indicated": true,
      "abcde_assessment": {
        "asymmetry": true,
        "border_irregularity": true,
        "color_variation": true,
        "diameter": ">6mm",
        "evolution": true,
        "overall_concern": "High"
      },
      "differential_diagnosis": [
        "Atypical nevus",
        "Melanoma in situ",
        "Seborrheic keratosis (less likely)"
      ]
    },
    "lesion_analysis": {
      "identified_lesions": [
        {
          "id": 1,
          "location": "Central back",
          "clinical_impression": "Atypical melanocytic lesion",
          "management": "Excisional biopsy recommended"
        }
      ],
      "risk_stratification": "High risk",
      "urgency": "Within 2-4 weeks"
    },
    "photo_documentation": {
      "available": true,
      "findings": "Asymmetric pigmented lesion with color variegation",
      "comparison": "No previous photos for comparison"
    },
    "diagnostic_recommendations": {
      "immediate": [
        {
          "procedure": "Excisional biopsy",
          "margins": "2-3mm",
          "urgency": "Within 2-4 weeks",
          "rationale": "Rule out melanoma"
        }
      ],
      "additional": [
        {
          "test": "Total body photography",
          "rationale": "Baseline for monitoring"
        },
        {
          "test": "Dermoscopy of atypical nevi",
          "rationale": "Risk stratification"
        }
      ]
    },
    "treatment_recommendations": {
      "suspicious_lesion": {
        "management": "Excisional biopsy with appropriate margins",
        "follow_up": "Based on pathology results",
        "referral": "Surgical dermatology or oncology if malignant"
      },
      "eczema_management": {
        "topical": [
          "Triamcinolone 0.1% ointment BID to affected areas",
          "Tacrolimus 0.1% ointment for face/folds"
        ],
        "moisturizers": "Thick emollients TID",
        "triggers": "Avoid harsh soaps, fragrances"
      },
      "preventive_measures": [
        "Sun protection education",
        "Monthly self-examinations",
        "Annual dermatology screening"
      ]
    },
    "surveillance_plan": {
      "frequency": "Every 6 months given multiple atypical nevi",
      "modality": "Full body exam with dermoscopy",
      "self_monitoring": "Monthly with ABCDE criteria",
      "photography": "Annual total body photography"
    },
    "patient_education": {
      "sun_safety": [
        "SPF 30+ daily",
        "Protective clothing",
        "Avoid peak UV hours"
      ],
      "warning_signs": [
        "New or changing moles",
        "Bleeding or non-healing lesions",
        "Symptoms in existing moles"
      ]
    },
    "clinical_differential": {
      "primary_diagnosis": "Atypical nevus vs early melanoma",
      "differential_diagnoses": [
        "Dysplastic nevus",
        "Melanoma in situ",
        "Compound nevus with atypia"
      ],
      "clinical_confidence": 0.75,
      "biopsy_necessity": "Required for definitive diagnosis"
    }
  },
  "status": "success"
}
```

## Psychiatry Report `/api/report/psychiatry`

```json
{
  "report_id": "uuid",
  "report_type": "psychiatry",
  "specialty": "psychiatry",
  "generated_at": "2025-01-01T00:00:00Z",
  "report_data": {
    "executive_summary": {
      "one_page_summary": "Comprehensive psychiatric evaluation...",
      "key_findings": ["Major depressive episode", "Generalized anxiety"],
      "patterns_identified": ["Chronic depression with anxiety features"],
      "chief_complaints": ["Depressed mood", "Anxiety", "Insomnia"],
      "action_items": ["Initiate antidepressant", "Therapy referral"],
      "specialist_focus": "psychiatry",
      "target_audience": "psychiatrist"
    },
    "clinical_summary": {
      "chief_complaint": "Worsening depression and anxiety",
      "hpi": "28-year-old female with 6-month history of low mood...",
      "psychiatric_history": {
        "previous_episodes": "One prior episode 3 years ago",
        "hospitalizations": "None",
        "suicide_attempts": "None",
        "current_treatment": "None"
      }
    },
    "psychiatry_assessment": {
      "mood_symptoms": {
        "depression": {
          "duration": "6 months",
          "severity": "Moderate to severe",
          "symptoms": [
            "Depressed mood",
            "Anhedonia",
            "Guilt",
            "Concentration difficulties",
            "Fatigue",
            "Sleep disturbance",
            "Appetite decrease"
          ],
          "functional_impact": "Missing work 2-3 days/month"
        },
        "anxiety": {
          "type": "Generalized",
          "duration": "Concurrent with depression",
          "symptoms": [
            "Excessive worry",
            "Restlessness",
            "Muscle tension",
            "Irritability"
          ]
        }
      },
      "sleep_pattern": {
        "insomnia_type": "Initial and middle",
        "hours_per_night": "4-5",
        "quality": "Poor, non-restorative"
      },
      "substance_use": {
        "alcohol": "Social only",
        "drugs": "Denies",
        "tobacco": "Never"
      }
    },
    "mental_status_exam": {
      "appearance": "Well-groomed but tired-appearing",
      "behavior": "Cooperative, good eye contact",
      "speech": "Normal rate and rhythm",
      "mood": "Depressed",
      "affect": "Constricted, mood-congruent",
      "thought_process": "Linear and goal-directed",
      "thought_content": "No SI/HI, no psychosis",
      "cognition": "Alert and oriented x3",
      "insight": "Good",
      "judgment": "Intact"
    },
    "safety_assessment": {
      "suicidal_ideation": {
        "current": "Denies",
        "passive": "Occasional thoughts life not worth living",
        "plan": "None",
        "intent": "None",
        "means": "No access to firearms"
      },
      "homicidal_ideation": "Denies",
      "risk_level": "Low",
      "protective_factors": [
        "Strong family support",
        "Future goals",
        "No prior attempts"
      ]
    },
    "diagnostic_formulation": {
      "primary_diagnosis": "Major Depressive Disorder, moderate, single episode",
      "secondary_diagnosis": "Generalized Anxiety Disorder",
      "differential": [
        "Adjustment disorder",
        "Bipolar disorder (screen negative)",
        "Thyroid dysfunction (needs labs)"
      ],
      "dsm5_codes": ["F32.1", "F41.1"]
    },
    "treatment_recommendations": {
      "pharmacotherapy": {
        "antidepressant": {
          "recommendation": "Sertraline 50mg daily",
          "rationale": "First-line SSRI, addresses both depression and anxiety",
          "titration": "Increase to 100mg after 2 weeks if tolerated"
        },
        "sleep": {
          "recommendation": "Trazodone 50mg qhs PRN",
          "alternative": "Sleep hygiene first"
        },
        "monitoring": "Check in 2 weeks for side effects"
      },
      "psychotherapy": {
        "modality": "Cognitive Behavioral Therapy",
        "frequency": "Weekly initially",
        "focus": "Depression and anxiety management"
      },
      "lifestyle": [
        "Regular exercise program",
        "Sleep hygiene education",
        "Stress reduction techniques",
        "Maintain social connections"
      ]
    },
    "laboratory_recommendations": [
      {"test": "TSH", "rationale": "Rule out thyroid dysfunction"},
      {"test": "CBC", "rationale": "Baseline before medication"},
      {"test": "CMP", "rationale": "Baseline metabolic panel"},
      {"test": "Vitamin D", "rationale": "Deficiency can worsen mood"}
    ],
    "follow_up_plan": {
      "psychiatry": "2 weeks for medication check",
      "therapy": "Start within 1-2 weeks",
      "primary_care": "Share treatment plan",
      "crisis_plan": "Emergency contacts provided"
    },
    "clinical_scales": {
      "PHQ9_Score": {
        "total_score": 16,
        "severity": "Moderately severe depression",
        "items": {
          "little_interest": 2,
          "feeling_down": 3,
          "sleep": 3,
          "tired": 2,
          "appetite": 2,
          "feeling_bad": 2,
          "concentration": 2,
          "moving_slowly": 0,
          "suicide": 0
        },
        "confidence": 0.95,
        "functional_impact": "Very difficult"
      },
      "GAD7_Score": {
        "total_score": 12,
        "severity": "Moderate anxiety",
        "items": {
          "feeling_nervous": 2,
          "cant_stop_worrying": 2,
          "worrying_too_much": 2,
          "trouble_relaxing": 2,
          "restless": 2,
          "irritable": 1,
          "afraid": 1
        },
        "confidence": 0.95
      },
      "MDQ_Screen": {
        "result": "Negative",
        "confidence": 0.9,
        "reasoning": "No manic/hypomanic symptoms endorsed"
      }
    },
    "prognosis": {
      "assessment": "Good with treatment",
      "factors_favorable": [
        "First episode",
        "Good insight",
        "Motivated for treatment",
        "Support system"
      ],
      "factors_unfavorable": [
        "Duration of untreated symptoms",
        "Comorbid anxiety"
      ]
    }
  },
  "status": "success"
}
```

## Gastroenterology Report `/api/report/gastroenterology`

```json
{
  "report_id": "uuid",
  "report_type": "gastroenterology",
  "specialty": "gastroenterology",
  "generated_at": "2025-01-01T00:00:00Z",
  "report_data": {
    "executive_summary": {
      "one_page_summary": "Comprehensive GI evaluation...",
      "key_findings": ["Chronic diarrhea", "Weight loss", "Abdominal pain"],
      "patterns_identified": ["Inflammatory bowel disease pattern"],
      "chief_complaints": ["Diarrhea", "Cramping", "Blood in stool"],
      "urgency_indicators": ["Bloody diarrhea", "Weight loss"],
      "action_items": ["Colonoscopy", "IBD workup"],
      "specialist_focus": "gastroenterology",
      "target_audience": "gastroenterologist"
    },
    "clinical_summary": {
      "chief_complaint": "Chronic diarrhea with blood",
      "hpi": "25-year-old with 3-month history of bloody diarrhea...",
      "gi_review": {
        "bowel_pattern": "6-8 loose stools daily",
        "blood": "Bright red blood mixed with stool",
        "pain": "Crampy, relieved by defecation",
        "weight_loss": "15 pounds in 3 months"
      }
    },
    "gastroenterology_assessment": {
      "gi_symptoms": {
        "diarrhea": {
          "frequency": "6-8 times daily",
          "consistency": "Loose to watery",
          "blood": "Present in most stools",
          "mucus": "Present",
          "urgency": "Severe",
          "nocturnal": true
        },
        "abdominal_pain": {
          "location": "LLQ primarily",
          "character": "Crampy",
          "timing": "Before and during BM",
          "severity": "6/10"
        },
        "associated": [
          "Tenesmus",
          "Fatigue",
          "Low-grade fever",
          "Joint pains"
        ]
      },
      "constitutional_symptoms": {
        "weight_loss": "15 lbs (10% body weight)",
        "appetite": "Decreased",
        "fever": "Low-grade intermittent"
      },
      "extraintestinal_manifestations": [
        "Arthralgia",
        "Possible erythema nodosum"
      ]
    },
    "gastroenterologist_specific_findings": {
      "alarm_features": [
        "Bloody diarrhea",
        "Weight loss >10%",
        "Nocturnal symptoms",
        "Anemia suspected"
      ],
      "physical_exam": {
        "abdomen": "Soft, tender LLQ, no masses",
        "rectal": "Indicated but deferred to specialist"
      },
      "differential_diagnosis": [
        "Ulcerative colitis",
        "Crohn's disease",
        "Infectious colitis (less likely given duration)"
      ]
    },
    "diagnostic_recommendations": {
      "endoscopy": {
        "colonoscopy": {
          "urgency": "Within 1-2 weeks",
          "prep": "Split dose",
          "biopsies": "Multiple from each segment"
        },
        "upper_endoscopy": "If Crohn's suspected"
      },
      "laboratory": {
        "inflammatory": [
          {"test": "CRP, ESR", "rationale": "Disease activity"},
          {"test": "Fecal calprotectin", "rationale": "Intestinal inflammation"}
        ],
        "infectious": [
          {"test": "Stool culture", "rationale": "Rule out infection"},
          {"test": "C. diff toxin", "rationale": "Rule out C. diff"},
          {"test": "Ova and parasites", "rationale": "If travel history"}
        ],
        "ibd_specific": [
          {"test": "pANCA, ASCA", "rationale": "IBD serologies"},
          {"test": "CBC with diff", "rationale": "Anemia, inflammation"},
          {"test": "CMP", "rationale": "Electrolytes, albumin"}
        ]
      },
      "imaging": {
        "ct_enterography": "If small bowel involvement suspected",
        "mri_pelvis": "If perianal disease"
      }
    },
    "treatment_recommendations": {
      "acute_management": {
        "symptom_control": [
          "Avoid antidiarrheals until infection ruled out",
          "Acetaminophen for pain (avoid NSAIDs)"
        ],
        "nutrition": [
          "Low residue diet",
          "Ensure adequate hydration",
          "Consider nutrition consult"
        ]
      },
      "ibd_treatment": {
        "induction": "5-ASA (mesalamine) if mild UC suspected",
        "moderate_severe": "Steroids may be needed",
        "maintenance": "Based on diagnosis and severity"
      },
      "monitoring": {
        "labs": "Weekly during acute phase",
        "symptoms": "Daily diary",
        "weight": "Weekly"
      }
    },
    "follow_up_plan": {
      "gastroenterology": "After colonoscopy for results",
      "primary_care": "Keep informed of workup",
      "nutrition": "If continued weight loss",
      "surgery": "Only if complications"
    },
    "patient_education": {
      "diet": [
        "Food diary to identify triggers",
        "Avoid high-fiber during flares",
        "Small frequent meals"
      ],
      "red_flags": [
        "Severe abdominal pain",
        "High fever",
        "Significant bleeding"
      ],
      "support": "IBD support group information"
    },
    "clinical_scales": {
      "Mayo_Score_Estimate": {
        "stool_frequency": 3,
        "rectal_bleeding": 2,
        "physician_global": 2,
        "endoscopy": "Pending",
        "total": 7,
        "severity": "Moderate",
        "confidence": 0.7,
        "note": "Endoscopy pending for complete score"
      },
      "Montreal_Classification": {
        "age_at_diagnosis": "A2 (17-40 years)",
        "location": "Pending endoscopy",
        "behavior": "Pending evaluation",
        "confidence": 0.6
      },
      "Harvey_Bradshaw_Estimate": {
        "general_wellbeing": 2,
        "abdominal_pain": 2,
        "liquid_stools": 6,
        "abdominal_mass": 0,
        "complications": 0,
        "total": 10,
        "activity": "Moderate",
        "confidence": 0.75
      }
    }
  },
  "status": "success"
}
```

## Endocrinology Report `/api/report/endocrinology`

```json
{
  "report_id": "uuid",
  "report_type": "endocrinology",
  "specialty": "endocrinology",
  "generated_at": "2025-01-01T00:00:00Z",
  "report_data": {
    "executive_summary": {
      "one_page_summary": "Comprehensive endocrine evaluation...",
      "key_findings": ["Uncontrolled diabetes", "Possible thyroid dysfunction"],
      "patterns_identified": ["Poor glycemic control", "Metabolic syndrome"],
      "chief_complaints": ["Fatigue", "Polyuria", "Weight gain"],
      "action_items": ["Adjust diabetes medications", "Thyroid testing"],
      "specialist_focus": "endocrinology",
      "target_audience": "endocrinologist"
    },
    "clinical_summary": {
      "chief_complaint": "Poor diabetes control and fatigue",
      "hpi": "52-year-old with T2DM x 8 years, worsening control...",
      "endocrine_history": {
        "diabetes": "Type 2, diagnosed 8 years ago",
        "thyroid": "No known disease",
        "other": "PCOS history"
      }
    },
    "endocrine_assessment": {
      "diabetes_assessment": {
        "duration": "8 years",
        "current_control": "Poor",
        "last_hba1c": "9.8%",
        "glucose_patterns": {
          "fasting": "180-220 mg/dL",
          "postprandial": "250-300 mg/dL",
          "bedtime": "200-240 mg/dL"
        },
        "complications_screening": {
          "retinopathy": "Last exam 2 years ago",
          "nephropathy": "Microalbuminuria present",
          "neuropathy": "Numbness in feet"
        }
      },
      "metabolic_symptoms": {
        "weight": "Gained 20 lbs in 6 months",
        "energy": "Severe fatigue",
        "polyuria": "5-6 times nightly",
        "polydipsia": "Drinking 3-4L daily"
      },
      "thyroid_symptoms": {
        "energy": "Fatigue despite sleep",
        "weight": "Difficulty losing weight",
        "temperature": "Cold intolerance",
        "skin": "Dry skin",
        "hair": "Hair thinning"
      }
    },
    "endocrinologist_specific_findings": {
      "medication_review": {
        "current": [
          "Metformin 1000mg BID",
          "Glipizide 10mg daily"
        ],
        "adherence": "Reports good adherence",
        "side_effects": "None reported"
      },
      "lifestyle_factors": {
        "diet": "High carbohydrate intake",
        "exercise": "Sedentary",
        "sleep": "Poor quality, likely OSA"
      },
      "physical_findings": {
        "bmi": 34.2,
        "waist_circumference": "42 inches",
        "acanthosis_nigricans": "Present",
        "thyroid": "Diffusely enlarged"
      }
    },
    "diagnostic_recommendations": {
      "diabetes_workup": [
        {"test": "Fasting glucose", "frequency": "Now and monthly"},
        {"test": "HbA1c", "frequency": "Every 3 months"},
        {"test": "Lipid panel", "rationale": "CV risk assessment"},
        {"test": "Urine microalbumin", "rationale": "Nephropathy screening"},
        {"test": "Creatinine, eGFR", "rationale": "Kidney function"}
      ],
      "thyroid_evaluation": [
        {"test": "TSH, Free T4", "urgency": "Within 1 week"},
        {"test": "TPO antibodies", "if": "TSH abnormal"},
        {"test": "Thyroid ultrasound", "indication": "Enlarged gland"}
      ],
      "additional": [
        {"test": "Vitamin D", "rationale": "Often low in diabetes"},
        {"test": "B12", "rationale": "On metformin"},
        {"test": "Sleep study", "rationale": "OSA screening"}
      ]
    },
    "treatment_recommendations": {
      "diabetes_management": {
        "medication_adjustment": {
          "add": "GLP-1 agonist (semaglutide)",
          "rationale": "Weight loss and glucose control",
          "alternative": "SGLT2 inhibitor if GLP-1 not tolerated"
        },
        "insulin_consideration": {
          "basal": "May need if HbA1c >10%",
          "starting_dose": "0.2 units/kg"
        }
      },
      "lifestyle_interventions": {
        "diet": [
          "Refer to diabetes educator",
          "Carb counting education",
          "Mediterranean diet pattern"
        ],
        "exercise": [
          "Start with 150 min/week walking",
          "Resistance training 2x/week"
        ],
        "weight": "Target 5-10% weight loss"
      },
      "complication_prevention": [
        "Annual eye exam",
        "Podiatry referral",
        "Statin therapy indicated",
        "ACE inhibitor for microalbuminuria"
      ]
    },
    "monitoring_plan": {
      "glucose": {
        "smbg": "Before meals and bedtime",
        "cgm": "Consider if hypoglycemia",
        "pattern": "Review at each visit"
      },
      "labs": {
        "hba1c": "3 months",
        "kidney": "6 months",
        "lipids": "Annually"
      },
      "complications": {
        "eyes": "Annual dilated exam",
        "feet": "Every visit",
        "kidneys": "Annual microalbumin"
      }
    },
    "clinical_scales": {
      "Diabetes_Control": {
        "hba1c_category": "Poor control",
        "estimated_average_glucose": "240 mg/dL",
        "time_in_range": "Likely <40%",
        "confidence": 0.9,
        "complications_risk": "High"
      },
      "FINDRISC_Score": {
        "total_score": "Not applicable (already diabetic)",
        "risk_factors": [
          "Obesity",
          "Sedentary",
          "Family history"
        ]
      },
      "Metabolic_Syndrome": {
        "criteria_met": 5,
        "components": [
          "Central obesity",
          "Hyperglycemia",
          "Hypertension",
          "Low HDL",
          "High triglycerides"
        ],
        "confidence": 0.95
      }
    }
  },
  "status": "success"
}
```

## Pulmonology Report `/api/report/pulmonology`

```json
{
  "report_id": "uuid",
  "report_type": "pulmonology",
  "specialty": "pulmonology",
  "generated_at": "2025-01-01T00:00:00Z",
  "report_data": {
    "executive_summary": {
      "one_page_summary": "Comprehensive pulmonary evaluation...",
      "key_findings": ["Chronic cough", "Dyspnea on exertion", "Wheezing"],
      "patterns_identified": ["Obstructive pattern", "Possible asthma-COPD overlap"],
      "chief_complaints": ["Shortness of breath", "Productive cough"],
      "urgency_indicators": ["Progressive dyspnea", "Reduced exercise tolerance"],
      "action_items": ["Pulmonary function tests", "Chest imaging"],
      "specialist_focus": "pulmonology",
      "target_audience": "pulmonologist"
    },
    "clinical_summary": {
      "chief_complaint": "Progressive shortness of breath",
      "hpi": "58-year-old former smoker with 6-month worsening dyspnea...",
      "pulmonary_history": {
        "smoking": "30 pack-years, quit 2 years ago",
        "occupational": "Construction worker - dust exposure",
        "childhood": "Recurrent bronchitis"
      }
    },
    "pulmonary_assessment": {
      "respiratory_symptoms": {
        "dyspnea": {
          "severity": "mMRC grade 2",
          "onset": "Gradual over 6 months",
          "pattern": "Exertional",
          "orthopnea": "None",
          "pnd": "None"
        },
        "cough": {
          "duration": "Chronic - years",
          "character": "Productive",
          "sputum": "White, moderate amount",
          "hemoptysis": "None"
        },
        "wheezing": {
          "frequency": "Daily",
          "triggers": ["Cold air", "Exercise", "Dust"],
          "nocturnal": "Occasional"
        }
      },
      "functional_impact": {
        "exercise_tolerance": "One flight of stairs",
        "adl_limitation": "Moderate",
        "work_impact": "Unable to do heavy lifting"
      },
      "exacerbation_history": {
        "frequency": "2-3 per year",
        "hospitalizations": "None",
        "steroid_courses": "2 in past year"
      }
    },
    "pulmonologist_specific_findings": {
      "physical_exam": {
        "respiratory_rate": "18",
        "oxygen_saturation": "94% on room air",
        "chest": "Decreased breath sounds, expiratory wheeze",
        "accessory_muscles": "Not used at rest"
      },
      "risk_assessment": {
        "copd_risk": "High - smoking history",
        "asthma_features": "Reversibility, atopy",
        "aco_possibility": "Consider overlap syndrome"
      }
    },
    "diagnostic_recommendations": {
      "pulmonary_function": {
        "spirometry": {
          "pre_post_bronchodilator": true,
          "urgency": "Within 2 weeks",
          "expected": "Obstructive pattern"
        },
        "lung_volumes": "If obstruction confirmed",
        "dlco": "Assess gas exchange"
      },
      "imaging": {
        "chest_xray": {
          "views": "PA and lateral",
          "urgency": "Within 1 week"
        },
        "hrct": {
          "indication": "If PFTs abnormal",
          "protocol": "Inspiratory and expiratory"
        }
      },
      "laboratory": [
        {"test": "CBC with eosinophils", "rationale": "Asthma phenotyping"},
        {"test": "Alpha-1 antitrypsin", "rationale": "Early COPD"},
        {"test": "Total IgE, specific IgE", "rationale": "Allergic component"}
      ]
    },
    "treatment_recommendations": {
      "bronchodilators": {
        "immediate": "Albuterol MDI 2 puffs QID PRN",
        "long_acting": {
          "laba": "Consider after PFTs",
          "lama": "If COPD confirmed"
        }
      },
      "anti_inflammatory": {
        "ics": "Low-medium dose if asthma component",
        "combination": "ICS/LABA if indicated"
      },
      "non_pharmacologic": [
        "Smoking cessation reinforcement",
        "Pulmonary rehabilitation referral",
        "Vaccination updates (flu, pneumonia, COVID)"
      ],
      "exacerbation_plan": {
        "action_plan": "Written plan provided",
        "rescue": "Prednisone 40mg x 5 days",
        "when_to_call": "Specific parameters given"
      }
    },
    "monitoring_plan": {
      "symptoms": "Daily diary",
      "peak_flow": "If asthma component",
      "spirometry": "Every 6-12 months",
      "imaging": "Annual CXR if COPD"
    },
    "clinical_scales": {
      "CAT_Score": {
        "total": 18,
        "impact": "Medium impact on life",
        "breakdown": {
          "cough": 3,
          "phlegm": 3,
          "chest_tightness": 2,
          "breathlessness": 4,
          "activities": 3,
          "confidence": 1,
          "sleep": 1,
          "energy": 1
        },
        "confidence": 0.9
      },
      "mMRC_Dyspnea": {
        "grade": 2,
        "description": "Walks slower than peers due to breathlessness",
        "confidence": 0.95
      },
      "ACT_Score": {
        "total": 19,
        "control": "Not well controlled",
        "confidence": 0.85,
        "components": {
          "symptom_frequency": 4,
          "night_symptoms": 4,
          "activity_limitation": 3,
          "rescue_use": 4,
          "self_rating": 4
        }
      },
      "GOLD_Estimate": {
        "group": "B",
        "rationale": "High symptoms, low exacerbation risk",
        "confidence": 0.7,
        "note": "Pending spirometry for confirmation"
      }
    }
  },
  "status": "success"
}
```

## Orthopedics Report `/api/report/orthopedics`

```json
{
  "report_id": "uuid",
  "report_type": "orthopedics",
  "specialty": "orthopedics",
  "generated_at": "2025-01-01T00:00:00Z",
  "report_data": {
    "executive_summary": {
      "one_page_summary": "Comprehensive orthopedic evaluation...",
      "key_findings": ["Chronic knee pain", "Mechanical symptoms", "Functional limitation"],
      "patterns_identified": ["Degenerative joint disease", "Possible meniscal tear"],
      "chief_complaints": ["Right knee pain", "Swelling", "Locking"],
      "action_items": ["MRI knee", "Orthopedic referral", "PT evaluation"],
      "specialist_focus": "orthopedics",
      "target_audience": "orthopedist"
    },
    "clinical_summary": {
      "chief_complaint": "Right knee pain with locking",
      "hpi": "45-year-old with 3-month history of right knee pain after twisting injury...",
      "injury_timeline": [
        {
          "date": "2024-10-15",
          "event": "Twisted knee playing tennis",
          "mechanism": "Pivoting motion",
          "severity": "Immediate pain and swelling",
          "treatment": "RICE, NSAIDs"
        }
      ]
    },
    "orthopedic_assessment": {
      "affected_joints": ["Right knee"],
      "pain_characteristics": {
        "location": "Medial joint line",
        "quality": "Sharp with movement, aching at rest",
        "timing": "Worse with weight bearing and stairs",
        "severity": "6/10 average, 8/10 with locking",
        "radiation": "None"
      },
      "mechanical_symptoms": {
        "locking": "2-3 times per week",
        "catching": "Daily",
        "instability": "Occasional giving way",
        "stiffness": "Morning stiffness 20 minutes",
        "swelling": "Mild persistent effusion"
      },
      "functional_limitations": {
        "ambulation": "Limited to 30 minutes",
        "stairs": "One step at a time",
        "activities": ["Unable to run", "Difficulty squatting"],
        "work_impact": "Modified duties"
      }
    },
    "orthopedist_specific_findings": {
      "injury_mechanism": {
        "traumatic": "Twisting injury during sports",
        "overuse": "Not primary",
        "degenerative": "Possible underlying OA"
      },
      "red_flags": {
        "present": [],
        "absent": ["Fever", "Night pain", "Constitutional symptoms"]
      },
      "previous_treatments": {
        "conservative": ["NSAIDs", "Ice", "Activity modification"],
        "surgical": ["None"],
        "response": "Minimal improvement"
      }
    },
    "diagnostic_recommendations": {
      "imaging": {
        "xrays": {
          "views": "AP, lateral, sunrise, standing",
          "rationale": "Assess joint space, alignment"
        },
        "mri": {
          "indicated": "yes",
          "region": "Right knee without contrast",
          "rationale": "Evaluate menisci, ligaments, cartilage"
        },
        "ct": "Not indicated"
      },
      "laboratory": [
        {
          "test": "If effusion tapped: cell count, crystals",
          "indication": "Only if inflammatory arthritis suspected"
        }
      ],
      "other": []
    },
    "treatment_recommendations": {
      "conservative_management": {
        "immediate": [
          "Continue activity modification",
          "Ice after activity",
          "Knee sleeve for support"
        ],
        "medications": [
          {
            "class": "NSAIDs",
            "specific": "Naproxen 500mg BID with food",
            "duration": "2-3 weeks"
          }
        ],
        "physical_therapy": {
          "focus": "Quadriceps strengthening, ROM, proprioception",
          "frequency": "2-3x/week for 6 weeks",
          "specific_exercises": [
            "Straight leg raises",
            "Mini squats",
            "Balance training"
          ]
        }
      },
      "injection_options": {
        "corticosteroid": {
          "location": "Intra-articular",
          "indication": "If PT fails"
        },
        "viscosupplementation": "Consider if OA confirmed",
        "prp": "Limited evidence"
      },
      "surgical_considerations": {
        "indicated": "If conservative treatment fails",
        "procedure_options": [
          "Arthroscopic meniscectomy",
          "Meniscal repair if tear amenable"
        ],
        "timing": "After 3-6 months conservative treatment"
      }
    },
    "rehabilitation_plan": {
      "phase_1": {
        "goals": "Reduce pain and swelling, protect knee",
        "restrictions": ["No running", "No pivoting sports"],
        "duration": "2-4 weeks"
      },
      "phase_2": {
        "goals": "Restore full ROM, begin strengthening",
        "activities": ["Stationary bike", "Pool exercises"],
        "progression_criteria": "Pain <3/10, minimal swelling"
      },
      "return_to_activity": {
        "timeline": "3-6 months depending on treatment",
        "milestones": [
          "Full ROM",
          "Strength 80% of unaffected side",
          "No mechanical symptoms"
        ],
        "prevention": "Maintenance exercises, proper warm-up"
      }
    },
    "follow_up_plan": {
      "orthopedic_visit": "2-4 weeks with MRI results",
      "imaging_followup": "MRI within 2 weeks",
      "therapy_progress": "Reassess at 6 weeks",
      "surgical_decision": "Based on MRI and response to PT"
    },
    "clinical_scales": {
      "Oswestry_Disability_Index": {
        "calculated": "N/A - knee specific",
        "confidence": 0,
        "category": "Use KOOS instead",
        "reasoning": "ODI is for back pain",
        "sections": {},
        "missing_data": ["All - wrong scale for knee"]
      },
      "KOOS": {
        "calculated": "Yes",
        "confidence": 0.85,
        "subscales": {
          "pain": 65,
          "symptoms": 60,
          "adl": 70,
          "sport_rec": 40,
          "qol": 45
        },
        "interpretation": "Moderate impact across all domains",
        "reasoning": "Based on reported limitations in daily activities and sports"
      },
      "Lysholm_Knee_Score": {
        "total": 68,
        "category": "Fair",
        "confidence": 0.8,
        "components": {
          "limp": 3,
          "support": 5,
          "locking": 6,
          "instability": 20,
          "pain": 15,
          "swelling": 6,
          "stairs": 6,
          "squatting": 2
        }
      },
      "Pain_Disability": {
        "functional_score": "Moderate disability",
        "work_impact": "Modified duties",
        "adl_impact": "Independent with modifications",
        "confidence": 0.9
      }
    }
  },
  "status": "success"
}
```

## Rheumatology Report `/api/report/rheumatology`

```json
{
  "report_id": "uuid",
  "report_type": "rheumatology",
  "specialty": "rheumatology",
  "generated_at": "2025-01-01T00:00:00Z",
  "report_data": {
    "executive_summary": {
      "one_page_summary": "Comprehensive rheumatologic evaluation...",
      "key_findings": ["Symmetric joint pain", "Morning stiffness >1hr", "Fatigue"],
      "patterns_identified": ["Inflammatory arthritis pattern", "Possible RA"],
      "chief_complaints": ["Joint pain", "Swelling", "Stiffness"],
      "action_items": ["Rheumatoid panel", "Joint imaging", "DMARDs consideration"],
      "specialist_focus": "rheumatology",
      "target_audience": "rheumatologist"
    },
    "clinical_summary": {
      "chief_complaint": "Bilateral hand pain and swelling",
      "hpi": "38-year-old female with 4-month history of symmetric joint pain...",
      "symptom_evolution": [
        {
          "date": "2024-09-01",
          "joints_affected": ["MCPs", "PIPs bilateral"],
          "pattern": "Symmetric",
          "associated_symptoms": ["Fatigue", "Low-grade fever"]
        }
      ]
    },
    "rheumatologic_assessment": {
      "joint_involvement": {
        "pattern": "Symmetric polyarticular",
        "small_joints": ["MCPs 2-4", "PIPs 2-4", "Wrists bilateral"],
        "large_joints": ["Knees bilateral"],
        "distribution": "Polyarticular (>5 joints)"
      },
      "inflammatory_markers": {
        "morning_stiffness": "90 minutes",
        "inflammatory_pattern": "Present",
        "improvement_with_activity": "Yes"
      },
      "systemic_features": {
        "constitutional": ["Fatigue", "Low-grade fever", "5 lb weight loss"],
        "extra_articular": ["Dry eyes", "No rash", "No lung symptoms"],
        "serologies_needed": ["RF", "Anti-CCP", "ANA", "ESR", "CRP"]
      }
    },
    "rheumatologist_specific_findings": {
      "disease_classification": {
        "primary_consideration": "Rheumatoid arthritis",
        "differential": ["Psoriatic arthritis", "SLE", "Viral arthritis"],
        "criteria_met": ["Morning stiffness >1hr", "Symmetric arthritis", "3+ joint areas"],
        "criteria_missing": ["Serologies pending", "Radiographs needed"]
      },
      "disease_activity": {
        "current_activity": "Moderate to high",
        "trajectory": "Progressive over 4 months",
        "prognostic_factors": ["Young age", "Polyarticular", "Functional impact"]
      },
      "comorbidities": {
        "cardiovascular_risk": "Assess baseline",
        "osteoporosis_risk": "Screen if starting steroids",
        "infection_risk": "Screen before immunosuppression"
      }
    },
    "diagnostic_recommendations": {
      "laboratory": {
        "immediate": [
          {
            "test": "RF, anti-CCP antibodies",
            "rationale": "RA diagnosis and prognosis"
          },
          {
            "test": "CBC, CMP, ESR, CRP",
            "rationale": "Inflammation and baseline"
          },
          {
            "test": "ANA with reflex",
            "rationale": "Rule out SLE"
          }
        ],
        "additional": [
          {
            "test": "Hepatitis B/C",
            "indication": "Before DMARD therapy"
          },
          {
            "test": "TB screening",
            "indication": "Before biologics"
          }
        ]
      },
      "imaging": {
        "xrays": {
          "joints": "Hands, feet, chest",
          "purpose": "Baseline erosions, lung disease"
        },
        "ultrasound": {
          "indication": "Detect subclinical synovitis",
          "joints": "Most affected joints"
        },
        "mri": "If X-rays normal but high suspicion"
      }
    },
    "treatment_recommendations": {
      "immediate_therapy": {
        "symptomatic": [
          {
            "medication": "Naproxen 500mg BID",
            "monitoring": "Renal function, GI symptoms"
          }
        ],
        "bridge_therapy": {
          "corticosteroids": "Prednisone 15mg daily",
          "duration": "Until DMARD effective",
          "taper_plan": "Over 8-12 weeks"
        }
      },
      "dmard_therapy": {
        "conventional": [
          {
            "drug": "Methotrexate",
            "starting_dose": "15mg weekly",
            "folic_acid": "1mg daily",
            "monitoring": "CBC, LFTs monthly x3 then q3mo"
          }
        ],
        "combination": "Add hydroxychloroquine if partial response",
        "biologic_criteria": "If inadequate response to MTX at 3 months"
      },
      "supportive_care": [
        "Occupational therapy for joint protection",
        "Physical therapy for exercises",
        "Calcium/Vitamin D supplementation"
      ]
    },
    "monitoring_plan": {
      "disease_activity": {
        "frequency": "Every 3 months initially",
        "measures": ["DAS28", "CDAI", "Joint counts"],
        "target": "Remission or low disease activity"
      },
      "medication_monitoring": {
        "methotrexate": ["CBC, CMP, LFTs"],
        "frequency": "Monthly x3, then q3months",
        "annual": ["CXR", "Eye exam if on HCQ"]
      },
      "comorbidity_screening": {
        "cardiovascular": "Annual lipids, BP monitoring",
        "bone_health": "DEXA if on steroids >3 months",
        "malignancy": "Age-appropriate screening"
      }
    },
    "patient_education": {
      "disease_understanding": [
        "Chronic but treatable condition",
        "Importance of early treatment",
        "Goal is remission"
      ],
      "medication_counseling": [
        "DMARD importance and timeline",
        "Side effect monitoring",
        "Contraception if childbearing age"
      ],
      "lifestyle": [
        "Smoking cessation critical",
        "Regular exercise",
        "Mediterranean diet"
      ]
    },
    "clinical_scales": {
      "DAS28_Estimate": {
        "tender_joints": 8,
        "swollen_joints": 6,
        "esr": "Pending",
        "patient_global": 60,
        "calculated_score": "Pending labs",
        "activity": "Likely high",
        "confidence": 0.7,
        "note": "Need ESR for complete calculation"
      },
      "CDAI": {
        "tender_joints": 8,
        "swollen_joints": 6,
        "patient_global": 6,
        "provider_global": 6,
        "total": 26,
        "activity": "High disease activity",
        "confidence": 0.85
      },
      "HAQ-DI_Estimate": {
        "score": 1.25,
        "category": "Moderate disability",
        "confidence": 0.8,
        "affected_domains": [
          "Dressing",
          "Gripping",
          "Activities"
        ]
      },
      "ACR_EULAR_Criteria": {
        "score": 6,
        "classification": "Probable RA (pending serology)",
        "points": {
          "joint_involvement": 3,
          "symptom_duration": 1,
          "acute_phase": "Pending",
          "serology": "Pending"
        },
        "confidence": 0.75,
        "meets_criteria": "Pending serology"
      }
    }
  },
  "status": "success"
}
```

## Primary Care Report `/api/report/primary-care`

```json
{
  "report_id": "uuid",
  "report_type": "primary_care",
  "specialty": "primary-care",
  "generated_at": "2025-01-01T00:00:00Z",
  "report_data": {
    "clinical_summary": {
      "chief_complaints": ["Annual physical", "Fatigue", "Weight gain"],
      "hpi": "45-year-old male presents for annual exam, reports 6-month history of fatigue...",
      "review_of_systems": {
        "constitutional": ["Fatigue", "10 lb weight gain", "No fever"],
        "cardiovascular": ["No chest pain", "Occasional palpitations"],
        "respiratory": ["No cough", "Mild DOE with stairs"],
        "gastrointestinal": ["Good appetite", "Regular BMs"],
        "genitourinary": ["Nocturia 1-2x"],
        "musculoskeletal": ["Morning stiffness 10 min"],
        "neurological": ["No headaches", "Occasional dizziness"],
        "psychiatric": ["Work stress", "Good sleep"],
        "endocrine": ["Increased thirst", "No temperature intolerance"],
        "dermatologic": ["No rashes", "Dry skin"]
      }
    },
    "preventive_care_gaps": {
      "screening_due": [
        "Colonoscopy - due at age 45",
        "Lipid panel - overdue by 2 years",
        "Diabetes screening - due now"
      ],
      "immunizations_needed": [
        "Flu vaccine - seasonal",
        "Tdap booster - due",
        "COVID booster - eligible"
      ],
      "health_maintenance": [
        "Dental cleaning - overdue",
        "Eye exam - recommend baseline",
        "Skin cancer screening"
      ]
    },
    "chronic_disease_assessment": {
      "identified_conditions": [
        {
          "condition": "Hypertension",
          "control_status": "Well-controlled",
          "last_evaluation": "6 months ago",
          "management_gaps": ["Home BP monitoring needed"]
        },
        {
          "condition": "Prediabetes",
          "control_status": "Newly identified",
          "last_evaluation": "Today - A1c 6.2%",
          "management_gaps": ["Lifestyle counseling", "Repeat A1c in 3 months"]
        }
      ],
      "risk_factors": {
        "cardiovascular": [
          "Family history - father MI at 58",
          "Sedentary lifestyle",
          "BMI 29.5"
        ],
        "metabolic": [
          "Central adiposity",
          "Prediabetes",
          "Sedentary"
        ],
        "cancer": [
          "Family history - mother breast cancer",
          "No current screening"
        ]
      }
    },
    "medication_reconciliation": {
      "current_medications": [
        "Lisinopril 10mg daily",
        "Aspirin 81mg daily"
      ],
      "adherence_concerns": ["Reports occasional missed doses"],
      "potential_interactions": ["None identified"]
    },
    "specialist_coordination": {
      "current_specialists": ["None"],
      "recommended_referrals": [
        {
          "specialty": "Endocrinology",
          "reason": "Prediabetes with metabolic syndrome",
          "urgency": "routine",
          "pre_referral_workup": ["Lipid panel", "TSH", "Vitamin D"]
        }
      ],
      "care_gaps": ["No established specialists"]
    },
    "diagnostic_plan": {
      "laboratory": [
        {
          "test": "Comprehensive metabolic panel",
          "rationale": "Annual screening",
          "frequency": "Annual"
        },
        {
          "test": "Lipid panel",
          "rationale": "CV risk, overdue",
          "frequency": "Every 5 years"
        },
        {
          "test": "TSH",
          "rationale": "Fatigue evaluation",
          "frequency": "One-time"
        }
      ],
      "imaging": ["None indicated"],
      "screening": [
        "Schedule colonoscopy",
        "PSA discussion at next visit"
      ]
    },
    "health_optimization": {
      "lifestyle_counseling": {
        "diet": [
          "Mediterranean diet pattern",
          "Reduce processed foods",
          "Portion control"
        ],
        "exercise": [
          "150 min moderate exercise/week",
          "Start with walking 30 min daily",
          "Add resistance training 2x/week"
        ],
        "sleep": [
          "Sleep hygiene review",
          "Consistent sleep schedule",
          "Limit screens before bed"
        ],
        "stress": [
          "Mindfulness apps recommended",
          "Work-life balance discussion",
          "Consider counseling"
        ]
      },
      "behavioral_health": {
        "mood_screening": "PHQ-2 negative",
        "substance_use": "AUDIT-C negative",
        "support_resources": ["EAP through work available"]
      }
    },
    "care_plan_summary": {
      "immediate_actions": [
        "Order overdue labs",
        "Schedule colonoscopy",
        "Update immunizations"
      ],
      "short_term_goals": [
        "Lose 5-10 lbs in 3 months",
        "Establish exercise routine",
        "Improve A1c to <5.7%"
      ],
      "long_term_goals": [
        "Achieve BMI <25",
        "Prevent diabetes progression",
        "Optimize CV risk factors"
      ],
      "follow_up_schedule": {
        "next_visit": "3 months for diabetes recheck",
        "monitoring_plan": "A1c q3months until stable"
      }
    },
    "patient_engagement": {
      "strengths": [
        "Motivated to improve health",
        "Good insurance coverage",
        "Supportive family"
      ],
      "barriers": [
        "Long work hours",
        "Limited exercise experience",
        "Stress eating pattern"
      ],
      "education_priorities": [
        "Prediabetes management",
        "Exercise prescription",
        "Preventive care importance"
      ]
    }
  },
  "status": "success"
}
```

## Nephrology Report `/api/report/nephrology`

```json
{
  "report_id": "uuid",
  "report_type": "nephrology",
  "specialty": "nephrology",
  "generated_at": "2025-01-01T00:00:00Z",
  "report_data": {
    "executive_summary": {
      "one_page_summary": "Comprehensive nephrology evaluation...",
      "key_findings": ["Stage 3 CKD", "Proteinuria", "Hypertension"],
      "patterns_identified": ["Diabetic nephropathy pattern"],
      "chief_complaints": ["Leg swelling", "Fatigue"],
      "action_items": ["Optimize BP control", "Start ACE/ARB", "Dietary counseling"],
      "specialist_focus": "nephrology",
      "target_audience": "nephrologist"
    },
    "clinical_summary": {
      "chief_complaint": "Worsening kidney function",
      "hpi": "62-year-old with diabetes presenting with declining eGFR...",
      "risk_factors": ["Diabetes x15 years", "Hypertension x10 years", "Family history"]
    },
    "nephrology_assessment": {
      "renal_symptoms": {
        "urinary_changes": ["Foamy urine", "Nocturia 3x", "No hematuria"],
        "edema": ["Bilateral ankle edema", "2+ pitting", "Worse by evening"],
        "systemic": ["Fatigue", "Poor appetite", "No pruritus yet"]
      },
      "blood_pressure": {
        "control": "Uncontrolled",
        "medications": ["Amlodipine 10mg", "Metoprolol 50mg BID"],
        "target": "<130/80 for CKD"
      },
      "volume_status": {
        "assessment": "Mild hypervolemia",
        "clinical_signs": ["Edema", "BP elevated", "No JVD"]
      }
    },
    "diagnostic_recommendations": {
      "laboratory": {
        "immediate": [
          {"test": "BUN, creatinine, eGFR", "rationale": "kidney function"},
          {"test": "Urinalysis with microscopy", "rationale": "proteinuria, hematuria"},
          {"test": "Urine protein/creatinine ratio", "rationale": "quantify proteinuria"}
        ],
        "additional": [
          {"test": "Renal ultrasound", "indication": "size, obstruction"},
          {"test": "24-hour urine", "indication": "if needed for clearance"}
        ]
      }
    },
    "treatment_recommendations": {
      "ckd_management": {
        "blood_pressure": {"target": "<130/80", "medications": "Add ACE/ARB"},
        "proteinuria": {"target": "reduce by 30-50%", "interventions": ["ACE/ARB", "SGLT2i"]},
        "mineral_bone": {"phosphate_control": "diet restriction", "vitamin_d": "check level"}
      },
      "acute_issues": {
        "volume": "Furosemide 20mg daily",
        "electrolytes": "Monitor potassium with ACE",
        "uremia": "Not present currently"
      },
      "lifestyle": {
        "diet": ["Low sodium <2g/day", "Moderate protein 0.8g/kg", "Potassium monitoring"],
        "fluid": "No restriction currently",
        "nephrotoxins": ["Avoid NSAIDs", "Contrast precautions"]
      }
    },
    "clinical_scales": {
      "CKD_Staging": {
        "estimated_gfr": "42 mL/min/1.73m²",
        "ckd_stage": "G3a",
        "albuminuria_category": "A2 (moderate)",
        "confidence": 0.9,
        "reasoning": "Based on labs and clinical presentation",
        "prognosis": "Moderate risk of progression"
      },
      "Volume_Assessment": {
        "status": "Mild hypervolemia",
        "confidence": 0.85,
        "clinical_basis": ["Pitting edema", "Elevated BP", "Weight gain 5 lbs"]
      }
    }
  },
  "status": "success"
}
```

## Urology Report `/api/report/urology`

```json
{
  "report_id": "uuid",
  "report_type": "urology",
  "specialty": "urology",
  "generated_at": "2025-01-01T00:00:00Z",
  "report_data": {
    "executive_summary": {
      "one_page_summary": "Comprehensive urologic evaluation...",
      "key_findings": ["BPH symptoms", "Nocturia", "Weak stream"],
      "patterns_identified": ["Obstructive pattern", "Irritative symptoms"],
      "chief_complaints": ["Frequent urination", "Weak stream", "Nocturia"],
      "action_items": ["PSA testing", "Uroflowmetry", "Medical therapy"],
      "specialist_focus": "urology",
      "target_audience": "urologist"
    },
    "clinical_summary": {
      "chief_complaint": "Worsening urinary symptoms",
      "hpi": "68-year-old male with progressive LUTS over 2 years...",
      "review_of_systems": {
        "lower_urinary_tract": ["Frequency q2h", "Nocturia 4x", "Weak stream"],
        "pain": ["No dysuria", "Mild suprapubic fullness"],
        "sexual_function": ["Decreased libido", "Mild ED"]
      }
    },
    "urology_assessment": {
      "luts_characterization": {
        "storage_symptoms": ["Frequency", "Urgency", "Nocturia 4x"],
        "voiding_symptoms": ["Hesitancy", "Weak stream", "Straining", "Intermittency"],
        "post_micturition": ["Incomplete emptying", "Post-void dribbling"]
      },
      "pain_assessment": {
        "location": ["Mild suprapubic"],
        "timing": "With full bladder",
        "severity": "2/10"
      },
      "sexual_function": {
        "erectile_function": "Mild ED",
        "ejaculatory_function": "Normal",
        "libido": "Decreased"
      }
    },
    "diagnostic_recommendations": {
      "laboratory": [
        {"test": "Urinalysis and culture", "rationale": "infection, hematuria"},
        {"test": "PSA", "indication": "BPH/cancer screening"},
        {"test": "Creatinine", "rationale": "renal function"}
      ],
      "imaging": [
        {"test": "Renal/bladder ultrasound", "indication": "obstruction, PVR"},
        {"test": "Post-void residual", "indication": "retention assessment"}
      ],
      "specialized": [
        {"test": "Uroflowmetry", "indication": "objective flow assessment"},
        {"test": "Cystoscopy", "indication": "if hematuria or failed medical therapy"}
      ]
    },
    "treatment_recommendations": {
      "medical_therapy": {
        "alpha_blockers": {"indication": "First-line for BPH", "options": ["Tamsulosin 0.4mg daily"]},
        "5ari": {"indication": "If prostate >40g", "options": ["Consider if PSA elevated"]},
        "anticholinergics": {"indication": "If storage symptoms predominate", "cautions": "Check PVR first"}
      },
      "behavioral": {
        "fluid_management": "Limit evening fluids",
        "bladder_training": "Timed voiding",
        "pelvic_floor": "If post-void dribbling"
      },
      "surgical_options": {
        "indications": ["Failed medical therapy", "Retention", "Complications"],
        "procedures": ["TURP", "Laser therapy"]
      }
    },
    "clinical_scales": {
      "IPSS": {
        "total_score": 18,
        "severity": "Moderate symptoms",
        "confidence": 0.9,
        "symptom_breakdown": {
          "incomplete_emptying": 3,
          "frequency": 3,
          "intermittency": 2,
          "urgency": 2,
          "weak_stream": 3,
          "straining": 2,
          "nocturia": "3 (4 times)"
        },
        "qol_score": 4,
        "reasoning": "Based on detailed symptom history"
      },
      "Bladder_Diary": {
        "daytime_frequency": "8-10 voids",
        "nocturia": "4 times",
        "urgency_episodes": "2-3 daily",
        "incontinence": "None"
      }
    }
  },
  "status": "success"
}
```

## Gynecology Report `/api/report/gynecology`

```json
{
  "report_id": "uuid",
  "report_type": "gynecology",
  "specialty": "gynecology",
  "generated_at": "2025-01-01T00:00:00Z",
  "report_data": {
    "executive_summary": {
      "one_page_summary": "Comprehensive gynecologic evaluation...",
      "key_findings": ["Irregular menses", "Heavy bleeding", "Possible PCOS"],
      "patterns_identified": ["Anovulatory cycles", "Hyperandrogenism"],
      "chief_complaints": ["Irregular periods", "Heavy bleeding", "Acne"],
      "action_items": ["Hormonal workup", "Pelvic ultrasound", "OCPs"],
      "specialist_focus": "gynecology",
      "target_audience": "gynecologist"
    },
    "clinical_summary": {
      "chief_complaint": "Irregular heavy periods",
      "hpi": "28-year-old with irregular menses since menarche...",
      "menstrual_history": {
        "lmp": "6 weeks ago",
        "cycle_length": "35-60 days",
        "cycle_regularity": "Irregular",
        "flow": "Heavy, 7-8 days",
        "duration": "Variable"
      },
      "obstetric_history": {
        "gravidity": "G0",
        "parity": "P0",
        "pregnancy_complications": []
      }
    },
    "gynecologic_assessment": {
      "menstrual_abnormalities": {
        "pattern": "Oligomenorrhea",
        "abnormal_bleeding": ["Menorrhagia", "No intermenstrual bleeding"],
        "dysmenorrhea": "Mild, managed with NSAIDs"
      },
      "pelvic_symptoms": {
        "pain": ["Mild cramping with menses"],
        "pressure": "None",
        "discharge": "Normal physiologic"
      },
      "hormonal_symptoms": {
        "vasomotor": [],
        "mood": ["Mild PMS symptoms"],
        "other": ["Acne", "Hirsutism - upper lip/chin", "Weight gain"]
      },
      "sexual_health": {
        "dyspareunia": "None",
        "libido_changes": "Normal",
        "contraception": "None currently, desires pregnancy in future"
      }
    },
    "diagnostic_recommendations": {
      "laboratory": [
        {"test": "CBC", "indication": "Heavy bleeding evaluation"},
        {"test": "TSH, prolactin", "indication": "Menstrual irregularity"},
        {"test": "FSH, LH, estradiol", "indication": "Day 3 if possible"},
        {"test": "Testosterone, DHEAS", "indication": "PCOS workup"}
      ],
      "imaging": [
        {"test": "Pelvic ultrasound", "indication": "Evaluate for PCOS, structural abnormalities"},
        {"test": "Saline sonogram", "indication": "If structural abnormality suspected"}
      ],
      "procedures": [
        {"test": "Endometrial biopsy", "indication": "Not indicated at age 28 unless persistent bleeding"},
        {"test": "Hysteroscopy", "indication": "Only if structural abnormality"}
      ]
    },
    "treatment_recommendations": {
      "menstrual_management": {
        "hormonal": ["Combined OCPs - first line", "Consider extended cycling"],
        "non_hormonal": ["Tranexamic acid for heavy days"],
        "procedural": ["Not indicated currently"]
      },
      "fertility_considerations": {
        "current_desires": "Not trying currently, wants children in 2-3 years",
        "fertility_preservation": "Counsel on age and PCOS impact"
      },
      "pcos_management": {
        "lifestyle": ["Weight loss 5-10%", "Low glycemic diet", "Exercise 150 min/week"],
        "medical": ["Metformin if insulin resistant", "Spironolactone for hirsutism after OCPs"],
        "cosmetic": ["Referral for laser hair removal if desired"]
      }
    },
    "preventive_care": {
      "screening_due": [
        {"test": "Pap smear", "due_date": "Due now (q3 years)"},
        {"test": "HPV testing", "indication": "With Pap at age 30"},
        {"test": "STI screening", "timing": "If new partner"},
        {"test": "Mammogram", "indication": "Age 40 or earlier if family history"}
      ]
    },
    "clinical_assessment": {
      "Menstrual_Pattern": {
        "classification": "Oligomenorrhea with menorrhagia",
        "cycle_length": "35-60 days",
        "variability": ">20 days variation",
        "confidence": 0.95,
        "abnormalities": ["Irregular cycles", "Heavy flow"]
      },
      "PCOS_Criteria": {
        "rotterdam_criteria_met": "2/3 criteria",
        "features": {
          "oligo_anovulation": "Present",
          "hyperandrogenism": "Clinical - hirsutism, acne",
          "pco_morphology": "Pending ultrasound"
        },
        "confidence": 0.85,
        "additional_workup": ["Testosterone", "Glucose tolerance test"]
      },
      "Bleeding_Assessment": {
        "pattern": "Heavy menstrual bleeding",
        "severity": "PBAC score >100 likely",
        "etiology": "Likely anovulatory",
        "evaluation_needed": ["CBC", "Ferritin", "Thyroid"]
      }
    }
  },
  "status": "success"
}
```

## Oncology Report `/api/report/oncology`

```json
{
  "report_id": "uuid",
  "report_type": "oncology",
  "specialty": "oncology",
  "generated_at": "2025-01-01T00:00:00Z",
  "report_data": {
    "executive_summary": {
      "one_page_summary": "Comprehensive oncologic evaluation for concerning symptoms...",
      "key_findings": ["Unintentional weight loss", "Night sweats", "Fatigue", "Lymphadenopathy"],
      "patterns_identified": ["B symptoms pattern", "Constitutional symptoms suggestive of malignancy"],
      "chief_complaints": ["Weight loss 20 lbs in 3 months", "Drenching night sweats", "Palpable neck mass"],
      "action_items": ["Urgent oncology referral", "CT chest/abdomen/pelvis", "Lymph node biopsy", "Complete staging workup"],
      "red_flags": ["Rapid weight loss >10%", "Persistent lymphadenopathy", "B symptoms"],
      "urgency_assessment": "Urgent - evaluation within 1-2 weeks"
    },
    "symptom_analysis": {
      "constitutional_symptoms": {
        "weight_loss": {
          "amount": "20 lbs (12% body weight)",
          "duration": "3 months",
          "intentional": false,
          "appetite": "Decreased"
        },
        "night_sweats": {
          "frequency": "4-5 nights/week",
          "severity": "Drenching - requires changing clothes",
          "duration": "2 months"
        },
        "fever": {
          "pattern": "Low-grade intermittent",
          "max_temp": "100.4°F",
          "pel_ebstein": false
        },
        "fatigue": {
          "severity": "Severe - affecting daily activities",
          "progression": "Worsening"
        }
      },
      "localized_symptoms": {
        "lymphadenopathy": {
          "locations": ["Cervical", "Supraclavicular"],
          "characteristics": "Firm, non-tender, fixed",
          "size": "2-3 cm"
        },
        "pain": {
          "bone_pain": "None currently",
          "abdominal": "Mild fullness"
        },
        "organ_specific": {
          "respiratory": ["Mild dyspnea on exertion"],
          "gi": ["Early satiety"],
          "neurologic": ["No focal deficits"]
        }
      }
    },
    "risk_assessment": {
      "personal_history": {
        "prior_cancer": "None",
        "radiation_exposure": "None known",
        "immunosuppression": "None"
      },
      "family_history": {
        "first_degree": ["Mother - breast cancer at 55", "Father - colon cancer at 65"],
        "hereditary_syndromes": "Not tested"
      },
      "environmental": {
        "tobacco": "Never smoker",
        "alcohol": "Social",
        "occupational": "Office worker - no known exposures"
      },
      "age_related_risk": "Age 45 - screening age for several cancers"
    },
    "diagnostic_priorities": {
      "immediate": [
        {
          "test": "CBC with differential",
          "rationale": "Evaluate for hematologic malignancy, cytopenias"
        },
        {
          "test": "Comprehensive metabolic panel",
          "rationale": "Organ function, calcium level"
        },
        {
          "test": "LDH, uric acid",
          "rationale": "Tumor burden markers"
        },
        {
          "test": "ESR, CRP",
          "rationale": "Inflammatory markers"
        }
      ],
      "imaging": [
        {
          "test": "CT chest/abdomen/pelvis with contrast",
          "urgency": "Within 1 week",
          "rationale": "Staging, identify primary site"
        },
        {
          "test": "PET/CT",
          "indication": "If lymphoma suspected after initial workup"
        }
      ],
      "tissue_diagnosis": [
        {
          "procedure": "Excisional lymph node biopsy",
          "urgency": "ASAP after imaging",
          "preferred": "Largest, most accessible node"
        },
        {
          "additional": "Flow cytometry, immunohistochemistry",
          "rationale": "Complete characterization"
        }
      ],
      "tumor_markers": {
        "if_indicated": ["Based on imaging findings", "AFP, CEA, CA 19-9, PSA as appropriate"]
      }
    },
    "differential_diagnosis": {
      "hematologic": [
        {
          "diagnosis": "Lymphoma (Hodgkin or Non-Hodgkin)",
          "supporting": "B symptoms, lymphadenopathy",
          "probability": "High"
        },
        {
          "diagnosis": "Leukemia",
          "supporting": "Constitutional symptoms",
          "probability": "Moderate"
        }
      ],
      "solid_tumors": [
        {
          "diagnosis": "Lung cancer",
          "supporting": "Constitutional symptoms",
          "probability": "Consider even in non-smoker"
        },
        {
          "diagnosis": "GI malignancy",
          "supporting": "Weight loss, early satiety",
          "probability": "Moderate"
        }
      ],
      "infectious": [
        {
          "diagnosis": "TB",
          "supporting": "Night sweats, lymphadenopathy",
          "probability": "Low but test"
        },
        {
          "diagnosis": "HIV",
          "supporting": "Constitutional symptoms",
          "probability": "Screen"
        }
      ]
    },
    "staging_workup": {
      "laboratory": [
        "Complete blood count with manual differential",
        "Comprehensive metabolic panel including calcium",
        "Liver function tests",
        "LDH, Beta-2 microglobulin",
        "Viral screens: HIV, Hepatitis B/C, EBV"
      ],
      "imaging_sequence": {
        "initial": "CT chest/abdomen/pelvis",
        "additional": "MRI brain if neurologic symptoms",
        "functional": "PET/CT for lymphoma staging"
      },
      "additional_biopsies": {
        "bone_marrow": "If hematologic malignancy confirmed",
        "other_sites": "Based on imaging findings"
      }
    },
    "referral_recommendations": {
      "oncology": {
        "urgency": "Urgent - within 1-2 weeks",
        "type": "Hematology/Oncology given lymphadenopathy",
        "prepare": "Have all test results available"
      },
      "supportive_services": [
        {
          "service": "Social work",
          "reason": "Psychosocial support, financial counseling"
        },
        {
          "service": "Nutrition",
          "reason": "Address weight loss"
        }
      ]
    },
    "patient_counseling": {
      "initial_discussion": [
        "Symptoms concerning and need thorough evaluation",
        "Multiple possibilities including treatable conditions",
        "Importance of prompt workup"
      ],
      "support_resources": [
        "Cancer support groups",
        "American Cancer Society resources",
        "Financial assistance programs"
      ],
      "next_steps": [
        "Schedule imaging within 1 week",
        "Surgical referral for lymph node biopsy",
        "Follow up in 1 week with initial results"
      ]
    },
    "clinical_urgency_scale": {
      "overall_urgency": "High",
      "red_flag_count": 4,
      "time_to_diagnosis": "Target <2 weeks",
      "reasoning": "Multiple B symptoms with lymphadenopathy requires urgent evaluation"
    }
  },
  "status": "success"
}
```

## Physical Therapy Report `/api/report/physical-therapy`

```json
{
  "report_id": "uuid",
  "report_type": "physical_therapy",
  "specialty": "physical-therapy",
  "generated_at": "2025-01-01T00:00:00Z",
  "report_data": {
    "executive_summary": {
      "one_page_summary": "Comprehensive functional assessment for physical therapy...",
      "key_findings": ["Chronic low back pain", "Functional limitations in ADLs", "Deconditioning", "Poor posture"],
      "patterns_identified": ["Mechanical low back pain", "Core weakness", "Movement avoidance behavior"],
      "chief_complaints": ["Low back pain", "Difficulty bending", "Unable to lift grandchildren"],
      "action_items": ["Start PT 2-3x/week", "Core strengthening", "Posture training", "Activity modification education"],
      "functional_focus": "Return to normal daily activities without pain"
    },
    "functional_assessment": {
      "primary_limitations": [
        {
          "activity": "Bending forward",
          "limitation": "Unable to touch knees without pain",
          "impact": "Cannot put on shoes/socks independently"
        },
        {
          "activity": "Lifting",
          "limitation": "Maximum 10 lbs from floor",
          "impact": "Cannot lift grandchildren (25 lbs)"
        },
        {
          "activity": "Sitting",
          "limitation": "30 minutes maximum",
          "impact": "Difficulty with desk work"
        },
        {
          "activity": "Walking",
          "limitation": "15-20 minutes on flat surface",
          "impact": "Cannot shop for groceries"
        }
      ],
      "pain_with_movement": {
        "flexion": "7/10 pain at end range",
        "extension": "3/10 pain",
        "rotation": "5/10 pain bilaterally",
        "lateral_flexion": "4/10 pain bilaterally"
      },
      "functional_scale_scores": {
        "oswestry": "44% (moderate disability)",
        "patient_specific": "3/10 average on functional tasks"
      }
    },
    "movement_analysis": {
      "posture": {
        "standing": "Forward head, increased lumbar lordosis, anterior pelvic tilt",
        "sitting": "Slouched, lack of lumbar support"
      },
      "movement_patterns": {
        "squat": "Avoids hip hinge, excessive knee flexion",
        "lifting": "Bends from back, no hip hinge",
        "gait": "Reduced arm swing, shortened stride length"
      },
      "muscle_imbalances": {
        "weak": ["Core muscles", "Gluteals", "Deep spinal stabilizers"],
        "tight": ["Hip flexors", "Hamstrings", "Lumbar paraspinals"],
        "overactive": ["Quadratus lumborum", "Upper traps"]
      }
    },
    "treatment_plan": {
      "phase_1_weeks_1_2": {
        "goals": ["Reduce pain to 5/10", "Improve pain-free ROM", "Education on spine mechanics"],
        "interventions": [
          "Manual therapy: Soft tissue mobilization",
          "Modalities: Heat/ice education",
          "Exercises: Pelvic tilts, knee to chest, cat-cow",
          "Education: Proper body mechanics"
        ],
        "frequency": "2-3x/week"
      },
      "phase_2_weeks_3_6": {
        "goals": ["Strengthen core", "Improve functional movements", "Reduce pain to 3/10"],
        "interventions": [
          "Progressive core strengthening",
          "Hip hinge training",
          "Bridge progressions",
          "Functional activity training"
        ],
        "home_program": "Daily exercises, 15-20 minutes"
      },
      "phase_3_weeks_7_12": {
        "goals": ["Return to all ADLs", "Lift 30 lbs safely", "Walk 45 minutes"],
        "interventions": [
          "Advanced strengthening",
          "Work simulation activities",
          "Cardiovascular conditioning",
          "Sport/activity specific training"
        ],
        "frequency": "1-2x/week with HEP"
      }
    },
    "home_exercise_program": {
      "week_1_2": [
        {
          "exercise": "Pelvic tilts",
          "sets_reps": "2x10",
          "frequency": "2x daily",
          "instructions": "Lying on back, flatten low back to surface"
        },
        {
          "exercise": "Knee to chest stretch",
          "sets_reps": "3x30 seconds each",
          "frequency": "2x daily",
          "instructions": "One knee at a time, gentle stretch"
        },
        {
          "exercise": "Walking",
          "duration": "10 minutes",
          "frequency": "2x daily",
          "instructions": "Flat surface, comfortable pace"
        }
      ],
      "progression_criteria": "Pain <5/10 with all exercises, proper form demonstrated"
    },
    "expected_outcomes": {
      "week_2": {
        "pain": "Reduce to 5-6/10",
        "function": "Sit 45 minutes",
        "activities": "Don shoes with minimal pain"
      },
      "week_6": {
        "pain": "Reduce to 3-4/10",
        "function": "Lift 20 lbs from floor",
        "activities": "Walk 30 minutes continuously"
      },
      "week_12": {
        "pain": "0-2/10 with activities",
        "function": "Lift 30+ lbs safely",
        "activities": "Return to all desired activities"
      }
    },
    "education_priorities": [
      "Spine anatomy and pain mechanisms",
      "Proper lifting mechanics",
      "Posture awareness and correction",
      "Activity pacing strategies",
      "Difference between hurt vs harm",
      "Long-term exercise importance"
    ],
    "equipment_recommendations": {
      "immediate": [
        "Lumbar roll for sitting",
        "Ice packs for flare-ups"
      ],
      "future": [
        "Resistance bands",
        "Stability ball",
        "Foam roller"
      ]
    },
    "precautions": {
      "red_flags_absent": ["Progressive neurological symptoms", "Bowel/bladder changes", "Saddle anesthesia"],
      "activity_restrictions": ["No heavy lifting >10 lbs initially", "Avoid prolonged sitting >30 min"],
      "when_to_stop": ["Sharp increasing pain", "Numbness/tingling in legs", "Any new symptoms"]
    },
    "referral_considerations": {
      "if_no_progress": [
        "MRI after 6 weeks if no improvement",
        "Pain management for injections",
        "Physiatry consultation"
      ],
      "complementary": [
        "Massage therapy for muscle tension",
        "Acupuncture if interested"
      ]
    },
    "prognosis": {
      "expected_recovery": "Good - 80% improvement expected",
      "timeline": "12 weeks for full recovery",
      "factors_favorable": ["Motivated", "No neurological symptoms", "First episode"],
      "factors_unfavorable": ["Sedentary job", "High BMI", "Fear avoidance behaviors"],
      "maintenance": "Ongoing HEP 3x/week indefinitely"
    }
  },
  "status": "success"
}
```

## Summary

Each specialist report returns:
1. **Common structure**: All have `report_id`, `report_type`, `specialty`, `generated_at`, `report_data`, and `status`
2. **Unique sections**: Each specialty has its own assessment fields (e.g., `cardiology_assessment`, `neurology_assessment`)
3. **Specialist-specific findings**: Most have `{specialist}_specific_findings` (e.g., `cardiologist_specific_findings`)
4. **Clinical scales**: Each specialty includes relevant validated scales with scores and confidence levels
5. **Specialty variations**: 
   - Primary care uses a completely different structure
   - Some specialties (oncology, physical therapy) don't follow the `{specialty}_assessment` pattern
   - Field naming is inconsistent (e.g., `orthopedic_assessment` not `orthopedics_assessment`)

The frontend should use the specialty field to determine which sections to display and handle the naming inconsistencies.