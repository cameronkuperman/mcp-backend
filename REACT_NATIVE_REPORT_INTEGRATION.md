# React Native Medical Report Integration Guide

Complete implementation for medical report generation in React Native mobile apps.

## 1. Report API Service

Create `services/reportApi.ts`:

```typescript
import AsyncStorage from '@react-native-async-storage/async-storage';
import { API_BASE_URL } from '@/config/api';

// Types
export interface ReportAnalyzeRequest {
  user_id?: string;
  context: {
    purpose?: 'symptom_specific' | 'annual_checkup' | 'specialist_referral' | 'emergency';
    symptom_focus?: string;
    time_frame?: {
      start?: string;
      end?: string;
    };
    target_audience?: 'self' | 'primary_care' | 'specialist' | 'emergency';
  };
  available_data?: {
    quick_scan_ids?: string[];
    deep_dive_ids?: string[];
    photo_session_ids?: string[];
  };
}

export interface ReportAnalyzeResponse {
  recommended_endpoint: string;
  recommended_type: string;
  reasoning: string;
  confidence: number;
  report_config: any;
  analysis_id: string;
  status: 'success' | 'error';
}

class ReportApiService {
  private async getAuthToken(): Promise<string | null> {
    return await AsyncStorage.getItem('authToken');
  }

  private async makeRequest(endpoint: string, method: string, body?: any) {
    const token = await this.getAuthToken();
    
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` }),
      },
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }

    return response.json();
  }

  // Step 1: Analyze report type
  async analyzeReport(request: ReportAnalyzeRequest): Promise<ReportAnalyzeResponse> {
    return this.makeRequest('/api/report/analyze', 'POST', request);
  }

  // Step 2: Generate specific reports
  async generateComprehensive(analysisId: string, userId?: string) {
    return this.makeRequest('/api/report/comprehensive', 'POST', {
      analysis_id: analysisId,
      user_id: userId,
    });
  }

  async generateUrgentTriage(analysisId: string, userId?: string) {
    return this.makeRequest('/api/report/urgent-triage', 'POST', {
      analysis_id: analysisId,
      user_id: userId,
    });
  }

  async generateSymptomTimeline(analysisId: string, userId?: string, symptomFocus?: string) {
    return this.makeRequest('/api/report/symptom-timeline', 'POST', {
      analysis_id: analysisId,
      user_id: userId,
      symptom_focus: symptomFocus,
    });
  }

  async generatePhotoProgression(analysisId: string, userId?: string) {
    return this.makeRequest('/api/report/photo-progression', 'POST', {
      analysis_id: analysisId,
      user_id: userId,
    });
  }

  async generateSpecialist(analysisId: string, userId?: string, specialty?: string) {
    return this.makeRequest('/api/report/specialist', 'POST', {
      analysis_id: analysisId,
      user_id: userId,
      specialty,
    });
  }

  async generateAnnualSummary(analysisId: string, userId: string, year?: number) {
    return this.makeRequest('/api/report/annual-summary', 'POST', {
      analysis_id: analysisId,
      user_id: userId,
      year,
    });
  }

  // Helper to generate any report based on analysis
  async generateReport(analysis: ReportAnalyzeResponse, userId?: string) {
    switch (analysis.recommended_type) {
      case 'comprehensive':
        return this.generateComprehensive(analysis.analysis_id, userId);
      case 'urgent_triage':
        return this.generateUrgentTriage(analysis.analysis_id, userId);
      case 'symptom_timeline':
        return this.generateSymptomTimeline(
          analysis.analysis_id,
          userId,
          analysis.report_config.primary_focus
        );
      case 'photo_progression':
        return this.generatePhotoProgression(analysis.analysis_id, userId);
      case 'specialist_focused':
        return this.generateSpecialist(analysis.analysis_id, userId);
      case 'annual_summary':
        return this.generateAnnualSummary(analysis.analysis_id, userId!);
      default:
        return this.generateComprehensive(analysis.analysis_id, userId);
    }
  }
}

export const reportApi = new ReportApiService();
```

## 2. Report Generation Hook

Create `hooks/useReportGeneration.ts`:

```typescript
import { useState, useCallback } from 'react';
import { reportApi, ReportAnalyzeRequest } from '@/services/reportApi';
import { useAuth } from '@/hooks/useAuth';
import { Alert } from 'react-native';

interface ReportGenerationState {
  isAnalyzing: boolean;
  isGenerating: boolean;
  analysis: any | null;
  report: any | null;
  error: string | null;
}

export const useReportGeneration = () => {
  const { user } = useAuth();
  const [state, setState] = useState<ReportGenerationState>({
    isAnalyzing: false,
    isGenerating: false,
    analysis: null,
    report: null,
    error: null,
  });

  const generateReport = useCallback(async (request: ReportAnalyzeRequest) => {
    setState(prev => ({ ...prev, isAnalyzing: true, error: null }));

    try {
      // Step 1: Analyze
      const analysis = await reportApi.analyzeReport({
        ...request,
        user_id: request.user_id || user?.id,
      });

      setState(prev => ({
        ...prev,
        analysis,
        isAnalyzing: false,
        isGenerating: true,
      }));

      // Step 2: Generate
      const report = await reportApi.generateReport(
        analysis,
        request.user_id || user?.id
      );

      setState(prev => ({
        ...prev,
        report,
        isGenerating: false,
      }));

      return { analysis, report };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to generate report';
      setState(prev => ({
        ...prev,
        error: errorMessage,
        isAnalyzing: false,
        isGenerating: false,
      }));
      
      Alert.alert('Error', errorMessage);
      throw error;
    }
  }, [user]);

  const reset = useCallback(() => {
    setState({
      isAnalyzing: false,
      isGenerating: false,
      analysis: null,
      report: null,
      error: null,
    });
  }, []);

  return {
    ...state,
    generateReport,
    reset,
  };
};
```

## 3. Report Generator Screen

Create `screens/ReportGeneratorScreen.tsx`:

```typescript
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
  SafeAreaView,
} from 'react-native';
import { Picker } from '@react-native-picker/picker';
import { useNavigation, useRoute } from '@react-navigation/native';
import { useReportGeneration } from '@/hooks/useReportGeneration';
import { colors } from '@/theme';
import Icon from 'react-native-vector-icons/Feather';

export const ReportGeneratorScreen = () => {
  const navigation = useNavigation();
  const route = useRoute();
  const { symptomFocus, quickScanIds = [], deepDiveIds = [] } = route.params || {};
  
  const { isAnalyzing, isGenerating, analysis, report, generateReport } = useReportGeneration();
  const [purpose, setPurpose] = useState('symptom_specific');
  const [targetAudience, setTargetAudience] = useState('self');

  useEffect(() => {
    if (report) {
      // Navigate to report viewer
      navigation.navigate('ReportViewer', { report });
    }
  }, [report]);

  const handleGenerateReport = async () => {
    await generateReport({
      context: {
        purpose: purpose as any,
        symptom_focus: symptomFocus,
        target_audience: targetAudience as any,
      },
      available_data: {
        quick_scan_ids: quickScanIds,
        deep_dive_ids: deepDiveIds,
      },
    });
  };

  const reportTypeInfo = {
    comprehensive: { icon: 'file-text', color: colors.primary },
    urgent_triage: { icon: 'alert-circle', color: colors.danger },
    symptom_timeline: { icon: 'clock', color: colors.info },
    photo_progression: { icon: 'camera', color: colors.success },
    specialist_focused: { icon: 'activity', color: colors.warning },
    annual_summary: { icon: 'calendar', color: colors.secondary },
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()}>
            <Icon name="arrow-left" size={24} color={colors.text} />
          </TouchableOpacity>
          <Text style={styles.title}>Generate Medical Report</Text>
          <View style={{ width: 24 }} />
        </View>

        {/* Configuration */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Report Configuration</Text>
          
          <View style={styles.field}>
            <Text style={styles.label}>Report Purpose</Text>
            <View style={styles.pickerContainer}>
              <Picker
                selectedValue={purpose}
                onValueChange={setPurpose}
                style={styles.picker}
              >
                <Picker.Item label="Specific Symptom Analysis" value="symptom_specific" />
                <Picker.Item label="Annual Health Summary" value="annual_checkup" />
                <Picker.Item label="Specialist Referral" value="specialist_referral" />
                <Picker.Item label="Emergency/Urgent" value="emergency" />
              </Picker>
            </View>
          </View>

          <View style={styles.field}>
            <Text style={styles.label}>Target Audience</Text>
            <View style={styles.pickerContainer}>
              <Picker
                selectedValue={targetAudience}
                onValueChange={setTargetAudience}
                style={styles.picker}
              >
                <Picker.Item label="Personal Use" value="self" />
                <Picker.Item label="Primary Care Doctor" value="primary_care" />
                <Picker.Item label="Specialist" value="specialist" />
                <Picker.Item label="Emergency Department" value="emergency" />
              </Picker>
            </View>
          </View>

          {symptomFocus && (
            <View style={styles.infoBox}>
              <Icon name="info" size={16} color={colors.primary} />
              <Text style={styles.infoText}>
                Symptom Focus: {symptomFocus}
              </Text>
            </View>
          )}
        </View>

        {/* Available Data */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Available Data</Text>
          <View style={styles.dataGrid}>
            <View style={styles.dataItem}>
              <Icon name="file-text" size={24} color={colors.primary} />
              <Text style={styles.dataCount}>{quickScanIds.length}</Text>
              <Text style={styles.dataLabel}>Quick Scans</Text>
            </View>
            <View style={styles.dataItem}>
              <Icon name="layers" size={24} color={colors.secondary} />
              <Text style={styles.dataCount}>{deepDiveIds.length}</Text>
              <Text style={styles.dataLabel}>Deep Dives</Text>
            </View>
          </View>
        </View>

        {/* Analysis Result */}
        {analysis && !isGenerating && (
          <View style={[styles.section, styles.analysisResult]}>
            <View style={styles.analysisHeader}>
              <Icon 
                name={reportTypeInfo[analysis.recommended_type]?.icon || 'file'} 
                size={24} 
                color={reportTypeInfo[analysis.recommended_type]?.color || colors.primary} 
              />
              <View style={styles.analysisText}>
                <Text style={styles.analysisTitle}>
                  Recommended: {analysis.recommended_type.replace(/_/g, ' ').toUpperCase()}
                </Text>
                <Text style={styles.analysisReason}>{analysis.reasoning}</Text>
              </View>
            </View>
            <Text style={styles.confidence}>
              Confidence: {Math.round(analysis.confidence * 100)}%
            </Text>
          </View>
        )}

        {/* Generate Button */}
        <TouchableOpacity
          style={[styles.generateButton, (isAnalyzing || isGenerating) && styles.buttonDisabled]}
          onPress={handleGenerateReport}
          disabled={isAnalyzing || isGenerating}
        >
          {isAnalyzing ? (
            <>
              <ActivityIndicator color="white" size="small" />
              <Text style={styles.buttonText}>Analyzing your data...</Text>
            </>
          ) : isGenerating ? (
            <>
              <ActivityIndicator color="white" size="small" />
              <Text style={styles.buttonText}>
                Generating {analysis?.recommended_type.replace(/_/g, ' ')} report...
              </Text>
            </>
          ) : (
            <>
              <Icon name="file-text" size={20} color="white" />
              <Text style={styles.buttonText}>Generate Medical Report</Text>
            </>
          )}
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  scrollContent: {
    paddingBottom: 20,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  title: {
    fontSize: 20,
    fontWeight: '600',
    color: colors.text,
  },
  section: {
    padding: 16,
    backgroundColor: 'white',
    marginTop: 12,
    marginHorizontal: 16,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowRadius: 10,
    elevation: 2,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 16,
  },
  field: {
    marginBottom: 16,
  },
  label: {
    fontSize: 14,
    fontWeight: '500',
    color: colors.textSecondary,
    marginBottom: 8,
  },
  pickerContainer: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    overflow: 'hidden',
  },
  picker: {
    height: 50,
  },
  infoBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.primaryLight,
    padding: 12,
    borderRadius: 8,
    marginTop: 8,
  },
  infoText: {
    marginLeft: 8,
    color: colors.primary,
    fontSize: 14,
    fontWeight: '500',
  },
  dataGrid: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  dataItem: {
    alignItems: 'center',
  },
  dataCount: {
    fontSize: 24,
    fontWeight: '600',
    color: colors.text,
    marginTop: 8,
  },
  dataLabel: {
    fontSize: 14,
    color: colors.textSecondary,
    marginTop: 4,
  },
  analysisResult: {
    backgroundColor: colors.primaryLight,
  },
  analysisHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  analysisText: {
    flex: 1,
    marginLeft: 12,
  },
  analysisTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
  },
  analysisReason: {
    fontSize: 14,
    color: colors.textSecondary,
    marginTop: 4,
  },
  confidence: {
    fontSize: 14,
    color: colors.textSecondary,
    marginTop: 12,
  },
  generateButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.primary,
    marginHorizontal: 16,
    marginTop: 24,
    paddingVertical: 16,
    borderRadius: 12,
  },
  buttonDisabled: {
    backgroundColor: colors.disabled,
  },
  buttonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
});
```

## 4. Report Viewer Screen

Create `screens/ReportViewerScreen.tsx`:

```typescript
import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  Share,
  Alert,
  Platform,
} from 'react-native';
import { useRoute, useNavigation } from '@react-navigation/native';
import Icon from 'react-native-vector-icons/Feather';
import RNHTMLtoPDF from 'react-native-html-to-pdf';
import FileViewer from 'react-native-file-viewer';
import { colors } from '@/theme';

export const ReportViewerScreen = () => {
  const route = useRoute();
  const navigation = useNavigation();
  const { report } = route.params;
  const [activeSection, setActiveSection] = useState('executive_summary');
  const [isExporting, setIsExporting] = useState(false);

  const exportPDF = async () => {
    setIsExporting(true);
    try {
      const html = generateReportHTML(report);
      const options = {
        html,
        fileName: `medical-report-${report.report_id}`,
        directory: Platform.OS === 'ios' ? 'Documents' : 'Download',
      };

      const file = await RNHTMLtoPDF.convert(options);
      
      Alert.alert(
        'PDF Generated',
        'Would you like to view or share the report?',
        [
          { text: 'View', onPress: () => FileViewer.open(file.filePath) },
          { text: 'Share', onPress: () => shareReport(file.filePath) },
          { text: 'Done', style: 'cancel' },
        ]
      );
    } catch (error) {
      Alert.alert('Error', 'Failed to generate PDF');
    } finally {
      setIsExporting(false);
    }
  };

  const shareReport = async (filePath?: string) => {
    try {
      const message = report.report_data.executive_summary.one_page_summary;
      
      if (filePath) {
        await Share.share({
          message,
          url: `file://${filePath}`,
        });
      } else {
        await Share.share({ message });
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to share report');
    }
  };

  // Urgent triage report - special layout
  if (report.report_type === 'urgent_triage') {
    return (
      <SafeAreaView style={[styles.container, styles.urgentContainer]}>
        <ScrollView contentContainerStyle={styles.scrollContent}>
          <View style={styles.urgentHeader}>
            <Icon name="alert-circle" size={32} color={colors.danger} />
            <Text style={styles.urgentTitle}>Urgent Medical Summary</Text>
          </View>

          <View style={styles.urgentAction}>
            <Text style={styles.urgentActionLabel}>Immediate Action Required:</Text>
            <Text style={styles.urgentActionText}>
              {report.triage_summary.recommended_action}
            </Text>
          </View>

          <View style={styles.urgentSection}>
            <Text style={styles.urgentSectionTitle}>Critical Symptoms:</Text>
            {report.triage_summary.vital_symptoms?.map((symptom, idx) => (
              <View key={idx} style={styles.symptomCard}>
                <Text style={styles.symptomName}>
                  {symptom.symptom} - {symptom.severity}
                </Text>
                <Text style={styles.symptomDuration}>Duration: {symptom.duration}</Text>
                {symptom.red_flags?.length > 0 && (
                  <Text style={styles.redFlag}>⚠️ {symptom.red_flags.join(', ')}</Text>
                )}
              </View>
            ))}
          </View>

          <View style={styles.urgentSection}>
            <Text style={styles.urgentSectionTitle}>Tell the Doctor:</Text>
            {report.triage_summary.what_to_tell_doctor?.map((point, idx) => (
              <Text key={idx} style={styles.bulletPoint}>• {point}</Text>
            ))}
          </View>

          <TouchableOpacity
            style={styles.urgentButton}
            onPress={exportPDF}
            disabled={isExporting}
          >
            <Icon name="download" size={20} color="white" />
            <Text style={styles.urgentButtonText}>Download Emergency Summary</Text>
          </TouchableOpacity>
        </ScrollView>
      </SafeAreaView>
    );
  }

  // Standard report viewer
  const sections = Object.keys(report.report_data);

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Icon name="arrow-left" size={24} color={colors.text} />
        </TouchableOpacity>
        <Text style={styles.title}>Medical Report</Text>
        <View style={styles.headerActions}>
          <TouchableOpacity onPress={exportPDF} style={styles.headerButton}>
            <Icon name="download" size={20} color={colors.primary} />
          </TouchableOpacity>
          <TouchableOpacity onPress={() => shareReport()} style={styles.headerButton}>
            <Icon name="share-2" size={20} color={colors.primary} />
          </TouchableOpacity>
        </View>
      </View>

      {/* Report Info */}
      <View style={styles.reportInfo}>
        <Text style={styles.reportType}>
          {report.report_type.replace(/_/g, ' ').toUpperCase()}
        </Text>
        <Text style={styles.reportDate}>
          {new Date(report.generated_at).toLocaleDateString()}
        </Text>
      </View>

      {/* Section Tabs */}
      <ScrollView 
        horizontal 
        showsHorizontalScrollIndicator={false}
        style={styles.tabContainer}
      >
        {sections.map((section) => (
          <TouchableOpacity
            key={section}
            onPress={() => setActiveSection(section)}
            style={[
              styles.tab,
              activeSection === section && styles.activeTab,
            ]}
          >
            <Text style={[
              styles.tabText,
              activeSection === section && styles.activeTabText,
            ]}>
              {section.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* Content */}
      <ScrollView style={styles.content}>
        <ReportSection
          sectionName={activeSection}
          sectionData={report.report_data[activeSection]}
        />
      </ScrollView>
    </SafeAreaView>
  );
};

// Section renderer component
const ReportSection = ({ sectionName, sectionData }) => {
  if (sectionName === 'executive_summary') {
    return (
      <View style={styles.section}>
        <View style={styles.summaryBox}>
          <Text style={styles.summaryTitle}>One Page Summary</Text>
          <Text style={styles.summaryText}>{sectionData.one_page_summary}</Text>
        </View>

        {sectionData.chief_complaints?.length > 0 && (
          <View style={styles.listSection}>
            <Text style={styles.listTitle}>Chief Complaints</Text>
            {sectionData.chief_complaints.map((item, idx) => (
              <Text key={idx} style={styles.listItem}>• {item}</Text>
            ))}
          </View>
        )}

        {sectionData.key_findings?.length > 0 && (
          <View style={styles.listSection}>
            <Text style={styles.listTitle}>Key Findings</Text>
            {sectionData.key_findings.map((item, idx) => (
              <Text key={idx} style={styles.listItem}>• {item}</Text>
            ))}
          </View>
        )}
      </View>
    );
  }

  // Generic section renderer
  return (
    <View style={styles.section}>
      {Object.entries(sectionData).map(([key, value]) => (
        <View key={key} style={styles.subsection}>
          <Text style={styles.subsectionTitle}>
            {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
          </Text>
          {Array.isArray(value) ? (
            value.map((item, idx) => (
              <Text key={idx} style={styles.listItem}>
                • {typeof item === 'object' ? JSON.stringify(item) : item}
              </Text>
            ))
          ) : typeof value === 'object' ? (
            <Text style={styles.jsonText}>{JSON.stringify(value, null, 2)}</Text>
          ) : (
            <Text style={styles.valueText}>{value}</Text>
          )}
        </View>
      ))}
    </View>
  );
};

// Helper function to generate HTML for PDF
const generateReportHTML = (report) => {
  return `
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        h1 { color: #333; }
        h2 { color: #666; margin-top: 20px; }
        h3 { color: #888; }
        .summary { background-color: #f5f5f5; padding: 15px; border-radius: 5px; }
        .section { margin-bottom: 30px; }
        ul { margin-left: 20px; }
      </style>
    </head>
    <body>
      <h1>Medical Report</h1>
      <p>Generated: ${new Date(report.generated_at).toLocaleString()}</p>
      <p>Report ID: ${report.report_id}</p>
      
      <div class="summary">
        <h2>Executive Summary</h2>
        <p>${report.report_data.executive_summary.one_page_summary}</p>
      </div>
      
      <!-- Add more sections as needed -->
    </body>
    </html>
  `;
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  urgentContainer: {
    backgroundColor: '#FEF2F2',
  },
  scrollContent: {
    paddingBottom: 20,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    backgroundColor: 'white',
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  title: {
    fontSize: 20,
    fontWeight: '600',
    color: colors.text,
  },
  headerActions: {
    flexDirection: 'row',
  },
  headerButton: {
    marginLeft: 16,
  },
  reportInfo: {
    backgroundColor: 'white',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  reportType: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.primary,
  },
  reportDate: {
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 4,
  },
  tabContainer: {
    backgroundColor: 'white',
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  tab: {
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
  },
  activeTab: {
    borderBottomColor: colors.primary,
  },
  tabText: {
    fontSize: 14,
    color: colors.textSecondary,
  },
  activeTabText: {
    color: colors.primary,
    fontWeight: '600',
  },
  content: {
    flex: 1,
  },
  section: {
    padding: 16,
  },
  summaryBox: {
    backgroundColor: colors.primaryLight,
    padding: 16,
    borderRadius: 12,
    marginBottom: 16,
  },
  summaryTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 8,
  },
  summaryText: {
    fontSize: 14,
    color: colors.text,
    lineHeight: 20,
  },
  listSection: {
    marginBottom: 16,
  },
  listTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 8,
  },
  listItem: {
    fontSize: 14,
    color: colors.text,
    marginBottom: 4,
    paddingLeft: 8,
  },
  subsection: {
    marginBottom: 20,
  },
  subsectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 8,
  },
  valueText: {
    fontSize: 14,
    color: colors.text,
  },
  jsonText: {
    fontSize: 12,
    color: colors.textSecondary,
    backgroundColor: '#f5f5f5',
    padding: 8,
    borderRadius: 4,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  // Urgent styles
  urgentHeader: {
    alignItems: 'center',
    padding: 20,
  },
  urgentTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: colors.danger,
    marginTop: 8,
  },
  urgentAction: {
    backgroundColor: '#FEE2E2',
    padding: 16,
    marginHorizontal: 16,
    borderRadius: 12,
    marginBottom: 16,
  },
  urgentActionLabel: {
    fontSize: 14,
    color: colors.danger,
    marginBottom: 4,
  },
  urgentActionText: {
    fontSize: 20,
    fontWeight: '700',
    color: colors.danger,
  },
  urgentSection: {
    backgroundColor: 'white',
    padding: 16,
    marginHorizontal: 16,
    marginBottom: 16,
    borderRadius: 12,
  },
  urgentSectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 12,
  },
  symptomCard: {
    backgroundColor: '#f5f5f5',
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
  },
  symptomName: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.text,
  },
  symptomDuration: {
    fontSize: 12,
    color: colors.textSecondary,
    marginTop: 4,
  },
  redFlag: {
    fontSize: 12,
    color: colors.danger,
    marginTop: 4,
  },
  bulletPoint: {
    fontSize: 14,
    color: colors.text,
    marginBottom: 4,
    paddingLeft: 8,
  },
  urgentButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.danger,
    marginHorizontal: 16,
    paddingVertical: 16,
    borderRadius: 12,
  },
  urgentButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
});
```

## 5. Navigation Setup

Update your navigation to include report screens:

```typescript
// navigation/AppNavigator.tsx
import { ReportGeneratorScreen } from '@/screens/ReportGeneratorScreen';
import { ReportViewerScreen } from '@/screens/ReportViewerScreen';

// Add to your stack navigator
<Stack.Screen 
  name="ReportGenerator" 
  component={ReportGeneratorScreen}
  options={{ title: 'Generate Report' }}
/>
<Stack.Screen 
  name="ReportViewer" 
  component={ReportViewerScreen}
  options={{ title: 'Medical Report' }}
/>
```

## 6. Integration from Quick Scan Results

```typescript
// In QuickScanResultsScreen
const handleGenerateReport = () => {
  navigation.navigate('ReportGenerator', {
    symptomFocus: analysis.primaryCondition,
    quickScanIds: [scanId],
  });
};

// Add button
<TouchableOpacity
  style={styles.reportButton}
  onPress={handleGenerateReport}
>
  <Icon name="file-text" size={20} color="white" />
  <Text style={styles.reportButtonText}>Generate Medical Report</Text>
</TouchableOpacity>
```

## 7. Required Dependencies

Add to `package.json`:

```json
{
  "dependencies": {
    "react-native-html-to-pdf": "^0.12.0",
    "react-native-file-viewer": "^2.1.5",
    "@react-native-picker/picker": "^2.4.8",
    "react-native-vector-icons": "^9.2.0"
  }
}
```

## iOS Setup

Add to `Info.plist`:

```xml
<key>UIFileSharingEnabled</key>
<true/>
<key>LSSupportsOpeningDocumentsInPlace</key>
<true/>
```

## Android Setup

Add to `AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
```

## Testing

```typescript
// Test report generation
const testReport = async () => {
  const { analysis, report } = await generateReport({
    context: {
      purpose: 'symptom_specific',
      symptom_focus: 'headache',
    },
    user_id: 'test-user-123',
  });
  
  console.log('Analysis:', analysis.recommended_type);
  console.log('Report ID:', report.report_id);
};
```

This implementation provides a complete medical report generation system for React Native with proper mobile UI patterns, PDF export, and sharing capabilities.