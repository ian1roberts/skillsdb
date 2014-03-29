import os
import logging
from datetime import datetime

def setup_log(module, fn=None, fileLevel=logging.DEBUG, consoleLevel=logging.INFO):
    logging.basicConfig(level=logging.DEBUG)
    log=logging.getLogger(module)
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', "%Y-%m-%d %H:%M:%S")
    time_now = datetime.today()
    time_now = time_now.strftime("%d-%m-%Y")
    if not fn:
        log_file = ''.join(['.logs/', time_now, '_skillsdb_run.log'])
    else:
        dirname, basename = os.path.dirname(fn), os.path.basename(fn)
        if not dirname:
            log_file = ''.join(['.logs/', time_now, '_', fn])
        else:
            log_file = ''.join([dirname, '/',time_now, '_', fn])
            
    if not os.path.exists('.logs'):
        os.mkdir('.logs')   

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(fileLevel)
    file_handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(consoleLevel)
    console_handler.setFormatter(formatter)
    
    log.addHandler(console_handler)
    log.addHandler(file_handler)
    log.propagate = 0

    return log
