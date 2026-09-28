import os
import sys

# Ensure working directory is project root
proj_dir = os.path.dirname(__file__)
os.chdir(proj_dir)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Clinic.settings')
import django
django.setup()

print('Running test_prescription_margins_v2.py')
print('='*80)

with open('test_prescription_margins_v2.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Execute the test script
exec(compile(code, 'test_prescription_margins_v2.py', 'exec'))

print('\nDone.')
