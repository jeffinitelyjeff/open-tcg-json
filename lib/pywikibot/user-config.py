import os

mylang = 'en'
family = 'dcg'

username = os.environ.get('PYWIKIBOT_USERNAME')
if not username:
	raise RuntimeError('PYWIKIBOT_USERNAME environment variable is required')

usernames['dcg']['en'] = username
password_file = "user-password.py"

base_dir = os.environ.get('PYWIKIBOT_DIR', os.getcwd())
user_families_paths = [base_dir]
