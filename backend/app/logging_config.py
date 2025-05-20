import logging
import sys
from app.config import settings

def setup_logging():
    """アプリケーションのロギング設定をセットアップする"""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    
    # ルートロガーの設定
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # サードパーティライブラリのログレベルを調整
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    
    # アプリケーションロガーを取得
    logger = logging.getLogger("app")
    return logger

logger = setup_logging()
