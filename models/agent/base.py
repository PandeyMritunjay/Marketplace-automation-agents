from sqlalchemy.ext.declarative import declarative_base

# Shared Base for all agent models to enable foreign key relationships
Base = declarative_base()
