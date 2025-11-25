from .main import run as main_run

def daily_handler(event, context):
    import sys
    sys.argv = ['main.py', '--mode=daily']
    main_run()

def weekly_handler(event, context):
    import sys
    sys.argv = ['main.py', '--mode=weekly']
    main_run()