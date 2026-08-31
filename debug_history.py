import sys
import logging
logging.basicConfig(level=logging.DEBUG)
sys.path.insert(0, '.')
from logic.data_retrieval import DataRetrieval
from logic.config_manager import load_config
from logic.encryption import decrypt_text
import mysql.connector

cfg = load_config()['central']
conn = mysql.connector.connect(host=cfg['host'], user=cfg['user'], password=cfg['password'], database=cfg['database'])
c = conn.cursor(dictionary=True)
c.execute('SELECT * FROM erp_configs WHERE college_name = %s', ('Vishnu',))
erp = c.fetchone()
conn.close()

erp_config = {
    'db_type': erp['db_type'], 'host': erp['db_host'], 'port': erp['db_port'],
    'user': erp['db_user'], 'password': decrypt_text(erp['encrypted_pass']),
    'database': erp['db_name']
}
for k, v in erp.items():
    if k.startswith('tbl_') or k.startswith('col_') or k in ('strategy', 'discovery_timestamp'):
        if v is not None:
            erp_config[k] = v

from logic.erp_connection import ERPConnection
erp_conn = ERPConnection(erp_config)
erp_conn.connect()

def test_fetch():
    dr = DataRetrieval(erp_conn, erp_config, 'ADAPTER')
    for s_batch, h_batch, d_list in dr.fetch_batches(batch_size=10):
        print('Students fetched:', len(s_batch))
        print('Histories fetched:', len(h_batch))
        if h_batch:
            print('Sample history:', h_batch[0])
        break
        
test_fetch()
erp_conn.close()
