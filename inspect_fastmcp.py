#!/usr/bin/env python3
"""
Script to inspect FastMCP attributes and methods
Looking for app, asgi, wsgi or similar attributes that could be used with uvicorn
"""

import inspect
from pprint import pprint

try:
    from fastmcp import FastMCP
    
    # Create a FastMCP instance
    mcp = FastMCP("inspection-test")
    
    print("=== FastMCP Instance Attributes ===")
    print("\nAll attributes (dir()):")
    all_attrs = dir(mcp)
    for attr in sorted(all_attrs):
        if not attr.startswith('_'):
            print(f"  - {attr}")
    
    print("\n\n=== Detailed Attribute Inspection ===")
    # Look for specific attributes that might be ASGI/WSGI apps
    interesting_attrs = ['app', 'asgi', 'wsgi', 'application', 'server', 
                        'asgi_app', 'wsgi_app', 'fastapi', 'starlette']
    
    print("\nChecking for web server related attributes:")
    for attr_name in interesting_attrs:
        if hasattr(mcp, attr_name):
            attr_value = getattr(mcp, attr_name)
            print(f"\n{attr_name}: {type(attr_value)}")
            print(f"  Value: {attr_value}")
    
    print("\n\n=== All Instance Attributes with Types ===")
    for attr in sorted(all_attrs):
        if not attr.startswith('__'):
            try:
                value = getattr(mcp, attr)
                print(f"{attr}: {type(value).__name__}")
                
                # If it's a method, show its signature
                if callable(value) and not attr.startswith('_'):
                    try:
                        sig = inspect.signature(value)
                        print(f"  Signature: {sig}")
                    except:
                        pass
            except Exception as e:
                print(f"{attr}: <Error accessing: {e}>")
    
    print("\n\n=== Instance Variables (__dict__) ===")
    print("Direct instance variables:")
    for key, value in vars(mcp).items():
        print(f"  {key}: {type(value).__name__}")
    
    print("\n\n=== Looking for ASGI/WSGI Callable ===")
    # Check if the instance itself is callable (ASGI app pattern)
    if callable(mcp):
        print("FastMCP instance is callable!")
        sig = inspect.signature(mcp)
        print(f"Signature: {sig}")
    
    # Check for __call__ method
    if hasattr(mcp, '__call__'):
        print("\nHas __call__ method")
        call_method = getattr(mcp, '__call__')
        if callable(call_method):
            try:
                sig = inspect.signature(call_method)
                print(f"__call__ signature: {sig}")
            except:
                pass
    
    # Look for methods that might return ASGI/WSGI apps
    print("\n\n=== Methods that might return web apps ===")
    for attr in dir(mcp):
        if not attr.startswith('_'):
            value = getattr(mcp, attr)
            if callable(value):
                method_name_lower = attr.lower()
                if any(keyword in method_name_lower for keyword in 
                       ['app', 'asgi', 'wsgi', 'server', 'run', 'start']):
                    print(f"\n{attr}():")
                    try:
                        sig = inspect.signature(value)
                        print(f"  Signature: {sig}")
                        
                        # Check docstring
                        if value.__doc__:
                            first_line = value.__doc__.strip().split('\n')[0]
                            print(f"  Doc: {first_line}")
                    except:
                        pass

except ImportError as e:
    print(f"Error importing FastMCP: {e}")
    print("\nMake sure FastMCP is installed: pip install fastmcp")
except Exception as e:
    print(f"Error during inspection: {e}")
    import traceback
    traceback.print_exc()