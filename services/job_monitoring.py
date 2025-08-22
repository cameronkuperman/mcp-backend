"""
Job Monitoring and Alerting System
Monitors background job health and triggers alerts for failures
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from enum import Enum
import os
from supabase import create_client, Client
import httpx
import json

logger = logging.getLogger(__name__)

# Initialize Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class AlertType(Enum):
    FAILURE_RATE = "failure_rate"
    DLQ_SIZE = "dlq_size"
    CIRCUIT_BREAKER = "circuit_breaker"
    RETRY_RATE = "retry_rate"
    LONG_RUNNING = "long_running"
    NO_EXECUTION = "no_execution"

class JobMonitor:
    """Monitors job health and triggers alerts"""
    
    def __init__(self):
        self.alert_cooldowns: Dict[str, datetime] = {}
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL")  # Or other notification service
        
    async def check_job_health(self) -> Dict[str, Any]:
        """Comprehensive health check for all jobs"""
        
        health_status = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "jobs": {},
            "alerts": [],
            "overall_health": "healthy"
        }
        
        try:
            # Get job statistics from last 24 hours
            stats = await self.get_job_statistics(hours=24)
            
            for job_name, job_stats in stats.items():
                job_health = await self.evaluate_job_health(job_name, job_stats)
                health_status["jobs"][job_name] = job_health
                
                # Check for alerts
                alerts = await self.check_alerts(job_name, job_stats)
                health_status["alerts"].extend(alerts)
            
            # Determine overall health
            if any(alert["severity"] == AlertSeverity.CRITICAL.value for alert in health_status["alerts"]):
                health_status["overall_health"] = "critical"
            elif any(alert["severity"] == AlertSeverity.ERROR.value for alert in health_status["alerts"]):
                health_status["overall_health"] = "unhealthy"
            elif any(alert["severity"] == AlertSeverity.WARNING.value for alert in health_status["alerts"]):
                health_status["overall_health"] = "degraded"
            
            # Send notifications for critical alerts
            await self.send_notifications(health_status["alerts"])
            
        except Exception as e:
            logger.error(f"Error checking job health: {e}")
            health_status["error"] = str(e)
            health_status["overall_health"] = "unknown"
        
        return health_status
    
    async def get_job_statistics(self, hours: int = 24) -> Dict[str, Dict]:
        """Get job execution statistics"""
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # Query job execution log
        executions = supabase.table('job_execution_log')\
            .select('*')\
            .gte('started_at', cutoff_time.isoformat())\
            .execute()
        
        # Query retry queue
        retries = supabase.table('job_retry_queue')\
            .select('*')\
            .execute()
        
        # Query dead letter queue
        dlq = supabase.table('job_dead_letter_queue')\
            .select('*')\
            .eq('resolved', False)\
            .execute()
        
        # Query circuit breakers
        circuits = supabase.table('circuit_breaker_state')\
            .select('*')\
            .neq('state', 'closed')\
            .execute()
        
        # Aggregate statistics by job
        stats = {}
        
        for execution in (executions.data or []):
            job_name = execution['job_name']
            if job_name not in stats:
                stats[job_name] = {
                    'total_executions': 0,
                    'successful': 0,
                    'failed': 0,
                    'duration_sum': 0,
                    'duration_count': 0,
                    'last_execution': None,
                    'active_retries': 0,
                    'dlq_items': 0,
                    'circuit_breakers': []
                }
            
            stats[job_name]['total_executions'] += 1
            
            if execution['status'] == 'completed':
                stats[job_name]['successful'] += 1
            elif execution['status'] == 'failed':
                stats[job_name]['failed'] += 1
            
            if execution.get('duration_seconds'):
                stats[job_name]['duration_sum'] += execution['duration_seconds']
                stats[job_name]['duration_count'] += 1
            
            if not stats[job_name]['last_execution'] or execution['started_at'] > stats[job_name]['last_execution']:
                stats[job_name]['last_execution'] = execution['started_at']
        
        # Add retry queue data
        for retry in (retries.data or []):
            job_name = retry['job_name']
            if job_name in stats:
                stats[job_name]['active_retries'] += 1
        
        # Add DLQ data
        for item in (dlq.data or []):
            job_name = item['job_name']
            if job_name in stats:
                stats[job_name]['dlq_items'] += 1
        
        # Add circuit breaker data
        for circuit in (circuits.data or []):
            # Extract job name from breaker key
            breaker_key = circuit['breaker_key']
            for job_name in stats:
                if job_name in breaker_key:
                    stats[job_name]['circuit_breakers'].append({
                        'state': circuit['state'],
                        'failure_count': circuit['failure_count']
                    })
        
        return stats
    
    async def evaluate_job_health(self, job_name: str, stats: Dict) -> Dict:
        """Evaluate health of a specific job"""
        
        health = {
            'status': 'healthy',
            'success_rate': 0,
            'avg_duration': 0,
            'last_run_ago': None,
            'issues': []
        }
        
        if stats['total_executions'] > 0:
            health['success_rate'] = (stats['successful'] / stats['total_executions']) * 100
            
            if stats['duration_count'] > 0:
                health['avg_duration'] = stats['duration_sum'] / stats['duration_count']
            
            # Check success rate
            if health['success_rate'] < 50:
                health['status'] = 'critical'
                health['issues'].append(f"Success rate critically low: {health['success_rate']:.1f}%")
            elif health['success_rate'] < 80:
                health['status'] = 'unhealthy'
                health['issues'].append(f"Success rate low: {health['success_rate']:.1f}%")
            elif health['success_rate'] < 95:
                health['status'] = 'degraded'
                health['issues'].append(f"Success rate below target: {health['success_rate']:.1f}%")
        
        # Check last execution time
        if stats['last_execution']:
            last_run = datetime.fromisoformat(stats['last_execution'].replace('Z', '+00:00'))
            time_since = datetime.now(timezone.utc) - last_run
            health['last_run_ago'] = time_since.total_seconds()
            
            # Alert if job hasn't run recently (job-specific thresholds needed)
            if 'weekly' in job_name and time_since > timedelta(days=8):
                health['status'] = 'unhealthy'
                health['issues'].append(f"Job hasn't run in {time_since.days} days")
            elif 'daily' in job_name and time_since > timedelta(days=2):
                health['status'] = 'degraded'
                health['issues'].append(f"Job hasn't run in {time_since.days} days")
        
        # Check for active issues
        if stats['active_retries'] > 10:
            health['status'] = 'degraded'
            health['issues'].append(f"High retry queue: {stats['active_retries']} items")
        
        if stats['dlq_items'] > 0:
            if stats['dlq_items'] > 50:
                health['status'] = 'critical'
            else:
                health['status'] = 'unhealthy' if health['status'] == 'healthy' else health['status']
            health['issues'].append(f"Dead letter queue has {stats['dlq_items']} items")
        
        if stats['circuit_breakers']:
            health['status'] = 'critical'
            health['issues'].append(f"Circuit breakers open: {len(stats['circuit_breakers'])}")
        
        return health
    
    async def check_alerts(self, job_name: str, stats: Dict) -> List[Dict]:
        """Check if alerts should be triggered"""
        
        alerts = []
        
        # Get alert configurations
        configs = supabase.table('job_alert_config')\
            .select('*')\
            .eq('enabled', True)\
            .execute()
        
        for config in (configs.data or []):
            should_alert, value = await self.evaluate_alert_condition(config, job_name, stats)
            
            if should_alert and not self.is_in_cooldown(config['alert_name']):
                severity = self.determine_severity(config['alert_type'], value, config['threshold_value'])
                
                alert = {
                    'alert_name': config['alert_name'],
                    'job_name': job_name,
                    'alert_type': config['alert_type'],
                    'severity': severity.value,
                    'triggered_value': value,
                    'threshold_value': config['threshold_value'],
                    'message': self.format_alert_message(config, job_name, value)
                }
                
                alerts.append(alert)
                self.set_cooldown(config['alert_name'], config.get('cooldown_minutes', 30))
                
                # Log to database
                await self.log_alert(alert, config['id'])
        
        return alerts
    
    async def evaluate_alert_condition(self, config: Dict, job_name: str, stats: Dict) -> tuple[bool, float]:
        """Evaluate if an alert condition is met"""
        
        alert_type = config['alert_type']
        threshold = config['threshold_value']
        
        if alert_type == AlertType.FAILURE_RATE.value:
            if stats['total_executions'] > 0:
                failure_rate = (stats['failed'] / stats['total_executions']) * 100
                return failure_rate > threshold, failure_rate
        
        elif alert_type == AlertType.DLQ_SIZE.value:
            return stats['dlq_items'] > threshold, stats['dlq_items']
        
        elif alert_type == AlertType.CIRCUIT_BREAKER.value:
            breaker_count = len(stats['circuit_breakers'])
            return breaker_count > threshold, breaker_count
        
        elif alert_type == AlertType.RETRY_RATE.value:
            if stats['total_executions'] > 0:
                retry_rate = (stats['active_retries'] / stats['total_executions']) * 100
                return retry_rate > threshold, retry_rate
        
        return False, 0
    
    def determine_severity(self, alert_type: str, value: float, threshold: float) -> AlertSeverity:
        """Determine alert severity based on how much threshold is exceeded"""
        
        ratio = value / threshold if threshold > 0 else 1
        
        if alert_type == AlertType.FAILURE_RATE.value:
            if ratio > 2:  # More than 2x threshold
                return AlertSeverity.CRITICAL
            elif ratio > 1.5:
                return AlertSeverity.ERROR
            else:
                return AlertSeverity.WARNING
        
        elif alert_type == AlertType.DLQ_SIZE.value:
            if ratio > 5:  # More than 5x threshold
                return AlertSeverity.CRITICAL
            elif ratio > 2:
                return AlertSeverity.ERROR
            else:
                return AlertSeverity.WARNING
        
        elif alert_type == AlertType.CIRCUIT_BREAKER.value:
            return AlertSeverity.CRITICAL  # Circuit breakers are always critical
        
        return AlertSeverity.WARNING
    
    def format_alert_message(self, config: Dict, job_name: str, value: float) -> str:
        """Format alert message for notifications"""
        
        alert_type = config['alert_type']
        threshold = config['threshold_value']
        
        if alert_type == AlertType.FAILURE_RATE.value:
            return f"Job '{job_name}' failure rate is {value:.1f}% (threshold: {threshold}%)"
        elif alert_type == AlertType.DLQ_SIZE.value:
            return f"Job '{job_name}' has {int(value)} items in dead letter queue (threshold: {int(threshold)})"
        elif alert_type == AlertType.CIRCUIT_BREAKER.value:
            return f"Job '{job_name}' has {int(value)} open circuit breakers"
        elif alert_type == AlertType.RETRY_RATE.value:
            return f"Job '{job_name}' retry rate is {value:.1f}% (threshold: {threshold}%)"
        
        return f"Alert triggered for job '{job_name}': {alert_type}"
    
    def is_in_cooldown(self, alert_name: str) -> bool:
        """Check if alert is in cooldown period"""
        
        if alert_name not in self.alert_cooldowns:
            return False
        
        cooldown_until = self.alert_cooldowns[alert_name]
        return datetime.now(timezone.utc) < cooldown_until
    
    def set_cooldown(self, alert_name: str, minutes: int):
        """Set cooldown for an alert"""
        self.alert_cooldowns[alert_name] = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    
    async def log_alert(self, alert: Dict, config_id: str):
        """Log alert to database"""
        
        try:
            supabase.table('job_alert_history').insert({
                'alert_config_id': config_id,
                'alert_name': alert['alert_name'],
                'alert_type': alert['alert_type'],
                'triggered_value': alert['triggered_value'],
                'threshold_value': alert['threshold_value'],
                'severity': alert['severity'],
                'message': alert['message'],
                'notification_sent': False
            }).execute()
        except Exception as e:
            logger.error(f"Failed to log alert: {e}")
    
    async def send_notifications(self, alerts: List[Dict]):
        """Send notifications for triggered alerts"""
        
        if not alerts:
            return
        
        # Filter for significant alerts
        significant_alerts = [
            alert for alert in alerts 
            if alert['severity'] in [AlertSeverity.ERROR.value, AlertSeverity.CRITICAL.value]
        ]
        
        if not significant_alerts:
            return
        
        # Send to Slack (or other notification service)
        if self.webhook_url:
            await self.send_slack_notification(significant_alerts)
        
        # Could add email, PagerDuty, etc. here
    
    async def send_slack_notification(self, alerts: List[Dict]):
        """Send alert notification to Slack"""
        
        try:
            # Format message
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🚨 Job Health Alert"
                    }
                }
            ]
            
            for alert in alerts:
                severity_emoji = {
                    AlertSeverity.WARNING.value: "⚠️",
                    AlertSeverity.ERROR.value: "❌",
                    AlertSeverity.CRITICAL.value: "🔥"
                }.get(alert['severity'], "ℹ️")
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{severity_emoji} *{alert['job_name']}*\n{alert['message']}"
                    }
                })
            
            # Send to Slack
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json={"blocks": blocks}
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to send Slack notification: {response.text}")
        
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")

# Scheduled monitoring job
async def run_health_monitoring():
    """Run health monitoring check"""
    
    monitor = JobMonitor()
    health_status = await monitor.check_job_health()
    
    # Log health status
    logger.info(f"Health check completed: {health_status['overall_health']}")
    
    if health_status['overall_health'] in ['unhealthy', 'critical']:
        logger.error(f"System health is {health_status['overall_health']}: {health_status['alerts']}")
    
    return health_status

# Dashboard API endpoint
async def get_job_dashboard() -> Dict:
    """Get job health dashboard data for UI"""
    
    try:
        # Get dashboard view data
        dashboard = supabase.table('job_health_dashboard').select('*').execute()
        
        # Get recent alerts
        recent_alerts = supabase.table('job_alert_history')\
            .select('*')\
            .order('created_at', desc=True)\
            .limit(10)\
            .execute()
        
        # Get DLQ summary
        dlq_summary = supabase.table('dlq_summary').select('*').execute()
        
        return {
            'status': 'success',
            'dashboard': dashboard.data,
            'recent_alerts': recent_alerts.data,
            'dlq_summary': dlq_summary.data,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }