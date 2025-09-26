import sys
import os
# Ensure repository root is on sys.path when running from scripts/
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root not in sys.path:
	sys.path.insert(0, root)

from core.auth import login_user

print(login_user('melendez_ma@jp.pr.gov','admin123'))
