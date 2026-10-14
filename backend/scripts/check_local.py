from sqlalchemy import create_engine, text

e = create_engine("postgresql+psycopg://postgres@localhost:5432/nimbus")
with e.connect() as c:
    tables = c.execute(
        text("select count(*) from information_schema.tables where table_schema='public'")
    ).scalar()
    ver = c.execute(text("select version_num from alembic_version")).scalar()
    ents = c.execute(text("select count(*) from digital_entities")).scalar()
    cases = c.execute(text("select count(*) from investigation_cases")).scalar()
print(f"local nimbus: tables={tables} alembic={ver} entities={ents} cases={cases}")
