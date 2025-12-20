import logging
import logging.handlers
from pathlib import Path

# 创建日志目录
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# 配置日志
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = LOG_DIR / "scheduler.log"
LOG_LEVEL = logging.INFO

def setup_logger(name: str) -> logging.Logger:
    """设置日志记录器"""
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    
    # 移除已有的处理器（避免重复）
    logger.handlers.clear()
    
    # 文件处理器（带轮转）
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5  # 保留5个历史文件
    )
    file_handler.setLevel(LOG_LEVEL)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# 主日志记录器
logger = setup_logger("scheduler")
