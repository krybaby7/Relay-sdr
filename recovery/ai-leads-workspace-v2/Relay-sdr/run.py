"""Start one local pilot workspace. Never run multiple workers against this SQLite store."""
import os
from dotenv import load_dotenv
import uvicorn
from app.config import Config
from app.main import create_app

if __name__ == '__main__':
    load_dotenv()
    config = Config.from_env()
    print('\n  Relay SDR · local pilot\n')
    print(f'  Open: http://localhost:{config.port}')
    print(f'  Workspace token: {config.admin_token}\n')
    print('  Keep this token private. API keys never belong in the browser.')
    print('  Outbound dialing: ' + ('ENABLED (per-call safeguards still apply)' if config.enable_outbound else 'DISABLED'))
    uvicorn.run(create_app(config), host=os.getenv('HOST', '127.0.0.1'), port=config.port,
                access_log=False, ws_max_size=262144, ws_max_queue=16)
