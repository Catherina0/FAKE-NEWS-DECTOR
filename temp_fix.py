def fix_try_exception():
    try:
        print('Hello')
    except Exception as e:
        print(f'Error: {e}')
