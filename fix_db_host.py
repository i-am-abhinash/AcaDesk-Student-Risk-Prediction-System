import mysql.connector
conn = mysql.connector.connect(host='127.0.0.1', user='root', password='Abhinash@19', database='acadesk_central')
cursor = conn.cursor()
cursor.execute("UPDATE erp_configs SET db_host='127.0.0.1'")
conn.commit()
print('Updated erp_configs db_host to 127.0.0.1')
conn.close()
