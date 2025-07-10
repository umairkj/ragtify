import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.db.base import Base
from api.app.models import *
target_metadata = Base.metadata 