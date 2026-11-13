from alembic import context

connection = context.config.attributes["connection"]
service = context.config.attributes["service"]

context.configure(
    connection=connection,
    version_table_schema=service.schema,
    include_schemas=True,
    # Every table is explicitly qualified; never modify global search_path.
)
with context.begin_transaction():
    context.run_migrations()
