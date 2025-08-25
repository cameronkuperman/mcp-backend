#!/usr/bin/env python3
"""
Trigger Intelligence Generation for All Active Users
Generates weekly intelligence (briefs, velocity, patterns, etc.) for all users

Usage:
    python trigger_all_intelligence.py                    # Generate for all active users
    python trigger_all_intelligence.py --user USER_ID     # Generate for specific user
    python trigger_all_intelligence.py --test             # Test with single test user
    python trigger_all_intelligence.py --dry-run          # Show what would be generated
"""

import asyncio
import argparse
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Import required modules
from supabase_client import supabase
from services.weekly_intelligence_job import (
    run_weekly_intelligence_generation,
    trigger_weekly_intelligence_now,
    get_active_users,
    get_current_week_monday
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'intelligence_generation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)

# Test user ID for development
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"

class IntelligenceGenerator:
    """Manages intelligence generation for users"""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.stats = {
            'total_users': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
    
    async def get_all_active_users(self, days_active: int = 30) -> List[str]:
        """Get all active users from the database"""
        logger.info(f"Fetching active users (last {days_active} days)...")
        
        if self.dry_run:
            logger.info("[DRY RUN] Would fetch active users")
            return [TEST_USER_ID]  # Return test user for dry run
        
        users = await get_active_users(days_active)
        logger.info(f"Found {len(users)} active users")
        return users
    
    async def generate_for_user(self, user_id: str) -> Dict[str, Any]:
        """Generate intelligence for a single user"""
        logger.info(f"{'[DRY RUN] Would generate' if self.dry_run else 'Generating'} intelligence for user: {user_id}")
        
        if self.dry_run:
            return {
                'user_id': user_id,
                'status': 'dry_run',
                'message': 'Dry run - no actual generation'
            }
        
        try:
            # Use the job's generation function directly
            from services.weekly_intelligence_job import generate_user_intelligence
            result = await generate_user_intelligence(user_id, force_refresh=True)
            
            # Log component results
            if 'components' in result:
                for component, status in result['components'].items():
                    status_emoji = "✅" if status.get('status') == 'success' else "❌"
                    logger.info(f"  {status_emoji} {component}: {status.get('status', 'unknown')}")
            
            # Update stats
            success_rate = result.get('summary', {}).get('success_rate', 0)
            if success_rate > 80:
                self.stats['successful'] += 1
                logger.info(f"✅ User {user_id}: SUCCESS ({success_rate:.1f}% components)")
            else:
                self.stats['failed'] += 1
                logger.warning(f"⚠️ User {user_id}: PARTIAL ({success_rate:.1f}% components)")
            
            return result
            
        except Exception as e:
            self.stats['failed'] += 1
            self.stats['errors'].append({
                'user_id': user_id,
                'error': str(e)
            })
            logger.error(f"❌ User {user_id}: ERROR - {str(e)}")
            return {
                'user_id': user_id,
                'status': 'error',
                'error': str(e)
            }
    
    async def generate_for_all(self, user_ids: Optional[List[str]] = None):
        """Generate intelligence for all users or specified list"""
        start_time = datetime.now()
        week_of = get_current_week_monday()
        
        logger.info("=" * 60)
        logger.info(f"INTELLIGENCE GENERATION - Week of {week_of}")
        logger.info("=" * 60)
        
        # Get users
        if user_ids:
            users_to_process = user_ids
            logger.info(f"Processing {len(users_to_process)} specified users")
        else:
            users_to_process = await self.get_all_active_users()
        
        self.stats['total_users'] = len(users_to_process)
        
        if not users_to_process:
            logger.warning("No users to process")
            return
        
        # Process in batches
        batch_size = 5
        for i in range(0, len(users_to_process), batch_size):
            batch = users_to_process[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(users_to_process) + batch_size - 1) // batch_size
            
            logger.info(f"\n📦 Processing batch {batch_num}/{total_batches} ({len(batch)} users)")
            
            # Process batch concurrently
            tasks = [self.generate_for_user(user_id) for user_id in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log batch results
            for user_id, result in zip(batch, results):
                if isinstance(result, Exception):
                    logger.error(f"  Exception for {user_id}: {result}")
                    self.stats['failed'] += 1
                    self.stats['errors'].append({
                        'user_id': user_id,
                        'error': str(result)
                    })
            
            # Delay between batches to avoid rate limiting
            if i + batch_size < len(users_to_process) and not self.dry_run:
                logger.info("  Waiting 2 seconds before next batch...")
                await asyncio.sleep(2)
        
        # Final summary
        duration = (datetime.now() - start_time).total_seconds()
        self.print_summary(duration)
    
    def print_summary(self, duration_seconds: float):
        """Print generation summary"""
        logger.info("\n" + "=" * 60)
        logger.info("GENERATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Users: {self.stats['total_users']}")
        logger.info(f"✅ Successful: {self.stats['successful']}")
        logger.info(f"⚠️ Failed: {self.stats['failed']}")
        logger.info(f"⏱️ Duration: {duration_seconds:.1f} seconds")
        
        if self.stats['successful'] > 0:
            avg_time = duration_seconds / self.stats['successful']
            logger.info(f"⚡ Avg time per user: {avg_time:.1f} seconds")
        
        success_rate = (self.stats['successful'] / self.stats['total_users'] * 100) if self.stats['total_users'] > 0 else 0
        logger.info(f"📊 Success Rate: {success_rate:.1f}%")
        
        if self.stats['errors']:
            logger.info(f"\n❌ Errors ({len(self.stats['errors'])} total):")
            for error in self.stats['errors'][:5]:  # Show first 5 errors
                logger.error(f"  - User {error['user_id']}: {error['error']}")
            if len(self.stats['errors']) > 5:
                logger.info(f"  ... and {len(self.stats['errors']) - 5} more errors")
        
        logger.info("=" * 60)

async def test_single_user():
    """Test generation with a single user"""
    logger.info("🧪 Running single user test...")
    generator = IntelligenceGenerator(dry_run=False)
    result = await generator.generate_for_user(TEST_USER_ID)
    
    if result.get('summary', {}).get('success_rate', 0) > 0:
        logger.info("✅ Test successful!")
        
        # Show what was generated
        logger.info("\n📋 Components generated:")
        for component, status in result.get('components', {}).items():
            logger.info(f"  - {component}: {status}")
    else:
        logger.error("❌ Test failed!")
    
    return result

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Generate intelligence for users')
    parser.add_argument('--user', type=str, help='Generate for specific user ID')
    parser.add_argument('--test', action='store_true', help='Test with single test user')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without executing')
    parser.add_argument('--all', action='store_true', help='Generate for all active users (default)')
    
    args = parser.parse_args()
    
    try:
        if args.test:
            # Test mode
            await test_single_user()
        elif args.user:
            # Single user mode
            generator = IntelligenceGenerator(dry_run=args.dry_run)
            await generator.generate_for_user(args.user)
            generator.print_summary(0)
        else:
            # All users mode (default)
            generator = IntelligenceGenerator(dry_run=args.dry_run)
            await generator.generate_for_all()
            
    except KeyboardInterrupt:
        logger.info("\n⚠️ Generation interrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())