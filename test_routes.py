import sys
sys.path.insert(0, r'C:\Users\Marwan\Desktop\AI\Flos\apps\backend\src')

try:
    from kashat.api import create_app
    app = create_app()
    
    # Find routes
    routes = []
    for route in app.routes:
        if hasattr(route, 'path'):
            if 'networth' in route.path or 'budget' in route.path or 'calendar' in route.path or 'insights' in route.path:
                routes.append(route.path)
    
    print("Found routes:")
    for r in sorted(routes):
        print(f"  {r}")
    
    if not routes:
        print("  NONE - These routes are NOT registered!")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
