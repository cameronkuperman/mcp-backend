-- Migration: Create Clinical Workflow Tables for Report Collaboration
-- Date: 2025-01-29
-- Description: Adds tables for clinical workflow, report sharing, and collaboration features

-- 1. Report workflows table
CREATE TABLE IF NOT EXISTS report_workflows (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  report_id UUID NOT NULL REFERENCES medical_reports(id) ON DELETE CASCADE,
  created_by TEXT NOT NULL, -- Changed to TEXT to match medical_reports.user_id type
  workflow_type VARCHAR(50) NOT NULL CHECK (workflow_type IN ('review', 'referral', 'consultation', 'second_opinion')),
  status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_review', 'completed', 'cancelled')),
  priority VARCHAR(20) DEFAULT 'routine' CHECK (priority IN ('routine', 'urgent', 'emergent')),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  completed_at TIMESTAMP WITH TIME ZONE,
  notes TEXT
);

-- 2. Workflow participants table
CREATE TABLE IF NOT EXISTS workflow_participants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workflow_id UUID NOT NULL REFERENCES report_workflows(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL, -- Changed to TEXT to be flexible with user_id types
  role VARCHAR(50) NOT NULL CHECK (role IN ('sender', 'reviewer', 'consultant', 'observer')),
  can_edit BOOLEAN DEFAULT false,
  can_comment BOOLEAN DEFAULT true,
  added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  added_by TEXT, -- Changed to TEXT
  UNIQUE(workflow_id, user_id)
);

-- 3. Workflow actions/comments table
CREATE TABLE IF NOT EXISTS workflow_actions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workflow_id UUID NOT NULL REFERENCES report_workflows(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL, -- Changed to TEXT
  action_type VARCHAR(50) NOT NULL CHECK (action_type IN ('comment', 'edit', 'approve', 'reject', 'forward', 'request_info', 'provide_info')),
  content JSONB NOT NULL, -- Stores comments, edits, forward details, etc.
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  parent_action_id UUID REFERENCES workflow_actions(id), -- For threaded comments
  is_private BOOLEAN DEFAULT false -- For clinician-only notes
);

-- 4. Report ratings table
CREATE TABLE IF NOT EXISTS report_ratings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  report_id UUID NOT NULL REFERENCES medical_reports(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL, -- Changed to TEXT
  rating INTEGER NOT NULL CHECK (rating IN (-1, 1)), -- -1 downvote, 1 upvote
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(report_id, user_id)
);

-- 5. Report access logs (for audit trail)
CREATE TABLE IF NOT EXISTS report_access_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  report_id UUID NOT NULL REFERENCES medical_reports(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL, -- Changed to TEXT
  access_type VARCHAR(50) NOT NULL CHECK (access_type IN ('view', 'download', 'print', 'share')),
  accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  ip_address INET,
  user_agent TEXT
);

-- 6. Notification queue for batched notifications
CREATE TABLE IF NOT EXISTS notification_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL, -- Changed to TEXT
  notification_type VARCHAR(50) NOT NULL,
  priority VARCHAR(20) DEFAULT 'routine' CHECK (priority IN ('routine', 'urgent')),
  title TEXT NOT NULL,
  message TEXT NOT NULL,
  data JSONB, -- Additional data like report_id, workflow_id, etc.
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  scheduled_for TIMESTAMP WITH TIME ZONE DEFAULT NOW() + INTERVAL '30 minutes',
  sent_at TIMESTAMP WITH TIME ZONE,
  status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed', 'cancelled')),
  delivery_method VARCHAR(50) DEFAULT 'in_app' CHECK (delivery_method IN ('in_app', 'email', 'sms', 'push'))
);

-- 7. Add specialty field to medical_reports if not exists
ALTER TABLE medical_reports 
ADD COLUMN IF NOT EXISTS specialty VARCHAR(100);

-- Indexes for performance
CREATE INDEX idx_workflows_report_id ON report_workflows(report_id);
CREATE INDEX idx_workflows_created_by ON report_workflows(created_by);
CREATE INDEX idx_workflows_status ON report_workflows(status);
CREATE INDEX idx_workflow_participants_user ON workflow_participants(user_id);
CREATE INDEX idx_workflow_actions_workflow ON workflow_actions(workflow_id);
CREATE INDEX idx_workflow_actions_user ON workflow_actions(user_id);
CREATE INDEX idx_ratings_report ON report_ratings(report_id);
CREATE INDEX idx_access_logs_report ON report_access_logs(report_id);
CREATE INDEX idx_access_logs_user ON report_access_logs(user_id);
CREATE INDEX idx_notifications_user ON notification_queue(user_id);
CREATE INDEX idx_notifications_status ON notification_queue(status);
CREATE INDEX idx_notifications_scheduled ON notification_queue(scheduled_for);

-- Row Level Security (RLS) Policies

-- Enable RLS on all tables
ALTER TABLE report_workflows ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_ratings ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_access_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_queue ENABLE ROW LEVEL SECURITY;

-- Workflow policies
CREATE POLICY "Users can view workflows they participate in" ON report_workflows
  FOR SELECT USING (
    auth.uid()::text = created_by OR
    EXISTS (
      SELECT 1 FROM workflow_participants 
      WHERE workflow_participants.workflow_id = report_workflows.id 
      AND workflow_participants.user_id = auth.uid()::text
    )
  );

CREATE POLICY "Users can create workflows for their reports" ON report_workflows
  FOR INSERT WITH CHECK (
    auth.uid()::text = created_by AND
    EXISTS (
      SELECT 1 FROM medical_reports 
      WHERE medical_reports.id = report_workflows.report_id 
      AND medical_reports.user_id = auth.uid()::text
    )
  );

-- Participant policies
CREATE POLICY "Workflow participants can view participant list" ON workflow_participants
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM workflow_participants wp
      WHERE wp.workflow_id = workflow_participants.workflow_id 
      AND wp.user_id = auth.uid()::text
    )
  );

-- Action policies
CREATE POLICY "Participants can view workflow actions" ON workflow_actions
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM workflow_participants 
      WHERE workflow_participants.workflow_id = workflow_actions.workflow_id 
      AND workflow_participants.user_id = auth.uid()::text
    ) AND (
      is_private = false OR 
      workflow_actions.user_id = auth.uid()::text
    )
  );

CREATE POLICY "Participants can create actions" ON workflow_actions
  FOR INSERT WITH CHECK (
    auth.uid()::text = user_id AND
    EXISTS (
      SELECT 1 FROM workflow_participants 
      WHERE workflow_participants.workflow_id = workflow_actions.workflow_id 
      AND workflow_participants.user_id = auth.uid()::text
    )
  );

-- Rating policies
CREATE POLICY "Users can view ratings on accessible reports" ON report_ratings
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM medical_reports 
      WHERE medical_reports.id = report_ratings.report_id 
      AND (
        medical_reports.user_id = auth.uid()::text OR
        EXISTS (
          SELECT 1 FROM workflow_participants wp
          JOIN report_workflows rw ON rw.id = wp.workflow_id
          WHERE rw.report_id = medical_reports.id 
          AND wp.user_id = auth.uid()::text
        )
      )
    )
  );

CREATE POLICY "Users can rate accessible reports" ON report_ratings
  FOR INSERT WITH CHECK (
    auth.uid()::text = user_id
  );

-- Access log policies (write-only for users, admin can read)
CREATE POLICY "System can insert access logs" ON report_access_logs
  FOR INSERT WITH CHECK (auth.uid()::text = user_id);

-- Notification policies
CREATE POLICY "Users can view their own notifications" ON notification_queue
  FOR SELECT USING (auth.uid()::text = user_id);

-- Functions for common operations

-- Function to start a workflow
CREATE OR REPLACE FUNCTION start_report_workflow(
  p_report_id UUID,
  p_workflow_type VARCHAR(50),
  p_participants TEXT[],
  p_notes TEXT DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
  v_workflow_id UUID;
  v_user_id TEXT;
BEGIN
  -- Create workflow
  INSERT INTO report_workflows (report_id, created_by, workflow_type, notes)
  VALUES (p_report_id, auth.uid()::text, p_workflow_type, p_notes)
  RETURNING id INTO v_workflow_id;
  
  -- Add creator as participant
  INSERT INTO workflow_participants (workflow_id, user_id, role, can_edit, added_by)
  VALUES (v_workflow_id, auth.uid()::text, 'sender', true, auth.uid()::text);
  
  -- Add other participants
  FOREACH v_user_id IN ARRAY p_participants
  LOOP
    INSERT INTO workflow_participants (workflow_id, user_id, role, can_edit, added_by)
    VALUES (v_workflow_id, v_user_id, 'reviewer', false, auth.uid()::text);
  END LOOP;
  
  RETURN v_workflow_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to queue a notification
CREATE OR REPLACE FUNCTION queue_notification(
  p_user_id TEXT,
  p_type VARCHAR(50),
  p_title TEXT,
  p_message TEXT,
  p_data JSONB DEFAULT NULL,
  p_priority VARCHAR(20) DEFAULT 'routine',
  p_delay_minutes INTEGER DEFAULT 30
) RETURNS UUID AS $$
DECLARE
  v_notification_id UUID;
  v_scheduled_time TIMESTAMP WITH TIME ZONE;
BEGIN
  -- Calculate scheduled time based on priority
  IF p_priority = 'urgent' THEN
    v_scheduled_time := NOW();
  ELSE
    v_scheduled_time := NOW() + (p_delay_minutes || ' minutes')::INTERVAL;
  END IF;
  
  INSERT INTO notification_queue (
    user_id, notification_type, priority, title, message, 
    data, scheduled_for
  ) VALUES (
    p_user_id, p_type, p_priority, p_title, p_message, 
    p_data, v_scheduled_time
  ) RETURNING id INTO v_notification_id;
  
  RETURN v_notification_id;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update workflow status
CREATE OR REPLACE FUNCTION update_workflow_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_workflow_timestamp
  BEFORE UPDATE ON report_workflows
  FOR EACH ROW
  EXECUTE FUNCTION update_workflow_updated_at();

-- Comments on tables for documentation
COMMENT ON TABLE report_workflows IS 'Tracks clinical workflows for report review, referral, and collaboration';
COMMENT ON TABLE workflow_participants IS 'Users participating in a workflow with their roles and permissions';
COMMENT ON TABLE workflow_actions IS 'Actions taken within a workflow (comments, edits, approvals, etc.)';
COMMENT ON TABLE report_ratings IS 'User ratings (upvote/downvote) for medical reports';
COMMENT ON TABLE report_access_logs IS 'Audit trail of report access for compliance';
COMMENT ON TABLE notification_queue IS 'Queue for batched notifications with configurable delays';

-- Grant necessary permissions (adjust based on your setup)
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO authenticated;