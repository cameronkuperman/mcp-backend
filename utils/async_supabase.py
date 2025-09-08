"""Async wrapper for Supabase operations to prevent blocking"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional
from supabase_client import supabase
import logging

logger = logging.getLogger(__name__)

# Thread pool for database operations
_executor = ThreadPoolExecutor(max_workers=20)

class AsyncSupabase:
    """Async wrapper for Supabase client operations"""
    
    @staticmethod
    async def select(
        table: str,
        columns: str = "*",
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> Any:
        """Async wrapper for Supabase select operations"""
        def _select():
            query = supabase.table(table).select(columns)
            
            if filters:
                for key, value in filters.items():
                    if key == "eq":
                        for field, val in value.items():
                            query = query.eq(field, val)
                    elif key == "gte":
                        for field, val in value.items():
                            query = query.gte(field, val)
                    elif key == "lte":
                        for field, val in value.items():
                            query = query.lte(field, val)
                    elif key == "in":
                        for field, val in value.items():
                            query = query.in_(field, val)
            
            if order_by:
                query = query.order(order_by, desc=order_desc)
            
            if limit:
                query = query.limit(limit)
            
            return query.execute()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, _select)
    
    @staticmethod
    async def insert(table: str, data: Dict[str, Any]) -> Any:
        """Async wrapper for Supabase insert operations"""
        def _insert():
            return supabase.table(table).insert(data).execute()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, _insert)
    
    @staticmethod
    async def update(
        table: str,
        data: Dict[str, Any],
        filters: Dict[str, Any]
    ) -> Any:
        """Async wrapper for Supabase update operations"""
        def _update():
            query = supabase.table(table).update(data)
            
            for key, value in filters.items():
                if key == "eq":
                    for field, val in value.items():
                        query = query.eq(field, val)
            
            return query.execute()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, _update)
    
    @staticmethod
    async def batch_select(
        table: str,
        ids: List[str],
        id_field: str = "id",
        columns: str = "*",
        batch_size: int = 100
    ) -> List[Any]:
        """Batch select operations for large ID lists"""
        results = []
        
        # Split into batches
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            
            result = await AsyncSupabase.select(
                table=table,
                columns=columns,
                filters={"in": {id_field: batch_ids}}
            )
            
            if result.data:
                results.extend(result.data)
        
        return results

# Convenience functions for common operations
async def async_get_user_data(user_id: str, table: str, columns: str = "*", limit: int = 100) -> Any:
    """Get user-specific data from any table"""
    return await AsyncSupabase.select(
        table=table,
        columns=columns,
        filters={"eq": {"user_id": user_id}},
        limit=limit
    )

async def async_get_recent_data(
    user_id: str,
    table: str,
    date_field: str,
    start_date: str,
    columns: str = "*",
    limit: int = 100
) -> Any:
    """Get recent data for a user within date range"""
    return await AsyncSupabase.select(
        table=table,
        columns=columns,
        filters={
            "eq": {"user_id": user_id},
            "gte": {date_field: start_date}
        },
        limit=limit,
        order_by=date_field,
        order_desc=False
    )