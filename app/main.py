from app.factory import create_app

app = create_app(
    include_existing_routers=True,
    start_scanner=True,
)
